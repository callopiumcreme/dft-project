"""Backfill script: Q3-2025 Crown Oil consignment (Cartagena → UTB BV → Crown Oil UK).

Idempotent: running twice produces the same DB state (no duplicates, no error).
Uses ON CONFLICT upsert / existence checks so partial backfills are safe.

Source data (NOT committed to repo — stays in /tmp/bl_dl/):
  /tmp/bl_dl/arrivals_containers.csv  -- 29 container rows (BL1 x 15, BL2 x 14)
  /tmp/bl_dl/deliveries_uk.csv        — 20 ISO-tank delivery rows

Tables written (from migration 0021_logistics_downstream):
  off_taker, consignment, shipment_leg, shipment_unit, consignment_pos

NOT written — follow-up required:
  consignment_production_link — requires per-day production allocation mapping
  from the raw daily_production table across Jun-Aug 2025, which spans 2-3
  months of production and was not reconciled in this backfill window.
  Open task: cross-join daily_production with consignment DEL-CRW-2025-2
  by date range and split kg proportionally once per-batch product ledger is
  confirmed.

Usage:
    cd backend
    DATABASE_URL=postgresql+asyncpg://dft:dft@172.22.0.2:5432/dft \\
        python scripts/backfill_consignment_2025q3.py

    # or, if running inside the dft-project_internal network where
    # hostname 'db' resolves:
    python scripts/backfill_consignment_2025q3.py
"""
from __future__ import annotations

import asyncio
import csv
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dft:dft@172.22.0.2:5432/dft",
)

CSV_DIR = Path("/tmp/bl_dl")  # noqa: S108
CONTAINERS_CSV = CSV_DIR / "arrivals_containers.csv"
DELIVERIES_CSV = CSV_DIR / "deliveries_uk.csv"

# PoS file naming: 0016 has an underscore typo in the actual Drive filename.
_POS_FILENAME_OVERRIDES: dict[str, str] = {
    "OISCRO-0016-25": "OutgoingMaterial_Declaration_OISCRO-0016_-25.pdf",
}
_GDRIVE_POS_BASE = "gdrive:DFT_2025/POS TO CROWN"


def _pos_pdf_ref(pos_number: str) -> str:
    """Return the gdrive path for a given PoS number, honouring filename quirks."""
    if pos_number in _POS_FILENAME_OVERRIDES:
        return f"{_GDRIVE_POS_BASE}/{_POS_FILENAME_OVERRIDES[pos_number]}"
    return f"{_GDRIVE_POS_BASE}/OutgoingMaterial_Declaration_{pos_number}.pdf"


# ---------------------------------------------------------------------------
# Off-taker constants
# ---------------------------------------------------------------------------

OFF_TAKER_CODE = "CROWN-OIL-UK"
OFF_TAKER_NAME = "Crown Oil Limited"
OFF_TAKER_COUNTRY = "GB"
OFF_TAKER_ADDRESS = "Bury, Greater Manchester, UK"
OFF_TAKER_NOTES = (
    "Sole DFT off-taker (single buyer of project). "
    "RTFO submission handled by Crown Oil directly."
)

# ---------------------------------------------------------------------------
# Consignment constants
# ---------------------------------------------------------------------------

CONSIGNMENT_CODE = "DEL-CRW-2025-2"
CONSIGNMENT_PRODUCT_GRADE = "DEV-P100"
CONSIGNMENT_PROD_DATE_FROM = date(2025, 6, 1)
CONSIGNMENT_PROD_DATE_TO = date(2025, 8, 31)
CONSIGNMENT_TOTAL_KG = Decimal("576270.000")
CONSIGNMENT_STATUS = "at_utb"
CONSIGNMENT_NOTES = (
    "Backfill from BL CMDU856254189 + CMDU877254433 (Cartagena → Rotterdam) "
    "+ UTB BV transload + 20 ISO tanks to Crown Oil Bury UK. "
    "Reconciled 2026-05-23. See /tmp/bl_dl/RECONCILIATION.md."
)

# ---------------------------------------------------------------------------
# Shipment-leg constants
# ---------------------------------------------------------------------------

