"""Unit tests for ByproductBuyer + ByproductSale ORM models (DFTEN-175).

Goals:
  - Instantiate both models against the live DB schema (migration 0026).
  - Verify FK integrity: byproduct_sale.buyer_id → byproduct_buyer.id
    with ON DELETE RESTRICT semantics (deleting a buyer with active
    sales must fail).
  - Verify CHECK constraints surface as IntegrityError:
      * product_kind must be one of plus_oil / carbon_black / metal_scrap
      * kg_net must be > 0
  - Soft-delete via deleted_at preserves both rows.

All scratch rows use the ``TEST-MODEL-BP-`` prefix on ``byproduct_buyer.name``
and ``TEST-MODEL-INV-`` on ``byproduct_sale.invoice_no`` so the autouse
purge below leaves no residue.
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator  # noqa: TC003 — used in runtime annotations
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.models.byproduct_buyer import ByproductBuyer
from app.models.byproduct_sale import ByproductSale

# Engine + factory mirror tests/test_warehouse.py to reuse the docker DB.
_engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    _engine, expire_on_commit=False
)

_BUYER_PREFIX = "TEST-MODEL-BP-"
_INVOICE_PREFIX = "TEST-MODEL-INV-"


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with _factory() as s:
        yield s


@pytest_asyncio.fixture(autouse=True)
async def _purge() -> AsyncIterator[None]:
    """Soft-delete + tombstone scratch rows before AND after each test."""

    async def _run() -> None:
        async with _factory() as s:
            # Soft-delete sales tied to scratch buyers OR with the scratch invoice prefix.
            await s.execute(
                text(
                    """
                    UPDATE byproduct_sale
                       SET deleted_at = COALESCE(deleted_at, NOW())
                     WHERE (invoice_no LIKE :inv_pref
                            OR buyer_id IN (
                                SELECT id FROM byproduct_buyer
                                 WHERE name LIKE :buyer_pref
                            ))
                       AND deleted_at IS NULL
                    """
                ),
                {"inv_pref": f"{_INVOICE_PREFIX}%", "buyer_pref": f"{_BUYER_PREFIX}%"},
            )
            # Soft-delete + tombstone-rename buyers so the unique-active-name
            # constraint is freed for the next run.
            await s.execute(
                text(
                    """
                    UPDATE byproduct_buyer
                       SET deleted_at = COALESCE(deleted_at, NOW()),
                           name       = name || '__expired_' || id
                     WHERE name LIKE :buyer_pref
                       AND name NOT LIKE '%__expired_%'
                    """
                ),
                {"buyer_pref": f"{_BUYER_PREFIX}%"},
            )
            await s.commit()

    await _run()
    yield
    await _run()


@pytest.mark.asyncio
async def test_byproduct_buyer_insert_roundtrip(session: AsyncSession) -> None:
    """ByproductBuyer instantiates, persists, and round-trips via SELECT."""
    buyer = ByproductBuyer(
        name=f"{_BUYER_PREFIX}ACME",
        country="DE",
        vat="DE123456789",
        contact="ops@acme.example",
        notes="model-test fixture",
    )
    session.add(buyer)
    await session.commit()
    await session.refresh(buyer)

    assert buyer.id is not None
    assert buyer.created_at is not None
    assert buyer.updated_at is not None
    assert buyer.deleted_at is None

    fetched = await session.scalar(
        select(ByproductBuyer).where(ByproductBuyer.id == buyer.id)
    )
    assert fetched is not None
    assert fetched.name == f"{_BUYER_PREFIX}ACME"
    assert fetched.country == "DE"


@pytest.mark.asyncio
async def test_byproduct_sale_insert_with_fk(session: AsyncSession) -> None:
    """ByproductSale persists and resolves its buyer FK relationship."""
    buyer = ByproductBuyer(name=f"{_BUYER_PREFIX}SALE-FK")
    session.add(buyer)
    await session.flush()
    assert buyer.id is not None

    sale = ByproductSale(
        product_kind="carbon_black",
        buyer_id=buyer.id,
        sale_date=date.today(),
        kg_net=Decimal("150.250"),
        invoice_no=f"{_INVOICE_PREFIX}001",
        price_eur=Decimal("1875.00"),
    )
    session.add(sale)
    await session.commit()
    await session.refresh(sale)

    assert sale.id is not None
    assert sale.buyer_id == buyer.id
    assert sale.kg_net == Decimal("150.250")
    assert sale.deleted_at is None


@pytest.mark.asyncio
async def test_byproduct_sale_invalid_product_kind_rejected(
    session: AsyncSession,
) -> None:
    """CHECK constraint blocks product_kind outside the sellable enum."""
    buyer = ByproductBuyer(name=f"{_BUYER_PREFIX}KIND-CHECK")
    session.add(buyer)
    await session.flush()
    assert buyer.id is not None

    sale = ByproductSale(
        product_kind="eu_oil",  # not a SellableKind
        buyer_id=buyer.id,
        sale_date=date.today(),
        kg_net=Decimal("1.000"),
        invoice_no=f"{_INVOICE_PREFIX}KIND",
    )
    session.add(sale)
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


@pytest.mark.asyncio
async def test_byproduct_sale_kg_net_must_be_positive(session: AsyncSession) -> None:
    """CHECK constraint blocks kg_net <= 0."""
    buyer = ByproductBuyer(name=f"{_BUYER_PREFIX}KG-CHECK")
    session.add(buyer)
    await session.flush()
    assert buyer.id is not None

    sale = ByproductSale(
        product_kind="metal_scrap",
        buyer_id=buyer.id,
        sale_date=date.today(),
        kg_net=Decimal("0.000"),
        invoice_no=f"{_INVOICE_PREFIX}KG",
    )
    session.add(sale)
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


@pytest.mark.asyncio
async def test_byproduct_sale_buyer_fk_restrict(session: AsyncSession) -> None:
    """ON DELETE RESTRICT: hard-deleting a buyer with active sales fails."""
    buyer = ByproductBuyer(name=f"{_BUYER_PREFIX}RESTRICT")
    session.add(buyer)
    await session.flush()
    assert buyer.id is not None

    sale = ByproductSale(
        product_kind="plus_oil",
        buyer_id=buyer.id,
        sale_date=date.today(),
        kg_net=Decimal("10.000"),
        invoice_no=f"{_INVOICE_PREFIX}RESTRICT",
    )
    session.add(sale)
    await session.commit()

    # Attempt a hard DELETE of the buyer — must violate the FK.
    with pytest.raises(IntegrityError):
        await session.execute(
            text("DELETE FROM byproduct_buyer WHERE id = :bid"),
            {"bid": buyer.id},
        )
        await session.commit()
    await session.rollback()


@pytest.mark.asyncio
async def test_byproduct_buyer_soft_delete(session: AsyncSession) -> None:
    """Setting deleted_at preserves the row (no hard delete required)."""
    buyer = ByproductBuyer(name=f"{_BUYER_PREFIX}SOFT")
    session.add(buyer)
    await session.commit()
    await session.refresh(buyer)
    bid = buyer.id

    buyer.deleted_at = datetime.now(tz=UTC)
    await session.commit()

    fetched = await session.scalar(
        select(ByproductBuyer).where(ByproductBuyer.id == bid)
    )
    assert fetched is not None
    assert fetched.deleted_at is not None
