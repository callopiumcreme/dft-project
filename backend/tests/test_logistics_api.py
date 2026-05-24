"""Test suite for logistics downstream API.

Tests:
  - Happy path: create off_taker → create consignment → add 2 legs → add units → GET detail
  - Validation: kg_in < kg_out → 422
  - Validation: utb_transload without kg_stock_residual → 422
  - Soft delete: DELETE consignment → GET returns 404; DB row still exists
  - Status auto-advance: delivery_uk leg creation advances consignment to delivered_uk
"""
from __future__ import annotations

import os
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


async def _override_get_db() -> AsyncIterator[AsyncSession]:
    async with _factory() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(admin_headers: dict[str, str]) -> dict[str, str]:
    """Back-compat alias used by tests below — admin-authenticated headers."""
    return admin_headers


@pytest_asyncio.fixture
async def crown_oil_id(crown_oil_off_taker: dict[str, object]) -> int:
    """Ensure Crown Oil UK off_taker exists; return its id."""
    return int(crown_oil_off_taker["id"])


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_full_chain(
    client: AsyncClient,
    auth_headers: dict[str, str],
    crown_oil_id: int,
    db_session: AsyncSession,
) -> None:
    """Create off_taker → consignment → 2 legs → units → GET detail returns full chain."""

    # 1. Create an additional off_taker via API to verify endpoint
    ot_resp = await client.post(
        "/off-takers",
        json={
            "code": "TEST-BUYER-001",
            "name": "Test Buyer Ltd",
            "country": "DE",
            "address": "Berlin, DE",
        },
        headers=auth_headers,
    )
    assert ot_resp.status_code == 201, ot_resp.text
    ot_data = ot_resp.json()
    assert ot_data["code"] == "TEST-BUYER-001"
    assert ot_data["deleted_at"] is None

    # 2. Create consignment linked to Crown Oil
    cons_resp = await client.post(
        "/consignments",
        json={
            "code": "CONS-TEST-2025-HP",
            "off_taker_id": crown_oil_id,
            "product_grade": "DEV-P100",
            "prod_date_from": "2025-06-01",
            "prod_date_to": "2025-08-31",
            "total_kg": "576270.000",
            "status": "draft",
        },
        headers=auth_headers,
    )
    assert cons_resp.status_code == 201, cons_resp.text
    cons_id = cons_resp.json()["id"]

    # 3. Add first leg: bl_ocean
    leg1_resp = await client.post(
        "/shipments/legs",
        json={
            "consignment_id": cons_id,
            "seq": 1,
            "leg_type": "bl_ocean",
            "document_type": "BL_ocean",
            "document_ref": "CMDU856254189",
            "carrier": "CARTAGENA EXPRES 007CONU",
            "origin_node": "Cartagena",
            "destination_node": "Rotterdam",
            "kg_in": "298129.000",
            "kg_out": "298129.000",
        },
        headers=auth_headers,
    )
    assert leg1_resp.status_code == 201, leg1_resp.text
    leg1_id = leg1_resp.json()["id"]

    # 4. Add a container unit to leg1
    unit_resp = await client.post(
        f"/shipments/legs/{leg1_id}/units",
        json={
            "container_ref": "PCVU3502178",
            "kg_net": "9937.633",
        },
        headers=auth_headers,
    )
    assert unit_resp.status_code == 201, unit_resp.text
    assert unit_resp.json()["container_ref"] == "PCVU3502178"

    # 5. Add second leg: delivery_uk (triggers auto-status-advance)
    leg2_resp = await client.post(
        "/shipments/legs",
        json={
            "consignment_id": cons_id,
            "seq": 2,
            "leg_type": "delivery_uk",
            "document_type": "commercial_invoice",
            "document_ref": "JLY001",
            "origin_node": "Bury",
            "destination_node": "Bury",
            "kg_in": "298129.000",
            "kg_out": "298129.000",
        },
        headers=auth_headers,
    )
    assert leg2_resp.status_code == 201, leg2_resp.text

    # 6. Verify consignment auto-advanced to delivered_uk
    detail_resp = await client.get(f"/consignments/{cons_id}", headers=auth_headers)
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()
    assert detail["status"] == "delivered_uk", (
        f"Expected status=delivered_uk after delivery_uk leg; got {detail['status']}"
    )

    # 7. Verify full ConsignmentDetail structure
    assert detail["off_taker"] is not None
    assert detail["off_taker"]["id"] == crown_oil_id
    assert len(detail["legs"]) == 2
    assert detail["legs"][0]["seq"] == 1
    assert detail["legs"][1]["seq"] == 2
    # leg1 should have 1 unit
    assert len(detail["legs"][0]["units"]) == 1
    assert detail["legs"][0]["units"][0]["container_ref"] == "PCVU3502178"
    # pos and production_links start empty
    assert detail["pos"] == []
    assert detail["production_links"] == []

    # 8. Attach a PoS
    pos_resp = await client.post(
        f"/consignments/{cons_id}/pos",
        json={"pos_number": "OISCRO-0013-25", "kg_net": "9937.633"},
        headers=auth_headers,
    )
    assert pos_resp.status_code == 201, pos_resp.text

    # 9. Attach a production link
    link_resp = await client.post(
        f"/consignments/{cons_id}/production-links",
        json={"prod_date": "2025-06-15", "kg_allocated": "5000.000"},
        headers=auth_headers,
    )
    assert link_resp.status_code == 201, link_resp.text

    # 10. GET detail again — pos and links now populated
    detail2 = (await client.get(f"/consignments/{cons_id}", headers=auth_headers)).json()
    assert len(detail2["pos"]) == 1
    assert detail2["pos"][0]["pos_number"] == "OISCRO-0013-25"
    assert len(detail2["production_links"]) == 1
    assert detail2["production_links"][0]["prod_date"] == "2025-06-15"

    # 11. Cleanup: delete test off-taker created in step 1
    del_ot = await client.delete(f"/off-takers/{ot_data['id']}", headers=auth_headers)
    assert del_ot.status_code == 204


