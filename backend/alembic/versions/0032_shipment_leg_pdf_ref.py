"""shipment_leg.pdf_ref — add per-leg document PDF path

Most ``shipment_leg`` rows already carry a *business* document
identifier in ``document_ref`` (BL ocean number, MRN, eRSV no., etc.).
What was missing is a pointer to the actual PDF on disk for each leg
— mirroring ``consignment_pos_customs.pdf_ref`` (EAD) and
``consignment_pos_customs.invoice_pdf_ref`` (commercial invoice).

Audit-aligned design:
    * Column holds a path **relative** to ``/data/bl_ocean`` (or another
      per-leg-type root in the future).  Path-traversal is guarded at
      the streaming route via ``Path.resolve().relative_to(root)``.
    * Filenames on disk preserve the Drive-provenance trail, e.g.
      ``c-1/BL_CMDU856254189_CARTAGENA_EXPRES_2025-06-11.pdf`` — the
      filename alone tells the auditor BL#, vessel, issuing date
      without a DB lookup.
    * Lookup keyed on ``(consignment_id, document_ref)`` — business key,
      never on auto-increment id (cf. migration row-id portability
      rule).

This migration is purely additive: no backfill, no constraint changes.
The backfill is performed out-of-band by the operator (rsync PDFs into
``data/bl_ocean/c-<cid>/`` + a portable UPDATE keyed on business
columns).
"""
from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "0032_shipment_leg_pdf_ref"
down_revision = "0031_pos_invoice_pdf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE shipment_leg "
        "ADD COLUMN IF NOT EXISTS pdf_ref TEXT"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE shipment_leg "
        "DROP COLUMN IF EXISTS pdf_ref"
    )
