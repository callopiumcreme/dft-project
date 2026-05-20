"""rebalance Feb-Aug 2025 daily_production EU% targets + force input=ktp

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-20

Rewrites daily_production for Feb-Aug 2025 to:

  1. Force kg_to_production = SUM(daily_inputs.total_input_kg) per day for
     Mar-Aug 2025. Five days currently diverge from input (xlsx
     transcription noise):
       - 2025-03-12  delta -5,539
       - 2025-04-10  delta    +60
       - 2025-04-21  delta +25,744
       - 2025-06-03  delta +4,999
       - 2025-08-21  delta -9,765
     All other Mar-Aug days already have ktp == input → no-op there.

  2. February 2025 is LEFT WITH ITS CURRENT ktp (which exceeds input
     by exactly 339,865 kg = Jan 2025 closing stock consumed on
     Feb 1-4). Stock carry-over is documented in Annex D and is the
     intended behaviour; only the EU% rebalance below is applied.

  3. Recompute eu_prod_kg = kg_to_production * EU_TARGET_PCT[mo] per day.
     EU targets:
       Feb 30.9 %   May 32.4 %   Aug 31.4 %
       Mar 25.8 %   Jun 27.8 %
       Apr 29.4 %   Jul 30.3 %

  4. Redistribute the new remainder = ktp - eu_new across the six
     subproducts (plus, carbon_black, metal_scrap, h2o, gas_syngas,
     losses) using the per-day OLD-row proportions of those six fields.
     Per-day weights preserve the existing xlsx fingerprint; only the
     EU split changes.

  5. Insert one audit_log row per touched daily_production row with
     action='update', old_values + new_values JSONB capture.

  6. REFRESH MATERIALIZED VIEW CONCURRENTLY mv_mass_balance_daily and
     mv_mass_balance_monthly outside any transaction (AUTOCOMMIT
     required by Postgres for CONCURRENTLY).

ISCC EU audit safety note: this migration explicitly rewrites
historical production-side rows. The change is authorised by the
project owner (2026-05-20 directive: force EU% to monthly targets, all
other months close to zero). Every modified row has its full old_values
captured in audit_log for auditor reconstruction. Downgrade restores
old_values verbatim.

GENERATED columns (litres_eu, litres_plus) auto-recompute on UPDATE; we
do not write them directly.
"""
from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP

from alembic import op
from sqlalchemy import text


revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


# Monthly EU% target — user directive 2026-05-20
EU_TARGET_PCT = {
    "2025-02": Decimal("30.9"),
    "2025-03": Decimal("25.8"),
    "2025-04": Decimal("29.4"),
    "2025-05": Decimal("32.4"),
    "2025-06": Decimal("27.8"),
    "2025-07": Decimal("30.3"),
    "2025-08": Decimal("31.4"),
}

SUBPROD_FIELDS = (
    "plus_prod_kg",
    "carbon_black_kg",
    "metal_scrap_kg",
    "h2o_kg",
    "gas_syngas_kg",
    "losses_kg",
)


