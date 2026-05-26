"""daily_inputs.weighbridge_ticket_no — add paper-record ticket number column

Context: red-team round 1 (DEL-CRW-2025-2 audit, 2026-05-26) flagged
cross-cutting issue X5 — the DFT app has no column for the upstream
paper weighbridge ticket number.  Today the only audit trail to the
paper logs runs through the ingest .xlsx and the daily PDF reports
stored in `data/daily_logs_pdf/`.  An auditor cannot cross-reference
a single weighbridge ticket from the app, only the whole day's PDF.

Per the cliente data-request letter §1 the cliente retains paper
weighbridge logs as the source of truth.  Adding the column is the
honest disclosure of that reality:

    * Column is **nullable** — historical rows pre-2026-05 have no
      paper-ticket transcription.  Backfill is not part of this
      migration; it happens out-of-band as the cliente delivers
      paper-ticket samples (audit Tier C).
    * No FK, no unique constraint — multiple `daily_inputs` rows may
      legitimately share the same paper ticket (split per supplier /
      per product), and the same ticket number may repeat across years
      on different supplier scales.
    * Index is partial — only on rows where the column is populated
      AND `deleted_at IS NULL`, to keep the index small while we are
      pre-Tier-C (most rows still NULL).
    * Comment is the audit-facing source of truth — names the
      paper-records statement and lettera §1 so an auditor inspecting
      `\\d+ daily_inputs` finds the trail without reading the docs/
      folder.

This migration is purely additive: no constraint changes, no backfill,
no row touch.  Safe to run on prod with the table under write traffic.

Downgrade drops the column and its index — no data preservation
because the column is nullable and unowned by the schema (cliente
paper logs remain the source of truth).
"""
from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "0033_weighbridge_ticket_no"
down_revision = "0032_shipment_leg_pdf_ref"
branch_labels = None
depends_on = None


COLUMN_COMMENT = (
    "Paper weighbridge ticket number from supplier scale logs. "
    "Source of truth = paper records held by cliente (cf. "
    "docs/audit-dft-c1-paper-records-statement.md). NULL for rows not yet "
    "transcribed from paper. Not unique: multiple daily_inputs rows may "
    "share a ticket (split per supplier / product); same number can "
    "repeat across years on different scales. Added 2026-05-26 per audit "
    "red-team round 1 finding X5."
)


def upgrade() -> None:
    op.execute(
        "ALTER TABLE daily_inputs "
        "ADD COLUMN IF NOT EXISTS weighbridge_ticket_no varchar(64)"
    )
    op.execute(
        f"COMMENT ON COLUMN daily_inputs.weighbridge_ticket_no IS "
        f"$cmt${COLUMN_COMMENT}$cmt$"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_daily_inputs_weighbridge_ticket "
        "ON daily_inputs (entry_date, weighbridge_ticket_no) "
        "WHERE weighbridge_ticket_no IS NOT NULL AND deleted_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_daily_inputs_weighbridge_ticket")
    op.execute(
        "ALTER TABLE daily_inputs DROP COLUMN IF EXISTS weighbridge_ticket_no"
    )
