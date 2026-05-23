"""Tests for the outbound eRSV renderer and endpoints.

Test matrix:
  - test_outbound_number_format: helper allocates CO/25/001, then CO/25/002
  - test_outbound_year_derived_from_shipment_year: a 2025 consignment minted
    in 2026 produces ``CO/25/...`` (regression: not wall-clock year).
  - test_outbound_idempotent_number: rendering same consignment twice keeps same no.
  - test_outbound_html_contains_buyer_and_pos: HTML for CONS-2025-Q3-CROWN has
    "Crown Oil" and at least one "OISCRO-" PoS string.
  - test_outbound_regenerate_admin_only: POST /regenerate as operator → 403;
    as admin → 200 with a new number.
  - test_outbound_pdf_returns_bytes: PDF endpoint returns non-empty bytes with
    application/pdf content-type.

DB note: tests that hit the live DB require the stack to be up and the
backfill from #4 to have been applied (CONS-2025-Q3-CROWN + PoS rows).
When the DB is unreachable, tests that depend on it are collected but will
fail with a connection error — they are NOT skipped so the CI pipeline
surfaces them clearly.
"""
from __future__ import annotations

import os
import re
from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.session import get_db
from app.main import app

# DATABASE_URL / JWT_SECRET + auth-bypass override are configured by conftest.py.
_engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(_engine, expire_on_commit=False)

# ---------------------------------------------------------------------------
# DB session override (auth override is installed by conftest.py)
# ---------------------------------------------------------------------------


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
# Helper: ensure Crown Oil off_taker and a scratch consignment exist
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
    r = await db.execute(
        text("SELECT id FROM off_taker WHERE code = 'CROWN-OIL-UK'")
    )
    return int(r.scalar_one())


async def _create_scratch_consignment(
    db: AsyncSession,
    crown_oil_id: int,
    code: str,
    *,
    clear_outbound_no: bool = False,
    prod_date_from: str = "2025-06-01",
    prod_date_to: str = "2025-08-31",
) -> int:
    """Insert (or reuse) a minimal consignment for testing. Returns its id.

    ``prod_date_from`` / ``prod_date_to`` default to a Q3 2025 window so
    minted ``ersv_outbound_no`` values land in the ``CO/25/...`` family
    regardless of the wall-clock year at test time.
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
                    -- Resurrect rows soft-deleted by a previous test run
                    deleted_at      = NULL
            """
        ),
        {
            "code": code,
            "ot_id": crown_oil_id,
            "pdf": pdf_obj,
            "pdt": pdt_obj,
        },
    )
    if clear_outbound_no:
        await db.execute(
            text(
                "UPDATE consignment SET ersv_outbound_no = NULL, updated_at = NOW() "
                "WHERE code = :code"
            ),
            {"code": code},
        )
    await db.commit()
    r = await db.execute(
        text("SELECT id FROM consignment WHERE code = :code"),
        {"code": code},
    )
    return int(r.scalar_one())


