"""Replace consignment_pos composite PK with surrogate id + partial UNIQUE.

Project rule "MAI hard delete — usare soft delete" requires that any row
flagged with ``deleted_at = NOW()`` becomes inert from the application's
point of view, freeing its natural key for re-insertion. ``consignment_pos``
violated that rule: a composite PRIMARY KEY on
``(consignment_id, pos_number)`` blocked re-insertion of the same natural
key after soft-deletion (hard PK violation, not the intended partial
UNIQUE pattern).

Fix:
  * drop composite PK ``consignment_pos_pkey``
  * add surrogate ``id BIGSERIAL PRIMARY KEY``
  * create partial UNIQUE index
    ``ux_consignment_pos_active (consignment_id, pos_number)
       WHERE deleted_at IS NULL``
    so active rows still cannot collide on the natural key.

No incoming FK references the composite PK:
``mass_balance_ledger`` joins via ``(ref_table, ref_id)`` plus the
separate FK to ``consignment(id)``; nothing depends on
``consignment_pos.pos_number``. Verified via ``pg_constraint`` at design
time. The existing FK
``consignment_pos_consignment_id_fkey`` (consignment_id -> consignment.id)
is preserved untouched.

Revision ID: 0028_consignment_pos_soft_delete_unique
Revises: 0027_pos_issuance_date
Create Date: 2026-05-24
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0028_consignment_pos_softdel"
down_revision = "0027_pos_issuance_date"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop composite PK so we can introduce the surrogate id.
    op.execute("ALTER TABLE consignment_pos DROP CONSTRAINT consignment_pos_pkey")

    # 2. Add surrogate id (BIGSERIAL = bigint + sequence + PK).
    op.execute(
        "ALTER TABLE consignment_pos "
        "ADD COLUMN id bigserial PRIMARY KEY"
    )

    # 3. Partial UNIQUE on natural key for active rows only.
    op.execute(
        "CREATE UNIQUE INDEX ux_consignment_pos_active "
        "ON consignment_pos (consignment_id, pos_number) "
        "WHERE deleted_at IS NULL"
    )


def downgrade() -> None:
    # Reverse: drop partial UNIQUE, drop surrogate id + its PK, restore
    # composite PK on (consignment_id, pos_number).
    #
    # Downgrade is only safe if there are no soft-deleted rows that would
    # collide with active rows on the natural key. We rely on the existing
    # partial UNIQUE to guarantee uniqueness among active rows; any
    # tombstoned rows must be hard-deleted first by the operator (Alembic
    # downgrades are not expected in production — this branch is for
    # roundtrip verification only).
    op.execute("DROP INDEX IF EXISTS ux_consignment_pos_active")
    op.execute("ALTER TABLE consignment_pos DROP CONSTRAINT consignment_pos_pkey")
    op.drop_column("consignment_pos", "id")
    op.execute(
        "ALTER TABLE consignment_pos "
        "ADD CONSTRAINT consignment_pos_pkey "
        "PRIMARY KEY (consignment_id, pos_number)"
    )
    # sa is imported to satisfy ruff F401 patterns elsewhere; explicit no-op.
    _ = sa