# ---------------------------------------------------------------------------
# Validation: kg_in < kg_out → 422
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_leg_kg_in_less_than_kg_out_returns_422(
    client: AsyncClient,
    auth_headers: dict[str, str],
    crown_oil_id: int,
) -> None:
    """Creating a leg where kg_in < kg_out must return 422."""
    # Create a throwaway consignment
    cons_resp = await client.post(
        "/consignments",
        json={
            "code": "CONS-VALIDATE-KG-422",
            "off_taker_id": crown_oil_id,
            "product_grade": "DEV-P100",
            "status": "draft",
        },
        headers=auth_headers,
    )
    assert cons_resp.status_code == 201, cons_resp.text
    cons_id = cons_resp.json()["id"]

    resp = await client.post(
        "/shipments/legs",
        json={
            "consignment_id": cons_id,
            "seq": 1,
            "leg_type": "bl_ocean",
            "document_type": "BL_ocean",
            "origin_node": "Cartagena",
            "destination_node": "Rotterdam",
            "kg_in": "100.000",   # LESS than kg_out
            "kg_out": "200.000",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
    assert "kg_in" in resp.text or "mass" in resp.text.lower()

    # Cleanup
    await client.delete(f"/consignments/{cons_id}", headers=auth_headers)


# ---------------------------------------------------------------------------
# Validation: utb_transload without kg_stock_residual → 422
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_utb_transload_without_kg_stock_residual_returns_422(
    client: AsyncClient,
    auth_headers: dict[str, str],
    crown_oil_id: int,
) -> None:
    """utb_transload leg without kg_stock_residual must return 422."""
    cons_resp = await client.post(
        "/consignments",
        json={
            "code": "CONS-VALIDATE-UTB-422",
            "off_taker_id": crown_oil_id,
            "product_grade": "DEV-P100",
            "status": "draft",
        },
        headers=auth_headers,
    )
    assert cons_resp.status_code == 201, cons_resp.text
    cons_id = cons_resp.json()["id"]

    resp = await client.post(
        "/shipments/legs",
        json={
            "consignment_id": cons_id,
            "seq": 1,
            "leg_type": "utb_transload",
            "document_type": "transload_report",
            "origin_node": "Dordrecht (UTB BV)",
            "destination_node": "Dordrecht (UTB BV)",
            "kg_in": "576270.000",
            "kg_out": "500410.000",
            # kg_stock_residual intentionally omitted
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
    assert "kg_stock_residual" in resp.text

    # Cleanup
    await client.delete(f"/consignments/{cons_id}", headers=auth_headers)


# ---------------------------------------------------------------------------
# Soft delete: GET after DELETE returns 404; DB row still exists
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_soft_delete_consignment(
    client: AsyncClient,
    auth_headers: dict[str, str],
    crown_oil_id: int,
    db_session: AsyncSession,
) -> None:
    """DELETE consignment soft-deletes it; GET returns 404; DB row has deleted_at set."""
    cons_resp = await client.post(
        "/consignments",
        json={
            "code": "CONS-SOFT-DELETE-TEST",
            "off_taker_id": crown_oil_id,
            "product_grade": "DEV-P100",
            "status": "draft",
        },
        headers=auth_headers,
    )
    assert cons_resp.status_code == 201, cons_resp.text
    cons_id = cons_resp.json()["id"]

    # Soft delete
    del_resp = await client.delete(f"/consignments/{cons_id}", headers=auth_headers)
    assert del_resp.status_code == 204, del_resp.text

    # GET must return 404
    get_resp = await client.get(f"/consignments/{cons_id}", headers=auth_headers)
    assert get_resp.status_code == 404, (
        f"Expected 404 after soft-delete, got {get_resp.status_code}"
    )

    # DB row must still exist with deleted_at set (never hard-delete)
    row = await db_session.execute(
        text("SELECT id, deleted_at FROM consignment WHERE id = :id"),
        {"id": cons_id},
    )
    record = row.fetchone()
    assert record is not None, "DB row was hard-deleted — must use soft delete only"
    assert record[1] is not None, "deleted_at must be set after soft delete"
