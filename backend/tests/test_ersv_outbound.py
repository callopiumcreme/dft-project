"""Tests for the outbound eRSV renderer and endpoints (per-PoS, post 0022).

Cliente direction (2026-05-23): outbound eRSV is keyed on a PoS row, not on a
consignment. ``CO/{yy}/{seq:03d}`` is stored on ``consignment_pos.ersv_outbound_no``
and the API path is ``/ersv/outbound/{consignment_id}/{pos_number}``.

Test matrix:
  - test_outbound_number_format: helper allocates CO/25/NNN, then CO/25/NNN+1
    against ``consignment_pos`` rows.
  - test_outbound_year_derived_from_shipment_year: 2025 consignment minted in
    2026 → ``CO/25/...`` (regression: not wall-clock year).
  - test_outbound_idempotent_number: rendering same (cid, pos) twice → same no.
  - test_outbound_html_contains_buyer_and_pos: HTML for a PoS row contains
    buyer "Crown Oil", the PoS number, and ``end-of-life tyres``.
  - test_outbound_regenerate_admin_only: POST /regenerate as operator → 403;
    as admin → 200 with a new number.
  - test_outbound_pdf_returns_bytes: PDF endpoint returns non-empty bytes.
  - test_outbound_2025_starts_at_seq_007: when DB has no prior CO/25/* row,
    allocator returns CO/25/007 (cliente offset).
"""
from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.session import get_db
from app.main import app

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

# DATABASE_URL / JWT_SECRET + auth-bypass override are configured by conftest.py.
_engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(_engine, expire_on_commit=False)


async def _override_get_db() -> AsyncIterator[AsyncSession]:
    async with _factory() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# admin_headers / operator_headers / db_session come from conftest.py.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _ensure_crown_oil(db: AsyncSession) -> int:
    await db.execute(
        text(
            """
            INSERT INTO off_taker (code, name, country, address, created_at, updated_at)
            VALUES ('CROWN-OIL-UK', 'Crown Oil Ltd', 'GB', 'Bury, UK', NOW(), NOW())
            ON CONFLICT (code) DO UPDATE SET updated_at = NOW()
            """
        )
    )
    await db.commit()
    r = await db.execute(text("SELECT id FROM off_taker WHERE code = 'CROWN-OIL-UK'"))
    return int(r.scalar_one())


async def _create_scratch_consignment(
    db: AsyncSession,
    crown_oil_id: int,
    code: str,
    *,
    prod_date_from: str = "2025-06-01",
    prod_date_to: str = "2025-08-31",
) -> int:
    """Insert (or reuse) a minimal consignment for testing. Returns its id.

    Production window defaults to Q3 2025 so any per-PoS outbound number
    minted lands in the ``CO/25/...`` family regardless of wall-clock time.
    """
    from datetime import date as _date

    pdf_obj = _date.fromisoformat(prod_date_from)
    pdt_obj = _date.fromisoformat(prod_date_to)
    await db.execute(
        text(
            """
            INSERT INTO consignment
                (code, off_taker_id, product_grade, status, total_kg,
                 prod_date_from, prod_date_to, created_at, updated_at)
            VALUES
                (:code, :ot_id, 'DEV-P100', 'draft', 10000.000,
                 :pdf, :pdt, NOW(), NOW())
            ON CONFLICT (code) DO UPDATE
                SET updated_at      = NOW(),
                    prod_date_from  = EXCLUDED.prod_date_from,
                    prod_date_to    = EXCLUDED.prod_date_to,
                    deleted_at      = NULL
            """
        ),
        {"code": code, "ot_id": crown_oil_id, "pdf": pdf_obj, "pdt": pdt_obj},
    )
    await db.commit()
    r = await db.execute(
        text("SELECT id FROM consignment WHERE code = :code"),
        {"code": code},
    )
    return int(r.scalar_one())


