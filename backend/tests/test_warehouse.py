"""Test suite for /warehouse and /byproduct endpoints (migration 0026).

Coverage:
  - GET /warehouse/stock: 6 product_kind rows, eu_oil reserved_kg overlay,
    syngas in/out balance == 0
  - GET /warehouse/movements: product_kind filter
  - POST/GET/DELETE /byproduct/buyers (soft-delete CRUD)
  - POST /byproduct/sales: ledger event creation, stock decrement,
    rejection of eu_oil, soft-delete correction restores stock
  - Authn / role gating: anonymous → 401, viewer → 403 on writes

Dependencies:
  - Migration 0026_warehouse_inventory must be applied (mass_balance_ledger
    has product_kind column; byproduct_buyer + byproduct_sale tables; views
    v_warehouse_stock + v_warehouse_recent_movements)
  - /warehouse router registered in app.main (currently not — tests that hit
    it will 404 until app.main:app.include_router(warehouse.router) lands)
  - /byproduct router does NOT exist yet — tests 5-8, 10 will fail until the
    router is added. Marked accordingly with a shared dependency note.

All test rows use the ``TEST-WH-`` / ``TEST-BUYER-`` prefix so the autouse
cleanup in conftest.py can reach them. Direct ledger inserts are tagged with
ref_table='_test_warehouse' so the post-test purge below can remove them
without touching production data.
"""
from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator  # noqa: TC003 — used in runtime annotations
from datetime import date
from decimal import Decimal

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
_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    _engine, expire_on_commit=False
)


async def _override_get_db() -> AsyncIterator[AsyncSession]:
    async with _factory() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_TEST_REF_TABLE = "_test_warehouse"


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def viewer_headers() -> dict[str, str]:
    """Headers for a viewer-authenticated request.

    NOTE: conftest auth override only distinguishes ``test-operator-token`` from
    everything-else (admin). We install a token-aware override that:
      - returns viewer for ``test-viewer-token``,
      - returns operator for ``test-operator-token``,
      - returns admin otherwise.
    This keeps admin/operator fixtures functional within the same test.
    """
    from fastapi import Depends
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

    from app.routers.auth import _get_current_user

    _bearer = HTTPBearer(auto_error=False)

    class _Usr:
        def __init__(self, uid: int, role: str, email: str) -> None:
            self.id = uid
            self.role = role
            self.email = email
            self.active = True
            self.full_name = f"Test {role.capitalize()}"
            self.password_hash = None

    async def _override(
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),  # noqa: B008
    ) -> _Usr:
        if credentials is None:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        token = credentials.credentials
        if token == "test-viewer-token":  # noqa: S105 — test fixture JWT, not a secret
            return _Usr(3, "viewer", "viewer@test")
        if token == "test-operator-token":  # noqa: S105 — test fixture JWT, not a secret
            return _Usr(2, "operator", "operator@test")
        return _Usr(1, "admin", "admin@test")

    prev = app.dependency_overrides.get(_get_current_user)
    app.dependency_overrides[_get_current_user] = _override
    try:
        yield {"Authorization": "Bearer test-viewer-token"}
    finally:
        if prev is None:
            app.dependency_overrides.pop(_get_current_user, None)
        else:
            app.dependency_overrides[_get_current_user] = prev


@pytest_asyncio.fixture(autouse=True)
async def _purge_warehouse_scratch() -> AsyncIterator[None]:
    """Soft-delete + hard-purge any test ledger / byproduct rows.

    Runs before AND after each test. Uses ``ref_table = '_test_warehouse'``
    on the ledger and the ``TEST-WH-`` / ``TEST-BUYER-`` prefixes on
    byproduct_buyer rows.
    """

    async def _purge() -> None:
        async with _factory() as session:
            # Hard-delete test ledger rows (test-only sentinel ref_table)
            await session.execute(
                text(
                    "DELETE FROM mass_balance_ledger "
                    "WHERE ref_table = :ref_table"
                ),
                {"ref_table": _TEST_REF_TABLE},
            )
            # Soft-delete byproduct_sale rows that reference test buyers
            await session.execute(
                text(
                    """
                    UPDATE byproduct_sale
                       SET deleted_at = COALESCE(deleted_at, NOW())
                     WHERE buyer_id IN (
                        SELECT id FROM byproduct_buyer
                         WHERE name LIKE 'TEST-WH-%'
                            OR name LIKE 'TEST-BUYER-%'
                     )
                       AND deleted_at IS NULL
                    """
                )
            )
            # Soft-delete + tombstone byproduct_buyer scratch rows
            await session.execute(
                text(
                    """
                    UPDATE byproduct_buyer
                       SET deleted_at = COALESCE(deleted_at, NOW()),
                           name       = name || '__expired_' || id
                     WHERE (name LIKE 'TEST-WH-%' OR name LIKE 'TEST-BUYER-%')
                       AND name NOT LIKE '%__expired_%'
                    """
                )
            )
            await session.commit()

    await _purge()
    yield
    await _purge()


