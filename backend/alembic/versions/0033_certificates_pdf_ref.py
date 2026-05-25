"""certificates.pdf_ref — add on-disk PDF path for ISCC certificates

The existing ``certificates.document_url`` column holds the **external**
URL (e.g. ISCC Hub permalink) and is currently NULL on all 18 prod rows.
Adding ``pdf_ref`` mirrors the naming pattern already established by:

    * ``shipment_leg.pdf_ref``               (migration 0032)
    * ``consignment_pos.pdf_ref``            (migration earlier)
    * ``consignment_pos_customs.pdf_ref``    (EAD, migration 0030)
    * ``consignment_pos_customs.invoice_pdf_ref`` (migration 0031)

Audit-aligned design:
    * Column holds a path **relative** to ``/data/certificates`` — guarded
      at the streaming route via ``Path.resolve().relative_to(root)``
      (cf. consignments PDF stream pattern).
    * Filename on disk preserves provenance, e.g.
      ``utb-bv/CERTIFICATE_UTB_BV.pdf``.
    * Lookup keyed on ``cert_number`` (business key, UNIQUE) — never on
      auto-increment id (cf. migration row-id portability rule).
    * ``document_url`` stays for ISCC Hub public link / Drive backup —
      two semantics, two columns.

Pure additive: no backfill in the migration. UTB BV cert row + PDF
placement performed by the operator (``data/certificates/utb-bv/...``
bind-mount + portable INSERT keyed on ``cert_number``).
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0033_certificates_pdf_ref"
down_revision = "0032_shipment_leg_pdf_ref"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE certificates "
        "ADD COLUMN IF NOT EXISTS pdf_ref TEXT"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE certificates "
        "DROP COLUMN IF EXISTS pdf_ref"
    )