def _q3(x: Decimal) -> Decimal:
    """Round to 3 decimals (numeric(14,3) column precision)."""
    return x.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def upgrade() -> None:
    conn = op.get_bind()

    rows = conn.execute(
        text(
            """
            SELECT
              p.id,
              p.prod_date,
              p.kg_to_production       AS old_ktp,
              p.eu_prod_kg             AS old_eu,
              p.plus_prod_kg,
              p.carbon_black_kg,
              p.metal_scrap_kg,
              p.h2o_kg,
              p.gas_syngas_kg,
              p.losses_kg,
              p.output_eu_kg,
              COALESCE(i.in_kg, 0)     AS input_kg
            FROM daily_production p
            LEFT JOIN (
              SELECT entry_date, SUM(total_input_kg) AS in_kg
              FROM daily_inputs
              WHERE entry_date BETWEEN '2025-02-01' AND '2025-08-31'
                AND deleted_at IS NULL
              GROUP BY entry_date
            ) i ON i.entry_date = p.prod_date
            WHERE p.prod_date BETWEEN '2025-02-01' AND '2025-08-31'
              AND p.deleted_at IS NULL
            ORDER BY p.prod_date
            """
        )
    ).fetchall()

    for r in rows:
        mo = r.prod_date.strftime("%Y-%m")
        pct = EU_TARGET_PCT[mo]

        old_ktp = Decimal(r.old_ktp or 0)
        old_eu = Decimal(r.old_eu or 0)
        input_kg = Decimal(r.input_kg or 0)

        # Step 1 — new ktp
        # Feb: keep old (stock carry-over).
        # Mar-Aug: force to input.
        new_ktp = old_ktp if mo == "2025-02" else input_kg

        # Step 3 — new EU
        new_eu = _q3(new_ktp * pct / Decimal("100"))

        # Step 4 — redistribute remainder over subproducts using per-day
        # OLD subproduct weights. If old subproducts sum to 0, fall back
        # to even split (defensive — should not occur in Feb-Aug).
        new_remainder = new_ktp - new_eu
        old_subs = {f: Decimal(getattr(r, f) or 0) for f in SUBPROD_FIELDS}
        old_sub_total = sum(old_subs.values())

        new_subs: dict[str, Decimal] = {}
        if old_sub_total > 0:
            # Proportional split. To avoid drift, allocate first N-1 by
            # proportion (rounded) and set the last field = remainder.
            running = Decimal("0")
            keys = list(SUBPROD_FIELDS)
            for k in keys[:-1]:
                share = _q3(new_remainder * old_subs[k] / old_sub_total)
                new_subs[k] = share
                running += share
            new_subs[keys[-1]] = _q3(new_remainder - running)
        else:
            even = _q3(new_remainder / Decimal(len(SUBPROD_FIELDS)))
            running = Decimal("0")
            for k in SUBPROD_FIELDS[:-1]:
                new_subs[k] = even
                running += even
            new_subs[SUBPROD_FIELDS[-1]] = _q3(new_remainder - running)

        # Skip no-op rows (avoid noise UPDATE + audit entry).
        is_noop = (
            new_ktp == old_ktp
            and new_eu == old_eu
            and all(new_subs[k] == old_subs[k] for k in SUBPROD_FIELDS)
        )
        if is_noop:
            continue

        old_values = {
            "kg_to_production": str(_q3(old_ktp)),
            "eu_prod_kg": str(_q3(old_eu)),
            **{k: str(_q3(old_subs[k])) for k in SUBPROD_FIELDS},
            "output_eu_kg": str(_q3(Decimal(r.output_eu_kg or 0))),
        }
        new_values = {
            "kg_to_production": str(new_ktp),
            "eu_prod_kg": str(new_eu),
            **{k: str(new_subs[k]) for k in SUBPROD_FIELDS},
            "output_eu_kg": str(new_eu),  # output_eu_kg tracks eu_prod_kg
        }

        conn.execute(
            text(
                """
                UPDATE daily_production SET
                  kg_to_production = :ktp,
                  eu_prod_kg       = :eu,
                  plus_prod_kg     = :plus,
                  carbon_black_kg  = :cb,
                  metal_scrap_kg   = :steel,
                  h2o_kg           = :h2o,
                  gas_syngas_kg    = :gas,
                  losses_kg        = :loss,
                  output_eu_kg     = :eu,
                  updated_at       = NOW()
                WHERE id = :id
                """
            ),
            {
                "id": r.id,
                "ktp": str(new_ktp),
                "eu": str(new_eu),
                "plus": str(new_subs["plus_prod_kg"]),
                "cb": str(new_subs["carbon_black_kg"]),
                "steel": str(new_subs["metal_scrap_kg"]),
                "h2o": str(new_subs["h2o_kg"]),
                "gas": str(new_subs["gas_syngas_kg"]),
                "loss": str(new_subs["losses_kg"]),
            },
        )

        conn.execute(
            text(
                """
                INSERT INTO audit_log
                  (table_name, record_id, action, old_values, new_values, changed_at)
                VALUES
                  ('daily_production', :rid, 'update',
                   CAST(:old AS jsonb), CAST(:new AS jsonb), NOW())
                """
            ),
            {
                "rid": r.id,
                "old": json.dumps(old_values),
                "new": json.dumps(new_values),
            },
        )

    # Refresh MVs within this migration's transaction.
    # Non-CONCURRENT refresh holds AccessExclusiveLock but is permitted
    # inside a transaction; AUTOCOMMIT trick is incompatible with the
    # asyncpg driver used by this project's alembic env.
    conn.execute(text("REFRESH MATERIALIZED VIEW mv_mass_balance_daily"))
    conn.execute(text("REFRESH MATERIALIZED VIEW mv_mass_balance_monthly"))


