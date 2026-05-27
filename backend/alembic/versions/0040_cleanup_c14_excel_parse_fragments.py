"""cleanup_c14_excel_parse_fragments — wipe daily_inputs.c14_analysis
populated by faulty Excel ingest (each lab test exploded into N text
fragments across N rows). Confirmed by client 2026-05-26: only PDFs in
Drive `DFT_2025/C14LABTEST/` are canonical lab evidence; everything
ingested from xlsx into `c14_analysis` is parse noise.

Window: entry_date BETWEEN 2025-01-01 AND 2025-08-31 (audit C1 scope).

Pre-check ground truth (executed 2026-05-26, head 0039):
    Jan-Aug 2025 daily_inputs (deleted_at IS NULL):
      total rows                 : 2047
      c14_analysis NOT NULL      : 98   (target)
      c14_value    NOT NULL      : 0    (no-op)
      manuf_veg_pct NOT NULL     : 164  (NOT TOUCHED — different metric)

    Distinct c14_analysis values include garbage fragments such as
    "SAMPLE SHIPPED TO NL", "SAYBOLT", "Crown Oil", "Bureau Veritas",
    bare numeric values "0.293" / "0.309", lab reference strings
    "NLADM-25-00196-001", "12010/00110117.5/L/25", and "Date of
    Sampling : 23-Jan-2025" lines — all of which originate from a
    single per-test PDF that the xlsx parser flattened row-by-row.

Migration plan:

    A. Backup table `_backup_c14_analysis_pre_0040` snapshots every
       affected row's (id, entry_date, supplier_id, c14_analysis_old)
       for full reversibility. Created in same transaction; survives
       upgrade so downgrade can restore exact prior state.

    B. Audit log: one 'update' entry per affected row, old_values
       carrying the original c14_analysis text, new_values NULL plus
       a reason/migration marker.

    C. UPDATE: NULL c14_analysis for the window where it is not NULL.
       Business-key WHERE (entry_date range + c14_analysis IS NOT
       NULL), no id reference per `feedback_migration_row_id_portability`.

    D. `c14_value` and `manuf_veg_pct` untouched by design.

Downgrade restores c14_analysis from `_backup_c14_analysis_pre_0040`
keyed by (entry_date, supplier_id, c14_analysis-as-was). Backup table
is then dropped. Audit log entries preserved (no DELETE).
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0040_wipe_c14_parse_frags"
down_revision = "0039_retire_legacy_suppliers"
branch_labels = None
depends_on = None


# Audit window (inclusive start, exclusive end-of-Aug → use < 2025-09-01).
WINDOW_START = "2025-01-01"
WINDOW_END_EXCLUSIVE = "2025-09-01"


def upgrade() -> None:
    # -----------------------------------------------------------------
    # A. Backup table — snapshot affected rows before NULL-ing.
    # -----------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS _backup_c14_analysis_pre_0040 (
            backup_id            bigserial PRIMARY KEY,
            daily_input_id       bigint        NOT NULL,
            entry_date           date          NOT NULL,
            supplier_id          bigint        NOT NULL,
            c14_analysis_old     text          NOT NULL,
            backed_up_at         timestamptz   NOT NULL DEFAULT NOW(),
            migration            text          NOT NULL DEFAULT
                '0040_wipe_c14_parse_frags'
        );
        """
    )
    op.execute(
        """
        INSERT INTO _backup_c14_analysis_pre_0040
            (daily_input_id, entry_date, supplier_id, c14_analysis_old)
        SELECT id, entry_date, supplier_id, c14_analysis
        FROM daily_inputs
        WHERE entry_date >= DATE '2025-01-01'
          AND entry_date <  DATE '2025-09-01'
          AND c14_analysis IS NOT NULL
          AND deleted_at IS NULL;
        """
    )

    # -----------------------------------------------------------------
    # B. Audit log + C. NULL c14_analysis (single CTE so we audit-log
    # exactly what we cleared, atomically).
    # -----------------------------------------------------------------
    op.execute(
        """
        WITH cleared AS (
            UPDATE daily_inputs
            SET c14_analysis = NULL,
                updated_at = NOW()
            WHERE entry_date >= DATE '2025-01-01'
              AND entry_date <  DATE '2025-09-01'
              AND c14_analysis IS NOT NULL
              AND deleted_at IS NULL
            RETURNING id, c14_analysis  -- already NULL post-update
        ),
        -- Pair every cleared id with its pre-NULL value from backup so
        -- audit_log.old_values carries the original text.
        cleared_with_old AS (
            SELECT b.daily_input_id AS id, b.c14_analysis_old
            FROM _backup_c14_analysis_pre_0040 b
            WHERE b.daily_input_id IN (SELECT id FROM cleared)
              AND b.migration = '0040_wipe_c14_parse_frags'
        )
        INSERT INTO audit_log (table_name, record_id, action,
                               old_values, new_values)
        SELECT 'daily_inputs', id, 'update',
               jsonb_build_object('c14_analysis', c14_analysis_old),
               jsonb_build_object(
                   'c14_analysis', NULL::text,
                   'kind', 'c14_parse_fragment_cleanup',
                   'reason', 'excel parser exploded 1 lab test into N '
                             'rows; client-confirmed Drive C14LABTEST/ '
                             'PDFs are canonical 2026-05-26',
                   'migration', '0040_wipe_c14_parse_frags'
               )
        FROM cleared_with_old;
        """
    )


def downgrade() -> None:
    # Restore c14_analysis from backup by daily_input_id (stable PK).
    op.execute(
        """
        UPDATE daily_inputs di
        SET c14_analysis = b.c14_analysis_old,
            updated_at = NOW()
        FROM _backup_c14_analysis_pre_0040 b
        WHERE b.daily_input_id = di.id
          AND b.migration = '0040_wipe_c14_parse_frags'
          AND di.c14_analysis IS NULL;
        """
    )

    # Drop the backup table — restore is complete.
    op.execute("DROP TABLE IF EXISTS _backup_c14_analysis_pre_0040;")

    # Audit log entries preserved (no DELETE).