# ---------------------------------------------------------------------------
# test_outbound_number_format
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_outbound_number_format(db_session: AsyncSession) -> None:
    """Number helper allocates CO/25/NNN, then CO/25/NNN+1 for the same year."""
    from app.services.ersv_renderer import _allocate_outbound_no

    crown_id = await _ensure_crown_oil(db_session)

    # Use unique codes so these scratch rows don't clash with real data
    code_a = "CONS-ERSV-OUT-NUM-A"
    code_b = "CONS-ERSV-OUT-NUM-B"

    id_a = await _create_scratch_consignment(
        db_session, crown_id, code_a, clear_outbound_no=True,
        prod_date_from="2025-06-01", prod_date_to="2025-08-31",
    )
    id_b = await _create_scratch_consignment(
        db_session, crown_id, code_b, clear_outbound_no=True,
        prod_date_from="2025-06-01", prod_date_to="2025-08-31",
    )

    # Clear any prior outbound numbers on these two rows so the counter
    # is predictable *for these rows only*.  Other rows with CO/25/... that
    # exist in the DB will shift the absolute sequence, so we only assert
    # the FORMAT and the ordering, not the absolute seq numbers.
    await db_session.execute(
        text(
            "UPDATE consignment SET ersv_outbound_no = NULL "
            "WHERE id = ANY(:ids)"
        ),
        {"ids": [id_a, id_b]},
    )
    await db_session.commit()

    no_a = await _allocate_outbound_no("25", db_session)
    # Persist so the next call sees it
    await db_session.execute(
        text(
            "UPDATE consignment SET ersv_outbound_no = :no WHERE id = :id"
        ),
        {"no": no_a, "id": id_a},
    )
    await db_session.commit()

    no_b = await _allocate_outbound_no("25", db_session)
    await db_session.execute(
        text(
            "UPDATE consignment SET ersv_outbound_no = :no WHERE id = :id"
        ),
        {"no": no_b, "id": id_b},
    )
    await db_session.commit()

    # Format assertions
    _pattern = re.compile(r"^CO/25/\d{3}$")
    assert _pattern.match(no_a), f"Expected CO/25/NNN, got {no_a!r}"
    assert _pattern.match(no_b), f"Expected CO/25/NNN, got {no_b!r}"

    # Ordering: seq(b) = seq(a) + 1
    seq_a = int(no_a.split("/")[2])
    seq_b = int(no_b.split("/")[2])
    assert seq_b == seq_a + 1, (
        f"Expected consecutive sequence: got {no_a} then {no_b}"
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
    """Regression: yy segment comes from consignment shipment year, not wall clock.

    A consignment with ``prod_date_to = 2025-08-31`` minted in 2026 (or any
    later year) MUST produce ``CO/25/...`` — not ``CO/26/...``.

    This guards against the bug where ``_allocate_outbound_no`` used
    ``datetime.now().year`` for the ``yy`` segment.
    """
    crown_id = await _ensure_crown_oil(db_session)
    cons_id = await _create_scratch_consignment(
        db_session,
        crown_id,
        "CONS-ERSV-OUT-YEAR-25",
        clear_outbound_no=True,
        prod_date_from="2025-06-01",
        prod_date_to="2025-08-31",
    )

    resp = await client.get(
        f"/ersv/outbound/{cons_id}?format=html",
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
    """Rendering the same consignment twice returns the same ersv_outbound_no."""
    crown_id = await _ensure_crown_oil(db_session)
    cons_id = await _create_scratch_consignment(
        db_session,
        crown_id,
        "CONS-ERSV-OUT-IDEM",
        clear_outbound_no=True,
    )

    # First render — allocates number
    resp1 = await client.get(
        f"/ersv/outbound/{cons_id}?format=html",
        headers=admin_headers,
    )
    assert resp1.status_code == 200, resp1.text
    no1 = resp1.headers.get("X-Ersv-Outbound-No")
    assert no1 is not None, "First render must return X-Ersv-Outbound-No header"
    assert re.match(r"^CO/\d{2}/\d{3}$", no1), f"Bad format: {no1!r}"

    # Second render — must return the same number
    resp2 = await client.get(
        f"/ersv/outbound/{cons_id}?format=html",
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
    """HTML for a consignment with Crown Oil buyer and PoS rows contains expected text."""
    crown_id = await _ensure_crown_oil(db_session)
    cons_id = await _create_scratch_consignment(
        db_session,
        crown_id,
        "CONS-ERSV-OUT-HTML",
        clear_outbound_no=True,
    )

    # Attach a PoS row so the template table is populated
    await db_session.execute(
        text(
            """
            INSERT INTO consignment_pos (consignment_id, pos_number, kg_net)
            VALUES (:cid, 'OISCRO-0013-25', 9000.000)
            ON CONFLICT (consignment_id, pos_number) DO UPDATE SET kg_net = 9000.000
            """
        ),
        {"cid": cons_id},
    )
    await db_session.commit()

    resp = await client.get(
        f"/ersv/outbound/{cons_id}?format=html",
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    html = resp.text

    assert "Crown Oil" in html, "HTML must contain buyer name 'Crown Oil'"
    assert "OISCRO-" in html, "HTML must contain at least one OISCRO- PoS reference"
    assert "end-of-life tyres" in html, "HTML must mention feedstock as end-of-life tyres"
    assert "DEV-P100" in html, "HTML must mention product grade DEV-P100"
    # Negative check — must never say "plastic"
    assert "plastic" not in html.lower(), "HTML must NOT contain the word 'plastic'"
    # Must not mention BiNova (dev studio — never in client docs)
    assert "binova" not in html.lower(), "HTML must NOT mention BiNova"
    # Swiss GmbH address check
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
    """POST /ersv/outbound/{id}/regenerate: operator → 403; admin → 200 with new number."""
    crown_id = await _ensure_crown_oil(db_session)
    cons_id = await _create_scratch_consignment(
        db_session,
        crown_id,
        "CONS-ERSV-OUT-REGEN",
        clear_outbound_no=True,
    )

    # First, ensure a number exists by doing an initial render
    init_resp = await client.get(
        f"/ersv/outbound/{cons_id}?format=html",
        headers=admin_headers,
    )
    assert init_resp.status_code == 200
    initial_no = init_resp.headers.get("X-Ersv-Outbound-No")

    # Operator must be rejected
    op_resp = await client.post(
        f"/ersv/outbound/{cons_id}/regenerate",
        headers=operator_headers,
    )
    assert op_resp.status_code == 403, (
        f"Expected 403 for operator, got {op_resp.status_code}: {op_resp.text}"
    )

    # Admin must succeed
    admin_resp = await client.post(
        f"/ersv/outbound/{cons_id}/regenerate",
        headers=admin_headers,
    )
    assert admin_resp.status_code == 200, (
        f"Expected 200 for admin, got {admin_resp.status_code}: {admin_resp.text}"
    )
    data = admin_resp.json()
    assert data["consignment_id"] == cons_id
    assert data["previous_no"] == initial_no
    new_no = data["ersv_outbound_no"]
    assert re.match(r"^CO/\d{2}/\d{3}$", new_no), f"Bad format: {new_no!r}"
    # New number must be different from the old one
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
        db_session,
        crown_id,
        "CONS-ERSV-OUT-PDF",
        clear_outbound_no=True,
    )

    resp = await client.get(
        f"/ersv/outbound/{cons_id}?format=pdf",
        headers=admin_headers,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    content_type = resp.headers.get("content-type", "")
    assert "application/pdf" in content_type, (
        f"Expected application/pdf content-type, got {content_type!r}"
    )

    pdf_bytes = resp.content
    assert len(pdf_bytes) > 0, "PDF response must not be empty"

    # Verify it starts with the PDF magic bytes
    assert pdf_bytes[:4] == b"%PDF", (
        f"Response does not start with %PDF magic: {pdf_bytes[:8]!r}"
    )

    # X-Ersv-Outbound-No header must be present
    no_header = resp.headers.get("X-Ersv-Outbound-No")
    assert no_header is not None
    assert re.match(r"^CO/\d{2}/\d{3}$", no_header), f"Bad format: {no_header!r}"
