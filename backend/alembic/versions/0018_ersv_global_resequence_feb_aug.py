"""eRSV global resequence Feb-Aug 2025 — enforce uniqueness

Revision ID: 0018
Revises: 0017
Create Date: 2026-05-22

Migration 0017 assigned ``ersv_number`` via a PER-supplier annual
counter, reset for each supplier. With 5 redistributed suppliers
sharing the same 1..N counter space, this produced 381 colliding
numbers — 82 of them appearing 5 times — across distinct
``daily_inputs`` rows.

A paper eRSV identifies one physical load. Duplicates break the
1-eRSV-to-1-load audit invariant relied on by the ISCC mass-balance
chain of custody.

This migration:
    1. Renumbers every plain-format (``NNNNN/25``) eRSV with
       ``entry_date >= 2025-02-01`` sequentially by
       ``(entry_date ASC, id ASC)`` into ``00001/25 .. 0NNNN/25``,
       5-digit zero-padded.
    2. Adds a partial UNIQUE index forbidding future collisions
       among non-deleted rows.

Out of scope (left untouched):
    - January 2025: FROZEN, 3-digit ``NNN/25`` namespace
      (already in RTFO-310125 bundle).
    - LE5TON ≤5 TON prefixed numbers (``CAMB-``, ``LANT-``, ``REEC-``,
      ``SUNS-``): separate doc format, not affected by 0017
      redistribution.
"""

from alembic import op


revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH renum AS (
            SELECT
                id,
                LPAD(
                    (ROW_NUMBER() OVER (ORDER BY entry_date ASC, id ASC))::text,
                    5, '0'
                ) || '/25' AS new_number
            FROM daily_inputs
            WHERE deleted_at IS NULL
              AND ersv_number IS NOT NULL
              AND entry_date >= DATE '2025-02-01'
              AND ersv_number ~ '^[0-9]+/25$'
        )
        UPDATE daily_inputs di
        SET ersv_number = renum.new_number
        FROM renum
        WHERE di.id = renum.id;
        """
    )

    # Partial UNIQUE — Feb+ only. Jan 2025 (FROZEN paper bundle) has
    # legacy 2-of-a-kind duplicates that are out of scope for this fix.
    op.execute(
        """
        CREATE UNIQUE INDEX ux_daily_inputs_ersv_number_feb_aug
          ON daily_inputs (ersv_number)
          WHERE deleted_at IS NULL
            AND ersv_number IS NOT NULL
            AND entry_date >= DATE '2025-02-01';
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_daily_inputs_ersv_number_feb_aug;")