async def _seed_ledger_row(
    session: AsyncSession,
    *,
    event_type: str,
    product_kind: str,
    kg_in: Decimal | None = None,
    kg_out: Decimal | None = None,
    event_date: date | None = None,
    ref_id: int | None = None,
) -> int:
    """Insert a scratch ledger row tagged for test-only cleanup. Returns id."""
    ref_id_val = ref_id if ref_id is not None else int(uuid.uuid4().int >> 96)
    result = await session.execute(
        text(
            """
            INSERT INTO mass_balance_ledger
                (event_type, event_date, kg_in, kg_out, ref_table, ref_id,
                 product_kind)
            VALUES (:event_type, :event_date, :kg_in, :kg_out,
                    :ref_table, :ref_id, :product_kind)
            RETURNING id
            """
        ),
        {
            "event_type": event_type,
            "event_date": event_date or date.today(),
            "kg_in": kg_in,
            "kg_out": kg_out,
            "ref_table": _TEST_REF_TABLE,
            "ref_id": ref_id_val,
            "product_kind": product_kind,
        },
    )
    row_id = int(result.scalar_one())
    await session.commit()
    return row_id


# ---------------------------------------------------------------------------
# 1. /warehouse/stock returns one row per product_kind
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_warehouse_stock_returns_six_product_kinds(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """Seed an ``opening`` event for every product_kind; expect 6 stock rows."""
    expected_kinds = {
        "eu_oil",
        "plus_oil",
        "carbon_black",
        "metal_scrap",
        "syngas",
        "h2o",
    }
    for kind in expected_kinds:
        await _seed_ledger_row(
            db_session,
            event_type="opening",
            product_kind=kind,
            kg_in=Decimal("1.000"),
        )

    resp = await client.get("/warehouse/stock", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    kinds_present = {r["product_kind"] for r in rows}
    assert expected_kinds.issubset(kinds_present), (
        f"Missing kinds: {expected_kinds - kinds_present}"
    )


# ---------------------------------------------------------------------------
# 2. /warehouse/stock — eu_oil.reserved_kg reflects at_utb consignments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_warehouse_stock_eu_oil_reserved_kg(
    client: AsyncClient,
    admin_headers: dict[str, str],
    crown_oil_off_taker: dict[str, object],
    db_session: AsyncSession,
) -> None:
    """A 1000-kg consignment at status='at_utb' must appear in eu_oil.reserved_kg."""
    crown_oil_id = int(crown_oil_off_taker["id"])

    cons_resp = await client.post(
        "/consignments",
        json={
            "code": "CONS-TEST-RESERVED-KG",
            "off_taker_id": crown_oil_id,
            "product_grade": "DEV-P100",
            "total_kg": "1000.000",
            "status": "at_utb",
        },
        headers=admin_headers,
    )
    assert cons_resp.status_code == 201, cons_resp.text

    # Ensure eu_oil row exists in the stock view
    await _seed_ledger_row(
        db_session,
        event_type="opening",
        product_kind="eu_oil",
        kg_in=Decimal("1.000"),
    )

    resp = await client.get("/warehouse/stock", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    eu_oil = next((r for r in rows if r["product_kind"] == "eu_oil"), None)
    assert eu_oil is not None, "eu_oil row missing from /warehouse/stock"
    # Other live at_utb / draft / loaded consignments in the DB may exist; we
    # asserted the floor — the new 1000 kg must be additive.
    assert Decimal(eu_oil["reserved_kg"]) >= Decimal("1000.000"), (
        f"Expected reserved_kg >= 1000, got {eu_oil['reserved_kg']}"
    )


# ---------------------------------------------------------------------------
# 3. /warehouse/stock — syngas in == out → stock_kg == 0
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_warehouse_stock_syngas_balance_is_zero(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """Production +500 then syngas_burn -500 → net syngas stock 0."""
    # Wipe any pre-existing syngas rows in the test sandbox to make the
    # assertion deterministic — production data uses real ref_table names so
    # this delete only touches test-seeded rows.
    await db_session.execute(
        text(
            "DELETE FROM mass_balance_ledger "
            "WHERE ref_table = :ref AND product_kind = 'syngas'"
        ),
        {"ref": _TEST_REF_TABLE},
    )
    await db_session.commit()

    # If production has real syngas rows, capture the baseline and just verify
    # our delta-zero pair doesn't shift it.
    baseline_result = await db_session.execute(
        text(
            "SELECT COALESCE(stock_kg, 0) FROM v_warehouse_stock "
            "WHERE product_kind = 'syngas'"
        )
    )
    baseline = Decimal(baseline_result.scalar() or 0)

    await _seed_ledger_row(
        db_session,
        event_type="production",
        product_kind="syngas",
        kg_in=Decimal("500.000"),
    )
    await _seed_ledger_row(
        db_session,
        event_type="syngas_burn",
        product_kind="syngas",
        kg_out=Decimal("500.000"),
    )

    resp = await client.get("/warehouse/stock", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    syngas = next(
        (r for r in resp.json() if r["product_kind"] == "syngas"), None
    )
    assert syngas is not None, "syngas row missing"
    assert Decimal(syngas["stock_kg"]) == baseline, (
        f"Expected syngas stock unchanged from baseline {baseline}, "
        f"got {syngas['stock_kg']}"
    )


# ---------------------------------------------------------------------------
# 4. /warehouse/movements — product_kind filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_warehouse_movements_filter_by_product_kind(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """?product_kind=carbon_black yields only carbon_black rows."""
    await _seed_ledger_row(
        db_session,
        event_type="production",
        product_kind="carbon_black",
        kg_in=Decimal("250.000"),
    )
    await _seed_ledger_row(
        db_session,
        event_type="production",
        product_kind="metal_scrap",
        kg_in=Decimal("75.000"),
    )

    resp = await client.get(
        "/warehouse/movements",
        params={"product_kind": "carbon_black", "limit": 100},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert rows, "Expected at least one carbon_black movement"
    assert all(r["product_kind"] == "carbon_black" for r in rows), (
        "Filter leaked non-carbon_black rows: "
        f"{[r['product_kind'] for r in rows]}"
    )


# ---------------------------------------------------------------------------
# 5. /byproduct/buyers — CRUD lifecycle with soft-delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_byproduct_buyers_crud(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """POST → 201, GET → list contains, DELETE → 204, GET → not listed."""
    create_resp = await client.post(
        "/byproduct/buyers",
        json={
            "name": "TEST-WH-BUYER-CRUD",
            "country": "DE",
            "vat": "DE123456789",
            "contact": "buyer@example.com",
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    buyer = create_resp.json()
    buyer_id = buyer["id"]
    assert buyer["name"] == "TEST-WH-BUYER-CRUD"

    # List contains the new buyer
    list_resp = await client.get("/byproduct/buyers", headers=admin_headers)
    assert list_resp.status_code == 200, list_resp.text
    assert any(b["id"] == buyer_id for b in list_resp.json()), (
        f"New buyer {buyer_id} not in GET /byproduct/buyers"
    )

    # Soft delete
    del_resp = await client.delete(
        f"/byproduct/buyers/{buyer_id}", headers=admin_headers
    )
    assert del_resp.status_code == 204, del_resp.text

    # List excludes deleted
    list_after = await client.get("/byproduct/buyers", headers=admin_headers)
    assert list_after.status_code == 200, list_after.text
    assert not any(b["id"] == buyer_id for b in list_after.json()), (
        "Soft-deleted buyer still visible in GET /byproduct/buyers"
    )


# ---------------------------------------------------------------------------
# 6. /byproduct/sales — creates ledger event + decrements stock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_byproduct_sale_creates_ledger_event(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """POST sale → ledger row with event_type='byproduct_sale', stock drops."""
    # Seed a buyer
    buyer_resp = await client.post(
        "/byproduct/buyers",
        json={"name": "TEST-WH-BUYER-SALE", "country": "DE"},
        headers=admin_headers,
    )
    assert buyer_resp.status_code == 201, buyer_resp.text
    buyer_id = buyer_resp.json()["id"]

    # Seed enough carbon_black stock to satisfy the sale
    await _seed_ledger_row(
        db_session,
        event_type="production",
        product_kind="carbon_black",
        kg_in=Decimal("500.000"),
    )

    stock_before = await client.get("/warehouse/stock", headers=admin_headers)
    cb_before = next(
        (r for r in stock_before.json() if r["product_kind"] == "carbon_black"),
        None,
    )
    assert cb_before is not None
    stock_kg_before = Decimal(cb_before["stock_kg"])

    sale_resp = await client.post(
        "/byproduct/sales",
        json={
            "product_kind": "carbon_black",
            "buyer_id": buyer_id,
            "sale_date": date.today().isoformat(),
            "kg_net": "100.000",
            "invoice_no": "INV-TEST-WH-0001",
        },
        headers=admin_headers,
    )
    assert sale_resp.status_code == 201, sale_resp.text

    # Ledger should now have one byproduct_sale row for carbon_black, kg_out=100
    ledger_check = await db_session.execute(
        text(
            """
            SELECT COUNT(*) FROM mass_balance_ledger
             WHERE event_type = 'byproduct_sale'
               AND product_kind = 'carbon_black'
               AND kg_out = 100.000
               AND deleted_at IS NULL
            """
        )
    )
    count = int(ledger_check.scalar_one())
    assert count >= 1, (
        f"Expected >= 1 ledger row event_type='byproduct_sale' "
        f"product_kind='carbon_black' kg_out=100; got {count}"
    )

    # Stock decreased by 100
    stock_after = await client.get("/warehouse/stock", headers=admin_headers)
    cb_after = next(
        (r for r in stock_after.json() if r["product_kind"] == "carbon_black"),
        None,
    )
    assert cb_after is not None
    assert Decimal(cb_after["stock_kg"]) == stock_kg_before - Decimal("100.000"), (
        f"Expected stock to drop by 100 kg; before={stock_kg_before} "
        f"after={cb_after['stock_kg']}"
    )


# ---------------------------------------------------------------------------
# 7. /byproduct/sales — eu_oil is not a sellable byproduct
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_byproduct_sale_rejects_oil_eu(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """eu_oil must be rejected by the SellableKind enum → 422."""
    buyer_resp = await client.post(
        "/byproduct/buyers",
        json={"name": "TEST-WH-BUYER-REJECT-EU"},
        headers=admin_headers,
    )
    assert buyer_resp.status_code == 201, buyer_resp.text
    buyer_id = buyer_resp.json()["id"]

    resp = await client.post(
        "/byproduct/sales",
        json={
            "product_kind": "eu_oil",  # NOT in SellableKind
            "buyer_id": buyer_id,
            "sale_date": date.today().isoformat(),
            "kg_net": "100.000",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 422, (
        f"Expected 422 for product_kind=eu_oil byproduct sale; "
        f"got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 8. /byproduct/sales — soft-delete writes a correction row + restores stock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_byproduct_sale_soft_delete_inserts_correction(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """Deleting a sale should append a correction row and restore stock."""
    buyer_resp = await client.post(
        "/byproduct/buyers",
        json={"name": "TEST-WH-BUYER-CORRECTION"},
        headers=admin_headers,
    )
    assert buyer_resp.status_code == 201, buyer_resp.text
    buyer_id = buyer_resp.json()["id"]

    await _seed_ledger_row(
        db_session,
        event_type="production",
        product_kind="metal_scrap",
        kg_in=Decimal("400.000"),
    )

    pre_sale_stock = await client.get("/warehouse/stock", headers=admin_headers)
    ms_pre = next(
        (r for r in pre_sale_stock.json() if r["product_kind"] == "metal_scrap"),
        None,
    )
    assert ms_pre is not None
    stock_pre = Decimal(ms_pre["stock_kg"])

    sale_resp = await client.post(
        "/byproduct/sales",
        json={
            "product_kind": "metal_scrap",
            "buyer_id": buyer_id,
            "sale_date": date.today().isoformat(),
            "kg_net": "120.000",
        },
        headers=admin_headers,
    )
    assert sale_resp.status_code == 201, sale_resp.text
    sale_id = sale_resp.json()["id"]

    # Find the original ledger row tied to this sale (most recent byproduct_sale
    # event for metal_scrap with kg_out=120 wired to this sale.id).
    original_id_row = await db_session.execute(
        text(
            """
            SELECT id FROM mass_balance_ledger
             WHERE event_type = 'byproduct_sale'
               AND product_kind = 'metal_scrap'
               AND ref_id = :sale_id
               AND deleted_at IS NULL
             ORDER BY id DESC
             LIMIT 1
            """
        ),
        {"sale_id": sale_id},
    )
    original_id = original_id_row.scalar()
    assert original_id is not None, (
        "Original byproduct_sale ledger row not found by ref_id"
    )

    # Soft-delete the sale
    del_resp = await client.delete(
        f"/byproduct/sales/{sale_id}", headers=admin_headers
    )
    assert del_resp.status_code == 204, del_resp.text

    # Correction row must exist pointing back at the original
    correction_count = await db_session.execute(
        text(
            """
            SELECT COUNT(*) FROM mass_balance_ledger
             WHERE event_type = 'correction'
               AND corrects_id = :orig
               AND deleted_at IS NULL
            """
        ),
        {"orig": int(original_id)},
    )
    assert int(correction_count.scalar_one()) == 1, (
        "Expected exactly one correction row for the deleted sale"
    )

    # Stock restored
    post_del_stock = await client.get("/warehouse/stock", headers=admin_headers)
    ms_post = next(
        (
            r for r in post_del_stock.json()
            if r["product_kind"] == "metal_scrap"
        ),
        None,
    )
    assert ms_post is not None
    assert Decimal(ms_post["stock_kg"]) == stock_pre, (
        f"Expected stock restored to {stock_pre}; got {ms_post['stock_kg']}"
    )


# ---------------------------------------------------------------------------
# 9. /warehouse/stock — anonymous request → 401
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_warehouse_auth_required(client: AsyncClient) -> None:
    """No Authorization header → 401 from /warehouse/stock."""
    resp = await client.get("/warehouse/stock")
    assert resp.status_code == 401, (
        f"Expected 401 without auth; got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 10. /byproduct/sales — viewer cannot create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_byproduct_sale_create_requires_operator_or_admin(
    client: AsyncClient,
    admin_headers: dict[str, str],
    viewer_headers: dict[str, str],
) -> None:
    """Viewer JWT POSTing a sale must be rejected with 403."""
    # Admin seeds a buyer so the request body is otherwise valid
    buyer_resp = await client.post(
        "/byproduct/buyers",
        json={"name": "TEST-WH-BUYER-VIEWER-DENY"},
        headers=admin_headers,
    )
    assert buyer_resp.status_code == 201, buyer_resp.text
    buyer_id = buyer_resp.json()["id"]

    resp = await client.post(
        "/byproduct/sales",
        json={
            "product_kind": "carbon_black",
            "buyer_id": buyer_id,
            "sale_date": date.today().isoformat(),
            "kg_net": "10.000",
        },
        headers=viewer_headers,
    )
    assert resp.status_code == 403, (
        f"Expected 403 for viewer POST /byproduct/sales; "
        f"got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 11. /warehouse/stock — product_kind filter narrows to a single product
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_warehouse_stock_filter_by_product_kind(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """?product_kind=eu_oil returns only the eu_oil row (0 or 1 element)."""
    # Seed an eu_oil opening so the view definitely has a row to filter to.
    await _seed_ledger_row(
        db_session,
        event_type="opening",
        product_kind="eu_oil",
        kg_in=Decimal("1.000"),
    )

    resp = await client.get(
        "/warehouse/stock",
        params={"product_kind": "eu_oil"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) == 1, (
        f"Expected exactly 1 row for product_kind=eu_oil; got {len(rows)}"
    )
    assert rows[0]["product_kind"] == "eu_oil"


# ---------------------------------------------------------------------------
# 12. /warehouse/stock — invalid product_kind → 400
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_warehouse_stock_invalid_product_kind_rejected(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """A product_kind outside the 6-value enum returns 400 with the allowed list."""
    resp = await client.get(
        "/warehouse/stock",
        params={"product_kind": "bogus"},
        headers=admin_headers,
    )
    assert resp.status_code == 400, (
        f"Expected 400 for bogus product_kind; "
        f"got {resp.status_code}: {resp.text}"
    )
    detail = resp.json().get("detail", "")
    assert "eu_oil" in detail and "h2o" in detail, (
        f"Expected 400 detail to enumerate allowed values; got {detail!r}"
    )