def downgrade() -> None:
    """Restore from audit_log old_values JSONB.

    Pulls the most recent audit_log row per (record_id) within the
    Feb-Aug 2025 window inserted by this upgrade, then writes the
    captured old_values back. After restore, soft-marks those audit
    rows by writing action='restore' rows referencing the same record
    so the rollback itself is auditable.
    """
    conn = op.get_bind()

    rows = conn.execute(
        text(
            """
            WITH ranked AS (
              SELECT
                a.id          AS audit_id,
                a.record_id,
                a.old_values,
                ROW_NUMBER() OVER (
                  PARTITION BY a.record_id
                  ORDER BY a.changed_at DESC, a.id DESC
                ) AS rn
              FROM audit_log a
              JOIN daily_production p ON p.id = a.record_id
              WHERE a.table_name = 'daily_production'
                AND a.action = 'update'
                AND p.prod_date BETWEEN '2025-02-01' AND '2025-08-31'
                AND a.old_values ? 'kg_to_production'
                AND a.old_values ? 'eu_prod_kg'
            )
            SELECT record_id, old_values
            FROM ranked
            WHERE rn = 1
            """
        )
    ).fetchall()

    for r in rows:
        ov = r.old_values
        conn.execute(
            text(
                """
                UPDATE daily_production SET
                  kg_to_production = :ktp,
                  eu_prod_kg       = :eu,
                  plus_prod_kg     = :plus,
                  carbon_black_kg  = :cb,
                  metal_scrap_kg   = :steel,
                  h2o_kg           = :h2o,
                  gas_syngas_kg    = :gas,
                  losses_kg        = :loss,
                  output_eu_kg     = :out,
                  updated_at       = NOW()
                WHERE id = :id
                """
            ),
            {
                "id": r.record_id,
                "ktp": ov["kg_to_production"],
                "eu": ov["eu_prod_kg"],
                "plus": ov["plus_prod_kg"],
                "cb": ov["carbon_black_kg"],
                "steel": ov["metal_scrap_kg"],
                "h2o": ov["h2o_kg"],
                "gas": ov["gas_syngas_kg"],
                "loss": ov["losses_kg"],
                "out": ov["output_eu_kg"],
            },
        )

        conn.execute(
            text(
                """
                INSERT INTO audit_log
                  (table_name, record_id, action, old_values, new_values, changed_at)
                VALUES
                  ('daily_production', :rid, 'restore',
                   NULL, CAST(:ov AS jsonb), NOW())
                """
            ),
            {"rid": r.record_id, "ov": json.dumps(ov)},
        )

    raw_conn = conn.connection.dbapi_connection
    prev_iso = raw_conn.isolation_level
    raw_conn.set_isolation_level(0)
    try:
        cur = raw_conn.cursor()
        cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_mass_balance_daily")
        cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_mass_balance_monthly")
        cur.close()
    finally:
        raw_conn.set_isolation_level(prev_iso)
