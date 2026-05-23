"""Tests for the Q3-2025 Crown Oil consignment backfill.

These tests assert the final DB state produced by
scripts/backfill_consignment_2025q3.py.  They connect directly to the live
DB (same pattern as conftest.py / test_logistics_api.py).

Prerequisites:
    Run the backfill script at least once before executing this suite:
        DATABASE_URL=postgresql+asyncpg://dft:dftdev_2026@172.22.0.2:5432/dft \\
            python3 scripts/backfill_consignment_2025q3.py

Tests:
    test_backfill_idempotent
        Runs the backfill script via subprocess twice, then verifies that row
        counts are identical both times (idempotency).

    test_backfill_mass_balance_closes
        sum(shipment_unit.kg_net) == 576,270 ± 1 kg
        sum(consignment_pos.kg_net) + utb_residual == 576,270 ± 1 kg

    test_backfill_off_taker_singleton
        Exactly 1 non-deleted row with code='CROWN-OIL-UK'.
"""
from __future__ import annotations

import os
import subprocess
import sys
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# DB URL — identical to conftest.py default
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://dft:dftdev_2026@172.22.0.2:5432/dft")
os.environ.setdefault("JWT_SECRET", "changeme-dft-secret-key-2026")

BACKFILL_SCRIPT = (
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    + "/scripts/backfill_consignment_2025q3.py"
)

CONSIGNMENT_CODE = "CONS-2025-Q3-CROWN"
OFF_TAKER_CODE = "CROWN-OIL-UK"
EXPECTED_TOTAL_KG = Decimal("576270.000")
EXPECTED_DELIVERY_KG = Decimal("500410.000")
EXPECTED_UTB_RESIDUAL = Decimal("75860.000")
TOLERANCE = Decimal("1")


