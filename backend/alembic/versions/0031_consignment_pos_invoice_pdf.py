"""consignment_pos_customs.invoice_pdf_ref — add per-PoS invoice doc ref

Each PoS (OISCRO-XXXX-25 series) has one commercial invoice issued by
OisteBio Swiss GmbH to Crown Oil Ltd (the sole buyer).  The invoice
number already lives on ``consignment_pos_customs.invoice_no`` but
until now there was no pointer to the actual PDF on disk.

This migration adds ``invoice_pdf_ref`` (TEXT NULL), holding a path
**relative** to ``/data/invoices`` (bind-mounted read-only into the
backend container) so the path stays portable across local + server.

Backfill (separate script) splits the master bundle
``invoices TO CROWN OIL.pdf`` into 20 per-invoice files under
``/data/invoices/c-<consignment_id>/INV_<invoice_no>.pdf`` and
populates this column.

Soft-delete: column lives on existing table, inherits its
``deleted_at`` semantics — no schema changes needed elsewhere.
"""
from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "0031_pos_invoice_pdf"
down_revision = "0030_pos_customs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE consignment_pos_customs "
        "ADD COLUMN IF NOT EXISTS invoice_pdf_ref TEXT"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE consignment_pos_customs "
        "DROP COLUMN IF EXISTS invoice_pdf_ref"
    )
