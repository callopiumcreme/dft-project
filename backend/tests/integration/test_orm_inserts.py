"""ORM <-> DB drift checks for the consignment_pos table.

Covers E8-C1 (surrogate PK) and E8-C2 (issuance_date column):

- The ORM model must declare ``id`` as the sole primary key — composite PK
  on ``(consignment_id, pos_number)`` was dropped by migration 0028 and any
  INSERT against the old composite PK now raises ``NotNullViolationError``
  because the surrogate ``id`` would be left unset.
- The ORM model must expose ``issuance_date`` so application code can read
  and write it through ``Mapped[date | None]`` instead of falling back to
  raw SQL (warehouse.py prior workaround).

These are pure ORM-layer assertions plus a smoke-test INSERT that touches
the real DB so any future drift between migration and model surfaces
immediately. The INSERT path uses the ``CONS-TEST-ORM`` scratch prefix so
the autouse cleanup fixture in ``conftest.py`` tombstones the row after
the test completes.
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consignment import Consignment
from app.models.consignment_pos import ConsignmentPos


# ---------------------------------------------------------------------------
# C1 — surrogate PK assertions (pure ORM, no DB needed)
# ---------------------------------------------------------------------------


def test_consignment_pos_pk_is_surrogate_id() -> None:
    """E8-C1: ConsignmentPos.__table__ primary key must be ``id`` only.

    Migration 0028 dropped the composite PK on (consignment_id, pos_number)
    and introduced ``id BIGSERIAL PRIMARY KEY``. The ORM model has to
    match or every INSERT will fail with ``NotNullViolationError`` on
    ``id`` because SQLAlchemy will not generate a value for a column it
    does not consider part of the primary key.
    """
    pk_cols = [c.name for c in ConsignmentPos.__table__.primary_key.columns]
    assert pk_cols == ["id"], (
        f"Expected PK = ['id'] after 0028; got {pk_cols}. "
        "ORM is still keyed on the old composite PK."
    )


def test_consignment_pos_has_partial_unique_index() -> None:
    """E8-C1: natural key uniqueness must survive on active rows only.

    Migration 0028 created ``ux_consignment_pos_active`` as a partial
    UNIQUE index on (consignment_id, pos_number) WHERE deleted_at IS NULL.
    The ORM declares it via ``__table_args__`` so Alembic autogenerate
    stays in sync with the live schema.
    """
    indexes = {idx.name: idx for idx in ConsignmentPos.__table__.indexes}
    assert "ux_consignment_pos_active" in indexes, (
        "Missing ux_consignment_pos_active index in ORM __table_args__"
    )
    idx = indexes["ux_consignment_pos_active"]
    assert idx.unique is True, "Index must be UNIQUE"
    col_names = [c.name for c in idx.columns]
    assert col_names == ["consignment_id", "pos_number"], (
        f"Index columns mismatch: {col_names}"
    )


# ---------------------------------------------------------------------------
# C2 — issuance_date column must be a Mapped ORM attribute
# ---------------------------------------------------------------------------


def test_consignment_pos_exposes_issuance_date() -> None:
    """E8-C2: ConsignmentPos.issuance_date must be a real Mapped attribute.

    Migration 0027 added ``issuance_date date`` to the table; without the
    ORM attribute, ``warehouse.py`` had to fall back to a raw SQL
    workaround to GROUP BY year. The attribute must be present and the
    underlying column must be the ``date`` type.
    """
    assert hasattr(ConsignmentPos, "issuance_date"), (
        "ConsignmentPos missing issuance_date attribute (DFTEN-172)"
    )
    col = ConsignmentPos.__table__.columns["issuance_date"]
    # Python type for sqlalchemy.Date is ``datetime.date``.
    assert col.type.python_type is date, (
        f"issuance_date type should map to datetime.date; got {col.type}"
    )
    assert col.nullable is True, "issuance_date must be NULL-able"


# ---------------------------------------------------------------------------
# Live INSERT smoke-test — exercise the full path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orm_insert_uses_surrogate_id_and_persists_issuance_date(
    db_session: AsyncSession,
    crown_oil_off_taker: dict[str, object],
) -> None:
    """End-to-end INSERT proving the ORM round-trips both fixes.

    Creates a throwaway consignment under the ``CONS-TEST-ORM`` scratch
    prefix (cleaned up by the autouse fixture), attaches a ConsignmentPos
    with an ``issuance_date``, then re-fetches by surrogate ``id``.

    This guards against regressions where:
      * the ORM PK drifts back to composite (INSERT fails on id NOT NULL)
      * issuance_date is dropped from the model (write silently lost)
    """
    # 1. Parent consignment using the registered scratch prefix.
    parent = Consignment(
        code="CONS-TEST-ORM-PK",
        off_taker_id=int(crown_oil_off_taker["id"]),
        product_grade="DEV-P100",
        status="draft",
    )
    db_session.add(parent)
    await db_session.flush()
    parent_id = parent.id

    # 2. ConsignmentPos INSERT — surrogate id auto-populated by BIGSERIAL.
    pos = ConsignmentPos(
        consignment_id=parent_id,
        pos_number="ORM-TEST-001",
        kg_net=None,
        issuance_date=date(2025, 6, 15),
    )
    db_session.add(pos)
    await db_session.flush()

    assert pos.id is not None, "Surrogate id must be auto-assigned by BIGSERIAL"
    assert isinstance(pos.id, int)

    # 3. Re-fetch by surrogate id to confirm persistence + issuance_date.
    fetched = (
        await db_session.execute(
            select(ConsignmentPos).where(ConsignmentPos.id == pos.id)
        )
    ).scalar_one()
    assert fetched.issuance_date == date(2025, 6, 15)
    assert fetched.consignment_id == parent_id
    assert fetched.pos_number == "ORM-TEST-001"

    # Rollback so the autouse cleanup only sees the parent consignment
    # (scratch prefix triggers the cascade tombstone).
    await db_session.commit()