LEG_DEFS = [
    {
        "seq": 1,
        "leg_type": "bl_ocean",
        "document_type": "BL_ocean",
        "document_ref": "CMDU856254189",
        "document_date": date(2025, 6, 11),
        "carrier": "CARTAGENA EXPRES voy 007CONU",
        "origin_node": "Cartagena (CO)",
        "destination_node": "Rotterdam (NL)",
        "kg_in": Decimal("298129.000"),
        "kg_out": Decimal("298129.000"),
        "kg_stock_residual": None,
        "notes": None,
    },
    {
        "seq": 2,
        "leg_type": "bl_ocean",
        "document_type": "BL_ocean",
        "document_ref": "CMDU877254433",
        "document_date": date(2025, 7, 3),
        "carrier": "ISTANBUL EXPRES voy 005COEN",
        "origin_node": "Cartagena (CO)",
        "destination_node": "Rotterdam (NL)",
        "kg_in": Decimal("278141.000"),
        "kg_out": Decimal("278141.000"),
        "kg_stock_residual": None,
        "notes": None,
    },
    {
        "seq": 3,
        "leg_type": "utb_transload",
        "document_type": "transload_report",
        "document_ref": "UTB-2025-Q3-CONSOLIDATED",
        "document_date": date(2025, 7, 20),
        "carrier": "UTB BV Dordrecht",
        "origin_node": "Dordrecht (NL)",
        "destination_node": "Dordrecht (NL)",
        "kg_in": Decimal("576270.000"),
        "kg_out": Decimal("500410.000"),
        "kg_stock_residual": Decimal("75860.000"),
        # operator_certificate_id resolved dynamically (NULL if no UTB cert row found)
        "notes": (
            "UTB BV ISCC cert filed under deliverables/RTFO-310825/03_supplier_evidence/"
            "certificates/CERTIFICATE UTB BV.pdf -- no DB certificate row at backfill time; "
            "set operator_certificate_id once cert is imported."
        ),
    },
    {
        "seq": 4,
        "leg_type": "delivery_uk",
        "document_type": "commercial_invoice",
        "document_ref": "JLY001-JLY020",
        "document_date": date(2025, 8, 15),
        "carrier": "Crown Oil road delivery",
        "origin_node": "Dordrecht (NL)",
        "destination_node": "Bury (UK)",
        "kg_in": Decimal("500410.000"),
        "kg_out": Decimal("500410.000"),
        "kg_stock_residual": None,
        "notes": None,
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_containers() -> list[dict[str, str]]:
    with CONTAINERS_CSV.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = [row for row in reader if row.get("container", "").strip()]
    if len(rows) != 29:
        raise RuntimeError(
            f"Expected 29 container rows in {CONTAINERS_CSV}, got {len(rows)}"
        )
    return rows


def _read_deliveries() -> list[dict[str, str]]:
    with DELIVERIES_CSV.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = [row for row in reader if row.get("pos_crown_no", "").strip()]
    if len(rows) != 20:
        raise RuntimeError(
            f"Expected 20 delivery rows in {DELIVERIES_CSV}, got {len(rows)}"
        )
    return rows


# ---------------------------------------------------------------------------
# Main backfill
# ---------------------------------------------------------------------------


async def run_backfill(session: AsyncSession) -> None:
    # ------------------------------------------------------------------ #
    # 1. off_taker — upsert by code (unique constraint)                   #
    # ------------------------------------------------------------------ #
    await session.execute(
        text(
            """
            INSERT INTO off_taker
                (code, name, country, address, notes, created_at, updated_at)
            VALUES
                (:code, :name, :country, :address, :notes, NOW(), NOW())
            ON CONFLICT (code) DO UPDATE
                SET name       = EXCLUDED.name,
                    country    = EXCLUDED.country,
                    address    = EXCLUDED.address,
                    notes      = EXCLUDED.notes,
                    updated_at = NOW()
            """
        ),
        {
            "code": OFF_TAKER_CODE,
            "name": OFF_TAKER_NAME,
            "country": OFF_TAKER_COUNTRY,
            "address": OFF_TAKER_ADDRESS,
            "notes": OFF_TAKER_NOTES,
        },
    )

    row = await session.execute(
        text("SELECT id FROM off_taker WHERE code = :code"),
        {"code": OFF_TAKER_CODE},
    )
    off_taker_id: int = int(row.scalar_one())

    # ------------------------------------------------------------------ #
    # 2. consignment — upsert by code (unique constraint)                  #
    # ------------------------------------------------------------------ #
    await session.execute(
        text(
            """
            INSERT INTO consignment
                (code, off_taker_id, product_grade,
                 prod_date_from, prod_date_to, total_kg, status, notes,
                 created_at, updated_at)
            VALUES
                (:code, :off_taker_id, :product_grade,
                 :prod_date_from, :prod_date_to, :total_kg, :status, :notes,
                 NOW(), NOW())
            ON CONFLICT (code) DO UPDATE
                SET off_taker_id    = EXCLUDED.off_taker_id,
                    product_grade   = EXCLUDED.product_grade,
                    prod_date_from  = EXCLUDED.prod_date_from,
                    prod_date_to    = EXCLUDED.prod_date_to,
                    total_kg        = EXCLUDED.total_kg,
                    status          = EXCLUDED.status,
                    notes           = EXCLUDED.notes,
                    updated_at      = NOW()
            """
        ),
        {
            "code": CONSIGNMENT_CODE,
            "off_taker_id": off_taker_id,
            "product_grade": CONSIGNMENT_PRODUCT_GRADE,
            "prod_date_from": CONSIGNMENT_PROD_DATE_FROM,
            "prod_date_to": CONSIGNMENT_PROD_DATE_TO,
            "total_kg": CONSIGNMENT_TOTAL_KG,
            "status": CONSIGNMENT_STATUS,
            "notes": CONSIGNMENT_NOTES,
        },
    )

    row = await session.execute(
        text("SELECT id FROM consignment WHERE code = :code"),
        {"code": CONSIGNMENT_CODE},
    )
    consignment_id: int = int(row.scalar_one())

    # ------------------------------------------------------------------ #
    # 3. shipment_leg — upsert by (consignment_id, seq)                   #
    #    seq is not a unique constraint by itself; use existence check +  #
    #    upsert via DELETE + re-insert would be destructive to shipment_  #
    #    unit children.  Instead: INSERT … ON CONFLICT DO UPDATE using a  #
    #    unique index on (consignment_id, seq) — if that index exists;    #
    #    otherwise: SELECT + conditional INSERT.                           #
    # ------------------------------------------------------------------ #

    # Check whether a unique index on (consignment_id, seq) exists
    idx_check = await session.execute(
        text(
            """
            SELECT COUNT(*) FROM pg_indexes
            WHERE tablename = 'shipment_leg'
              AND indexdef ILIKE '%consignment_id%seq%'
            """
        )
    )
    has_unique_idx = int(idx_check.scalar_one()) > 0

    leg_ids: dict[int, int] = {}  # seq → leg.id

    # Resolve UTB operator_certificate_id (NULL if no UTB cert row in DB)
    utb_cert_row = await session.execute(
        text(
            """
            SELECT id FROM certificates
            WHERE cert_number ILIKE '%UTB%'
               OR notes ILIKE '%UTB BV%'
            LIMIT 1
            """
        )
    )
    utb_cert_id: int | None = utb_cert_row.scalar_one_or_none()

    for leg_def in LEG_DEFS:
        seq = int(leg_def["seq"])  # type: ignore[call-overload]

        # Build params dict
        leg_params: dict[str, object] = {
            "consignment_id": consignment_id,
            "seq": seq,
            "leg_type": leg_def["leg_type"],
            "document_type": leg_def["document_type"],
            "document_ref": leg_def["document_ref"],
            "document_date": leg_def["document_date"],
            "carrier": leg_def["carrier"],
            "origin_node": leg_def["origin_node"],
            "destination_node": leg_def["destination_node"],
            "kg_in": leg_def["kg_in"],
            "kg_out": leg_def["kg_out"],
            "kg_stock_residual": leg_def["kg_stock_residual"],
            "operator_certificate_id": utb_cert_id if seq == 3 else None,
            "notes": leg_def["notes"],
        }

        if has_unique_idx:
            await session.execute(
                text(
                    """
                    INSERT INTO shipment_leg
                        (consignment_id, seq, leg_type, document_type, document_ref,
                         document_date, carrier, origin_node, destination_node,
                         kg_in, kg_out, kg_stock_residual,
                         operator_certificate_id, notes, created_at, updated_at)
                    VALUES
                        (:consignment_id, :seq, :leg_type, :document_type, :document_ref,
                         :document_date, :carrier, :origin_node, :destination_node,
                         :kg_in, :kg_out, :kg_stock_residual,
                         :operator_certificate_id, :notes, NOW(), NOW())
                    ON CONFLICT (consignment_id, seq) DO UPDATE
                        SET leg_type                = EXCLUDED.leg_type,
                            document_type           = EXCLUDED.document_type,
                            document_ref            = EXCLUDED.document_ref,
                            document_date           = EXCLUDED.document_date,
                            carrier                 = EXCLUDED.carrier,
                            origin_node             = EXCLUDED.origin_node,
                            destination_node        = EXCLUDED.destination_node,
                            kg_in                   = EXCLUDED.kg_in,
                            kg_out                  = EXCLUDED.kg_out,
                            kg_stock_residual       = EXCLUDED.kg_stock_residual,
                            operator_certificate_id = EXCLUDED.operator_certificate_id,
                            notes                   = EXCLUDED.notes,
                            updated_at              = NOW()
                    """
                ),
                leg_params,
            )
        else:
            # Fallback: existence check → skip if already present
            existing = await session.execute(
                text(
                    "SELECT id FROM shipment_leg "
                    "WHERE consignment_id = :consignment_id AND seq = :seq"
                ),
                {"consignment_id": consignment_id, "seq": seq},
            )
            existing_id = existing.scalar_one_or_none()
            if existing_id is None:
                await session.execute(
                    text(
                        """
                        INSERT INTO shipment_leg
                            (consignment_id, seq, leg_type, document_type, document_ref,
                             document_date, carrier, origin_node, destination_node,
                             kg_in, kg_out, kg_stock_residual,
                             operator_certificate_id, notes, created_at, updated_at)
                        VALUES
                            (:consignment_id, :seq, :leg_type, :document_type, :document_ref,
                             :document_date, :carrier, :origin_node, :destination_node,
                             :kg_in, :kg_out, :kg_stock_residual,
                             :operator_certificate_id, :notes, NOW(), NOW())
                        """
                    ),
                    leg_params,
                )

        # Retrieve the leg id
        leg_row = await session.execute(
            text(
                "SELECT id FROM shipment_leg "
                "WHERE consignment_id = :consignment_id AND seq = :seq"
            ),
            {"consignment_id": consignment_id, "seq": seq},
        )
        leg_ids[seq] = int(leg_row.scalar_one())

    # ------------------------------------------------------------------ #
    # 4. shipment_unit — idempotent via (leg_id, container_ref)           #
    #    shipment_unit has no unique index; use existence check.          #
    # ------------------------------------------------------------------ #
    containers = _read_containers()

    bl1_ref = "CMDU856254189"
    bl2_ref = "CMDU877254433"

    # Map document_ref → leg_id
    bl_leg_map: dict[str, int] = {}
    for seq, leg_def in zip((1, 2), LEG_DEFS[:2], strict=True):
        bl_leg_map[str(leg_def["document_ref"])] = leg_ids[seq]

    for row_data in containers:
        bl_ref = row_data["bl"].strip()
        if bl_ref == bl1_ref:
            leg_id = bl_leg_map[bl1_ref]
        elif bl_ref == bl2_ref:
            leg_id = bl_leg_map[bl2_ref]
        else:
            raise RuntimeError(f"Unknown BL ref in containers CSV: {bl_ref!r}")

        container_ref = row_data["container"].strip()
        flexitank_ref = row_data["flexitank"].strip() or None
        kg_gross = Decimal(row_data["gross_kg"].strip())
        kg_tare = Decimal(row_data["tare_kg"].strip())
        kg_net = Decimal(row_data["net_kg"].strip())
        notes = row_data["note"].strip() or None

        existing = await session.execute(
            text(
                "SELECT id FROM shipment_unit "
                "WHERE leg_id = :leg_id AND container_ref = :container_ref"
            ),
            {"leg_id": leg_id, "container_ref": container_ref},
        )
        if existing.scalar_one_or_none() is None:
            await session.execute(
                text(
                    """
                    INSERT INTO shipment_unit
                        (leg_id, container_ref, flexitank_ref,
                         kg_gross, kg_tare, kg_net, notes, created_at)
                    VALUES
                        (:leg_id, :container_ref, :flexitank_ref,
                         :kg_gross, :kg_tare, :kg_net, :notes, NOW())
                    """
                ),
                {
                    "leg_id": leg_id,
                    "container_ref": container_ref,
                    "flexitank_ref": flexitank_ref,
                    "kg_gross": kg_gross,
                    "kg_tare": kg_tare,
                    "kg_net": kg_net,
                    "notes": notes,
                },
            )

    # ------------------------------------------------------------------ #
    # 5. consignment_pos — composite PK (consignment_id, pos_number)     #
    #    → ON CONFLICT DO UPDATE is safe.                                 #
    #                                                                     #
    # Per cliente direction 2026-05-23: each PoS is its own outbound      #
    # eRSV with its own GHG triple. Until per-PoS lab measurements are    #
    # supplied we seed ISCC reference values (PoS page 2 standard set).   #
    # ``ersv_outbound_no`` is left NULL here — the renderer allocates     #
    # ``CO/{yy}/{seq:03d}`` lazily and idempotently on first render.      #
    # The ON CONFLICT clause preserves an existing ``ersv_outbound_no``    #
    # (audit safety) and only overwrites GHG values if they are NULL.     #
    # ------------------------------------------------------------------ #
    deliveries = _read_deliveries()

    # ISCC PoS reference values (gCO2eq/MJ; saving in %).
    GHG_EP_DEFAULT = Decimal("12.33")
    GHG_ETD_DEFAULT = Decimal("4.63")
    GHG_TOTAL_DEFAULT = Decimal("16.95")
    GHG_SAVING_PCT_DEFAULT = Decimal("81.96")

    for row_data in deliveries:
        pos_number = row_data["pos_crown_no"].strip()
        kg_net = Decimal(row_data["kgs"].strip())
        pdf_ref = _pos_pdf_ref(pos_number)

        await session.execute(
            text(
                """
                INSERT INTO consignment_pos
                    (consignment_id, pos_number, pdf_ref, kg_net,
                     ghg_ep, ghg_etd, ghg_total, ghg_saving_pct,
                     created_at)
                VALUES
                    (:consignment_id, :pos_number, :pdf_ref, :kg_net,
                     :ghg_ep, :ghg_etd, :ghg_total, :ghg_saving_pct,
                     NOW())
                ON CONFLICT (consignment_id, pos_number) DO UPDATE
                    SET pdf_ref        = EXCLUDED.pdf_ref,
                        kg_net         = EXCLUDED.kg_net,
                        ghg_ep         = COALESCE(consignment_pos.ghg_ep,
                                                  EXCLUDED.ghg_ep),
                        ghg_etd        = COALESCE(consignment_pos.ghg_etd,
                                                  EXCLUDED.ghg_etd),
                        ghg_total      = COALESCE(consignment_pos.ghg_total,
                                                  EXCLUDED.ghg_total),
                        ghg_saving_pct = COALESCE(consignment_pos.ghg_saving_pct,
                                                  EXCLUDED.ghg_saving_pct)
                """
            ),
            {
                "consignment_id": consignment_id,
                "pos_number": pos_number,
                "pdf_ref": pdf_ref,
                "kg_net": kg_net,
                "ghg_ep": GHG_EP_DEFAULT,
                "ghg_etd": GHG_ETD_DEFAULT,
                "ghg_total": GHG_TOTAL_DEFAULT,
                "ghg_saving_pct": GHG_SAVING_PCT_DEFAULT,
            },
        )


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


async def verify(session: AsyncSession) -> bool:
    ok = True

    # off_taker count
    ot_row = await session.execute(
        text(
            "SELECT COUNT(*) FROM off_taker "
            "WHERE code = :code AND deleted_at IS NULL"
        ),
        {"code": OFF_TAKER_CODE},
    )
    ot_count = int(ot_row.scalar_one())

    # consignment
    cons_row = await session.execute(
        text(
            "SELECT id, status, total_kg FROM consignment "
            "WHERE code = :code AND deleted_at IS NULL"
        ),
        {"code": CONSIGNMENT_CODE},
    )
    cons = cons_row.mappings().one()
    cons_id = int(cons["id"])
    cons_status = str(cons["status"])
    cons_total_kg = Decimal(str(cons["total_kg"]))

    # shipment_leg rows
    legs_row = await session.execute(
        text(
            "SELECT seq, kg_in, kg_out, kg_stock_residual, document_ref "
            "FROM shipment_leg "
            "WHERE consignment_id = :cid AND deleted_at IS NULL "
            "ORDER BY seq"
        ),
        {"cid": cons_id},
    )
    legs = legs_row.mappings().all()
    leg_count = len(legs)

    # Identify each leg by seq
    leg_by_seq = {int(r["seq"]): r for r in legs}

    # shipment_unit counts and sum
    units_row = await session.execute(
        text(
            """
            SELECT COUNT(*) AS cnt, COALESCE(SUM(su.kg_net), 0) AS total
            FROM shipment_unit su
            JOIN shipment_leg sl ON sl.id = su.leg_id
            WHERE sl.consignment_id = :cid
              AND sl.leg_type = 'bl_ocean'
              AND sl.deleted_at IS NULL
            """
        ),
        {"cid": cons_id},
    )
    units_agg = units_row.mappings().one()
    unit_count = int(units_agg["cnt"])
    unit_sum = Decimal(str(units_agg["total"]))

    # BL1 / BL2 split
    bl1_units_row = await session.execute(
        text(
            """
            SELECT COUNT(*) FROM shipment_unit su
            JOIN shipment_leg sl ON sl.id = su.leg_id
            WHERE sl.consignment_id = :cid
              AND sl.seq = 1
              AND sl.deleted_at IS NULL
            """
        ),
        {"cid": cons_id},
    )
    bl1_count = int(bl1_units_row.scalar_one())

    bl2_units_row = await session.execute(
        text(
            """
            SELECT COUNT(*) FROM shipment_unit su
            JOIN shipment_leg sl ON sl.id = su.leg_id
            WHERE sl.consignment_id = :cid
              AND sl.seq = 2
              AND sl.deleted_at IS NULL
            """
        ),
        {"cid": cons_id},
    )
    bl2_count = int(bl2_units_row.scalar_one())

    # consignment_pos count and sum (active rows only — 0022 adds deleted_at)
    pos_row = await session.execute(
        text(
            "SELECT COUNT(*) AS cnt, COALESCE(SUM(kg_net), 0) AS total "
            "FROM consignment_pos "
            "WHERE consignment_id = :cid AND deleted_at IS NULL"
        ),
        {"cid": cons_id},
    )
    pos_agg = pos_row.mappings().one()
    pos_count = int(pos_agg["cnt"])
    pos_sum = Decimal(str(pos_agg["total"]))

    # Assertions
    EXPECTED_UNIT_SUM = Decimal("576270.000")
    EXPECTED_POS_SUM = Decimal("500410.000")

    utb_leg = leg_by_seq.get(3)
    utb_residual = Decimal(str(utb_leg["kg_stock_residual"])) if utb_leg else Decimal("0")

    mass_ok = abs(unit_sum - EXPECTED_UNIT_SUM) <= Decimal("1")
    pos_mass_ok = abs(pos_sum + utb_residual - EXPECTED_UNIT_SUM) <= Decimal("1")

    ok = all([
        ot_count == 1,
        cons_status == "at_utb",
        abs(cons_total_kg - EXPECTED_UNIT_SUM) <= Decimal("1"),
        leg_count == 4,
        unit_count == 29,
        bl1_count == 15,
        bl2_count == 14,
        mass_ok,
        pos_count == 20,
        pos_mass_ok,
    ])

    # Print verification block (always, even if assertions fail)
    print()
    print("== Backfill verification ==")
    print(f"off_taker:                 {ot_count} ({OFF_TAKER_CODE})")
    print(
        f"consignment:               1 ({CONSIGNMENT_CODE}), "
        f"status={cons_status}, total_kg={cons_total_kg}"
    )
    print(f"shipment_leg:              {leg_count} (seq 1..4)")
    if 1 in leg_by_seq:
        print(
            f"  BL1 {leg_by_seq[1]['document_ref']}:       "
            f"net {int(Decimal(str(leg_by_seq[1]['kg_out']))):,} kg"
        )
    if 2 in leg_by_seq:
        print(
            f"  BL2 {leg_by_seq[2]['document_ref']}:       "
            f"net {int(Decimal(str(leg_by_seq[2]['kg_out']))):,} kg"
        )
    if 3 in leg_by_seq:
        utb_in = int(Decimal(str(leg_by_seq[3]["kg_in"])))
        utb_out = int(Decimal(str(leg_by_seq[3]["kg_out"])))
        utb_res = int(utb_residual)
        conservation = "✓ mass conservation" if utb_in == utb_out + utb_res else "✗ MISMATCH"
        print(
            f"  UTB transload:           "
            f"in {utb_in:,} out {utb_out:,} residual {utb_res:,} {conservation}"
        )
    if 4 in leg_by_seq:
        print(
            f"  Delivery UK:             "
            f"net {int(Decimal(str(leg_by_seq[4]['kg_out']))):,} kg"
        )
    print(
        f"shipment_unit:             {unit_count} ({bl1_count} BL1 + {bl2_count} BL2)"
        + ("  ✓ matches CSV" if unit_count == 29 else "  ✗ MISMATCH")
    )
    sum_ok_str = "✓ matches consignment.total_kg" if mass_ok else "✗ MISMATCH"
    print(f"  Sum net: {int(unit_sum):,} kg      {sum_ok_str}")
    pos_range = "OISCRO-0013-25 .. OISCRO-0032-25" if pos_count == 20 else f"({pos_count} rows)"
    print(f"consignment_pos:           {pos_count} ({pos_range})")
    pos_delivery_ok = abs(pos_sum - EXPECTED_POS_SUM) <= Decimal("1")
    pos_mass_str = "✓ matches delivery total" if pos_delivery_ok else "✗ MISMATCH"
    print(f"  Sum kg_net:              {int(pos_sum):,} kg {pos_mass_str}")
    closure_lhs = int(unit_sum)
    closure_rhs_out = int(pos_sum)
    closure_rhs_res = int(utb_residual)
    closure_ok = "✓" if pos_mass_ok else "✗ DOES NOT CLOSE"
    print(
        f"mass-balance closes:        {closure_lhs:,} kg in (29 BL units) == "
        f"{closure_rhs_out:,} kg out (20 PoS) + {closure_rhs_res:,} kg UTB residual  {closure_ok}"
    )

    return ok


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    if not CONTAINERS_CSV.exists():
        print(f"ERROR: source CSV not found: {CONTAINERS_CSV}", file=sys.stderr)
        sys.exit(1)
    if not DELIVERIES_CSV.exists():
        print(f"ERROR: source CSV not found: {DELIVERIES_CSV}", file=sys.stderr)
        sys.exit(1)

    engine = create_async_engine(DATABASE_URL, poolclass=NullPool, echo=False)
    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )

    async with factory() as session, session.begin():
        await run_backfill(session)

    # Verification runs in a separate read-only session (after commit)
    async with factory() as session:
        ok = await verify(session)

    await engine.dispose()

    if not ok:
        print(
            "\nERROR: one or more verification assertions FAILED -- see output above.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("\nBackfill completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