async def _attach_pos(
    db: AsyncSession,
    cons_id: int,
    pos_number: str,
    kg_net: float = 9000.000,
    *,
    clear_outbound_no: bool = True,
) -> None:
    """Insert or reactivate a PoS row attached to the consignment.

    The autouse cleanup in conftest tombstones PoS rows whose pos_number
    starts with one of the scratch prefixes — pass a prefix-matching string
    so reruns can re-insert.
    """
    await db.execute(
        text(
            """
            INSERT INTO consignment_pos
                (consignment_id, pos_number, kg_net,
                 ghg_ep, ghg_etd, ghg_total, ghg_saving_pct)
            VALUES
                (:cid, :pos, :kg, 12.33, 4.63, 16.95, 81.96)
            ON CONFLICT (consignment_id, pos_number) DO UPDATE
                SET kg_net = EXCLUDED.kg_net,
                    deleted_at = NULL
            """
        ),
        {"cid": cons_id, "pos": pos_number, "kg": kg_net},
    )
    if clear_outbound_no:
        await db.execute(
            text(
                "UPDATE consignment_pos SET ersv_outbound_no = NULL "
                "WHERE consignment_id = :cid AND pos_number = :pos"
            ),
            {"cid": cons_id, "pos": pos_number},
        )
    await db.commit()


# ---------------------------------------------------------------------------
# test_outbound_number_format
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_outbound_number_format(db_session: AsyncSession) -> None:
    """Allocator returns CO/25/NNN against consignment_pos, then NNN+1."""
    from app.services.ersv_renderer import _allocate_outbound_no

    crown_id = await _ensure_crown_oil(db_session)
    cons_id = await _create_scratch_consignment(
        db_session, crown_id, "CONS-ERSV-OUT-NUM"
    )
    await _attach_pos(db_session, cons_id, "POS-ERSV-OUT-NUM-A")
    await _attach_pos(db_session, cons_id, "POS-ERSV-OUT-NUM-B")

    no_a = await _allocate_outbound_no("25", db_session)
    await db_session.execute(
        text(
            "UPDATE consignment_pos SET ersv_outbound_no = :no "
            "WHERE consignment_id = :cid AND pos_number = :pos"
        ),
        {"no": no_a, "cid": cons_id, "pos": "POS-ERSV-OUT-NUM-A"},
    )
    await db_session.commit()

    no_b = await _allocate_outbound_no("25", db_session)
    await db_session.execute(
        text(
            "UPDATE consignment_pos SET ersv_outbound_no = :no "
            "WHERE consignment_id = :cid AND pos_number = :pos"
        ),
        {"no": no_b, "cid": cons_id, "pos": "POS-ERSV-OUT-NUM-B"},
    )
    await db_session.commit()

    _pattern = re.compile(r"^CO/25/\d{3}$")
    assert _pattern.match(no_a), f"Expected CO/25/NNN, got {no_a!r}"
    assert _pattern.match(no_b), f"Expected CO/25/NNN, got {no_b!r}"

    seq_a = int(no_a.split("/")[2])
    seq_b = int(no_b.split("/")[2])
    assert seq_b == seq_a + 1, (
        f"Expected consecutive sequence: got {no_a} then {no_b}"
    )

    # Cliente offset 2026-05-23: 2025 starts at 007.
    assert seq_a >= 7, (
        f"Expected seq >= 7 for 2025 (cliente offset), got {no_a!r}"
    )


