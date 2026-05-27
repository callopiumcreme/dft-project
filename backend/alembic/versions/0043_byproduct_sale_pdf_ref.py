"""add ``byproduct_sale.pdf_ref`` for per-invoice PDF storage

Story: F0-D (Conquer Trade DEV-P200 invoice viewer in the warehouse UI).
The 8 Q3-2025 Conquer Trade invoices CONQ-250001..250008 were ingested
in commit ``a5c088c`` from a single consolidated PDF in Drive
(``DFT_2025/INVOICES_CONQUER/INVOICES TO CONQUER 8.pdf``). To make each
invoice individually viewable + downloadable in
``/app/warehouse/byproduct-sales``, the consolidated PDF is split into 8
single-page files under ``data/byproduct/`` and each ``byproduct_sale``
row carries a relative path in the new ``pdf_ref`` column.

The column is nullable: pre-existing byproduct sales (carbon black,
metal scrap) without per-invoice PDFs simply keep ``pdf_ref = NULL`` and
the UI renders ``invoice_no`` as plain text. Conquer rows are backfilled
out-of-band by ``scripts/backfill_conquer_q3_2025.py`` (next revision)
keyed on the business key ``invoice_no`` for env portability.

Storage layout mirrors transload / customs: ``data/byproduct/`` is
bind-mounted into the backend container at ``/data/byproduct``; path
traversal is guarded at the streaming route via
``Path.resolve().relative_to(root)``.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0043_byproduct_sale_pdf_ref"
down_revision = "0042_d17_cosmetic_cleanup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "byproduct_sale",
        sa.Column("pdf_ref", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("byproduct_sale", "pdf_ref")