def _run_script() -> subprocess.CompletedProcess[str]:
    """Run the backfill script in a subprocess, inheriting DATABASE_URL."""
    env = os.environ.copy()
    result = subprocess.run(  # noqa: S603
        [sys.executable, BACKFILL_SCRIPT],
        capture_output=True,
        text=True,
        env=env,
    )
    return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db(db_session: AsyncSession) -> AsyncSession:
    """Alias for the shared db_session fixture from conftest.py."""
    return db_session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_backfill_idempotent(db: AsyncSession) -> None:
    """Running the backfill script twice must yield identical row counts.

    We run the script, snapshot counts, run again, snapshot again, assert equal.
    """

    async def _counts() -> dict[str, int]:
        """Return row counts for all backfill-owned tables."""
        cons_id_row = await db.execute(
            text("SELECT id FROM consignment WHERE code = :code AND deleted_at IS NULL"),
            {"code": CONSIGNMENT_CODE},
        )
        cons_id = cons_id_row.scalar_one()

        ot = int(
            (
                await db.execute(
                    text(
                        "SELECT COUNT(*) FROM off_taker "
                        "WHERE code = :code AND deleted_at IS NULL"
                    ),
                    {"code": OFF_TAKER_CODE},
                )
            ).scalar_one()
        )
        legs = int(
            (
                await db.execute(
                    text(
                        "SELECT COUNT(*) FROM shipment_leg "
                        "WHERE consignment_id = :cid AND deleted_at IS NULL"
                    ),
                    {"cid": cons_id},
                )
            ).scalar_one()
        )
        units = int(
            (
                await db.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM shipment_unit su
                        JOIN shipment_leg sl ON sl.id = su.leg_id
                        WHERE sl.consignment_id = :cid
                        """
                    ),
                    {"cid": cons_id},
                )
            ).scalar_one()
        )
        pos = int(
            (
                await db.execute(
                    text(
                        "SELECT COUNT(*) FROM consignment_pos WHERE consignment_id = :cid"
                    ),
                    {"cid": cons_id},
                )
            ).scalar_one()
        )
        return {"off_taker": ot, "legs": legs, "units": units, "pos": pos}

    # First run
    r1 = _run_script()
    assert r1.returncode == 0, f"First backfill run failed:\n{r1.stderr}"
    counts_after_first = await _counts()

    # Second run
    r2 = _run_script()
    assert r2.returncode == 0, f"Second backfill run failed:\n{r2.stderr}"
    counts_after_second = await _counts()

    assert counts_after_first == counts_after_second, (
        f"Idempotency violated — counts changed between runs:\n"
        f"  after 1st: {counts_after_first}\n"
        f"  after 2nd: {counts_after_second}"
    )
    # Also assert the expected absolute values
    assert counts_after_second["off_taker"] == 1
    assert counts_after_second["legs"] == 4
    assert counts_after_second["units"] == 29
    assert counts_after_second["pos"] == 20


@pytest.mark.asyncio
async def test_backfill_mass_balance_closes(db: AsyncSession) -> None:
    """Mass balance must close:
        sum(shipment_unit.kg_net for bl_ocean legs) == 576,270 ± 1
        sum(consignment_pos.kg_net) + utb_residual == 576,270 ± 1
    """
    cons_id_row = await db.execute(
        text(
            "SELECT id FROM consignment WHERE code = :code AND deleted_at IS NULL"
        ),
        {"code": CONSIGNMENT_CODE},
    )
    cons_id: int = int(cons_id_row.scalar_one())

    # Sum of bl_ocean shipment units
    unit_sum_row = await db.execute(
        text(
            """
            SELECT COALESCE(SUM(su.kg_net), 0)
            FROM shipment_unit su
            JOIN shipment_leg sl ON sl.id = su.leg_id
            WHERE sl.consignment_id = :cid
              AND sl.leg_type = 'bl_ocean'
              AND sl.deleted_at IS NULL
            """
        ),
        {"cid": cons_id},
    )
    unit_sum = Decimal(str(unit_sum_row.scalar_one()))

    assert abs(unit_sum - EXPECTED_TOTAL_KG) <= TOLERANCE, (
        f"sum(shipment_unit.kg_net) = {unit_sum} ≠ {EXPECTED_TOTAL_KG} ± {TOLERANCE}"
    )

    # UTB residual
    utb_row = await db.execute(
        text(
            "SELECT kg_stock_residual FROM shipment_leg "
            "WHERE consignment_id = :cid AND leg_type = 'utb_transload' "
            "AND deleted_at IS NULL"
        ),
        {"cid": cons_id},
    )
    utb_residual = Decimal(str(utb_row.scalar_one()))

    # Sum of PoS kg_net
    pos_sum_row = await db.execute(
        text(
            "SELECT COALESCE(SUM(kg_net), 0) FROM consignment_pos "
            "WHERE consignment_id = :cid"
        ),
        {"cid": cons_id},
    )
    pos_sum = Decimal(str(pos_sum_row.scalar_one()))

    assert abs(pos_sum + utb_residual - EXPECTED_TOTAL_KG) <= TOLERANCE, (
        f"sum(consignment_pos.kg_net) {pos_sum} + utb_residual {utb_residual} = "
        f"{pos_sum + utb_residual} ≠ {EXPECTED_TOTAL_KG} ± {TOLERANCE}"
    )

    # Verify expected UTB residual
    assert abs(utb_residual - EXPECTED_UTB_RESIDUAL) <= TOLERANCE, (
        f"utb_residual = {utb_residual} ≠ {EXPECTED_UTB_RESIDUAL}"
    )


@pytest.mark.asyncio
async def test_backfill_off_taker_singleton(db: AsyncSession) -> None:
    """Exactly 1 non-deleted off_taker row with code='CROWN-OIL-UK'."""
    row = await db.execute(
        text(
            "SELECT COUNT(*) FROM off_taker "
            "WHERE code = :code AND deleted_at IS NULL"
        ),
        {"code": OFF_TAKER_CODE},
    )
    count = int(row.scalar_one())
    assert count == 1, (
        f"Expected exactly 1 off_taker row for {OFF_TAKER_CODE!r}, found {count}"
    )