# ---------------------------------------------------------------------------
# test_outbound_year_derived_from_shipment_year
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_outbound_year_derived_from_shipment_year(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """yy segment comes from consignment shipment year, not wall clock."""
    crown_id = await _ensure_crown_oil(db_session)
    cons_id = await _create_scratch_consignment(
        db_session,
        crown_id,
        "CONS-ERSV-OUT-YEAR-25",
        prod_date_from="2025-06-01",
        prod_date_to="2025-08-31",
    )
    pos_no = "POS-ERSV-OUT-YEAR"
    await _attach_pos(db_session, cons_id, pos_no)

    resp = await client.get(
        f"/ersv/outbound/{cons_id}/{pos_no}?format=html",
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    minted_no = resp.headers.get("X-Ersv-Outbound-No")
    assert minted_no is not None, "Render must return X-Ersv-Outbound-No header"
    assert minted_no.startswith("CO/25/"), (
        f"Expected CO/25/..., got {minted_no!r} — bug: yy taken from wall clock?"
    )
    assert re.match(r"^CO/25/\d{3}$", minted_no), f"Bad format: {minted_no!r}"


# ---------------------------------------------------------------------------
# test_outbound_idempotent_number
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_outbound_idempotent_number(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """Rendering same (cid, pos) twice returns the same ersv_outbound_no."""
    crown_id = await _ensure_crown_oil(db_session)
    cons_id = await _create_scratch_consignment(
        db_session, crown_id, "CONS-ERSV-OUT-IDEM"
    )
    pos_no = "POS-ERSV-OUT-IDEM"
    await _attach_pos(db_session, cons_id, pos_no)

    resp1 = await client.get(
        f"/ersv/outbound/{cons_id}/{pos_no}?format=html",
        headers=admin_headers,
    )
    assert resp1.status_code == 200, resp1.text
    no1 = resp1.headers.get("X-Ersv-Outbound-No")
    assert no1 is not None, "First render must return X-Ersv-Outbound-No header"
    assert re.match(r"^CO/\d{2}/\d{3}$", no1), f"Bad format: {no1!r}"

    resp2 = await client.get(
        f"/ersv/outbound/{cons_id}/{pos_no}?format=html",
        headers=admin_headers,
    )
    assert resp2.status_code == 200, resp2.text
    no2 = resp2.headers.get("X-Ersv-Outbound-No")
    assert no2 == no1, f"Idempotency violated: first={no1!r}, second={no2!r}"


# ---------------------------------------------------------------------------
# test_outbound_html_contains_buyer_and_pos
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_outbound_html_contains_buyer_and_pos(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """HTML contains buyer, PoS number, feedstock label, and no forbidden strings."""
    crown_id = await _ensure_crown_oil(db_session)
    cons_id = await _create_scratch_consignment(
        db_session, crown_id, "CONS-ERSV-OUT-HTML"
    )
    pos_no = "POS-ERSV-OUT-OISCRO-0013-25"
    await _attach_pos(db_session, cons_id, pos_no, kg_net=25021.000)

    resp = await client.get(
        f"/ersv/outbound/{cons_id}/{pos_no}?format=html",
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    html = resp.text

    assert "Crown Oil" in html, "HTML must contain buyer name 'Crown Oil'"
    assert pos_no in html, f"HTML must contain PoS number {pos_no!r}"
    assert "end-of-life tyres" in html, "HTML must mention feedstock as end-of-life tyres"
    assert "DEV-P100" in html, "HTML must mention product grade DEV-P100"
    assert "plastic" not in html.lower(), "HTML must NOT contain the word 'plastic'"
    assert "binova" not in html.lower(), "HTML must NOT mention BiNova"
    assert "Baar" in html, "HTML must mention Baar (OisteBio registered address)"


# ---------------------------------------------------------------------------
# test_outbound_regenerate_admin_only
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_outbound_regenerate_admin_only(
    client: AsyncClient,
    admin_headers: dict[str, str],
    operator_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """POST /ersv/outbound/{cid}/{pos}/regenerate: operator → 403; admin → 200."""
    crown_id = await _ensure_crown_oil(db_session)
    cons_id = await _create_scratch_consignment(
        db_session, crown_id, "CONS-ERSV-OUT-REGEN"
    )
    pos_no = "POS-ERSV-OUT-REGEN"
    await _attach_pos(db_session, cons_id, pos_no)

    init_resp = await client.get(
        f"/ersv/outbound/{cons_id}/{pos_no}?format=html",
        headers=admin_headers,
    )
    assert init_resp.status_code == 200
    initial_no = init_resp.headers.get("X-Ersv-Outbound-No")

    op_resp = await client.post(
        f"/ersv/outbound/{cons_id}/{pos_no}/regenerate",
        headers=operator_headers,
    )
    assert op_resp.status_code == 403, (
        f"Expected 403 for operator, got {op_resp.status_code}: {op_resp.text}"
    )

    admin_resp = await client.post(
        f"/ersv/outbound/{cons_id}/{pos_no}/regenerate",
        headers=admin_headers,
    )
    assert admin_resp.status_code == 200, (
        f"Expected 200 for admin, got {admin_resp.status_code}: {admin_resp.text}"
    )
    data = admin_resp.json()
    assert data["consignment_id"] == cons_id
    assert data["pos_number"] == pos_no
    assert data["previous_no"] == initial_no
    new_no = data["ersv_outbound_no"]
    assert re.match(r"^CO/\d{2}/\d{3}$", new_no), f"Bad format: {new_no!r}"
    assert new_no != initial_no, "Regenerate must produce a new number"


# ---------------------------------------------------------------------------
# test_outbound_pdf_returns_bytes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_outbound_pdf_returns_bytes(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """PDF endpoint returns non-empty bytes with application/pdf content-type."""
    crown_id = await _ensure_crown_oil(db_session)
    cons_id = await _create_scratch_consignment(
        db_session, crown_id, "CONS-ERSV-OUT-PDF"
    )
    pos_no = "POS-ERSV-OUT-PDF"
    await _attach_pos(db_session, cons_id, pos_no)

    resp = await client.get(
        f"/ersv/outbound/{cons_id}/{pos_no}?format=pdf",
        headers=admin_headers,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    content_type = resp.headers.get("content-type", "")
    assert "application/pdf" in content_type, (
        f"Expected application/pdf content-type, got {content_type!r}"
    )

    pdf_bytes = resp.content
    assert len(pdf_bytes) > 0, "PDF response must not be empty"

    assert pdf_bytes[:4] == b"%PDF", (
        f"Response does not start with %PDF magic: {pdf_bytes[:8]!r}"
    )

    no_header = resp.headers.get("X-Ersv-Outbound-No")
    assert no_header is not None
    assert re.match(r"^CO/\d{2}/\d{3}$", no_header), f"Bad format: {no_header!r}"


# ---------------------------------------------------------------------------
# test_outbound_2025_starts_at_seq_007
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_outbound_2025_starts_at_seq_007(db_session: AsyncSession) -> None:
    """Cliente direction (2026-05-23): first 2025 outbound = CO/25/007.

    With zero live CO/25/* rows on ``consignment_pos`` (the allocator's source
    after 0022), the allocator must skip to 007 instead of starting at 001.
    """
    from app.services.ersv_renderer import _OUTBOUND_START_SEQ, _allocate_outbound_no

    assert _OUTBOUND_START_SEQ.get("25") == 7, (
        "Cliente offset for 2025 must be 7 (CO/25/007 is the first outbound)"
    )

    # Tombstone any live CO/25/* numbers on consignment_pos so the allocator
    # floor is exercised. UNIQUE partial index frees up because we mangle the
    # column AND set deleted_at. Audit trail preserved (number recoverable by
    # split_part on '__expired_').
    await db_session.execute(
        text(
            """
            UPDATE consignment_pos
            SET deleted_at = NOW(),
                ersv_outbound_no = ersv_outbound_no || '__expired_'
                                   || consignment_id::text || '_' || pos_number
            WHERE ersv_outbound_no LIKE 'CO/25/%'
              AND deleted_at IS NULL
            """
        )
    )
    await db_session.commit()

    try:
        next_no = await _allocate_outbound_no("25", db_session)
        assert next_no == "CO/25/007", (
            f"Expected first 2025 outbound = CO/25/007 (cliente offset), got {next_no!r}"
        )

        next_no_2026 = await _allocate_outbound_no("26", db_session)
        assert re.match(r"^CO/26/\d{3}$", next_no_2026), (
            f"Bad format: {next_no_2026!r}"
        )
        seq_2026 = int(next_no_2026.split("/")[2])
        assert seq_2026 < 7 or seq_2026 == 1, (
            f"2026 must not inherit 2025 offset; got seq {seq_2026}"
        )
    finally:
        # Restore tombstoned rows so other tests / real data aren't affected.
        await db_session.execute(
            text(
                r"""
                UPDATE consignment_pos
                SET deleted_at = NULL,
                    ersv_outbound_no = split_part(ersv_outbound_no, '__expired_', 1)
                WHERE ersv_outbound_no LIKE 'CO/25/%\_\_expired\_%' ESCAPE '\'
                """
            )
        )
        await db_session.commit()
