"""backfill shipment_leg.pdf_ref for the UTB-2025-Q3-CONSOLIDATED row

Story: DFTEN-166 (E8-G1). Closes the documentation gap on
``shipment_leg`` for the ``utb_transload`` leg of consignment c-1
(DEL-CRW-2025-2). After 0032 added the column, the inbound BL rows were
backfilled out-of-band but the transload row was left NULL because the
UTB-issued consolidated report did not yet exist as a deliverable.

This migration is keyed on the business identifiers
``(consignment.code, leg_type, document_ref)`` — not on auto-increment
ids — so it stays portable across env DBs (cf. migration row-id
portability rule, project memory).

PDF artefact ``UTB-2025-Q3-CONSOLIDATED.pdf`` is rendered out-of-band by
``scripts/render_transload_consolidated.py`` and lives at
``data/transload/c-1/`` (gitignored by the global ``data/`` rule). The
column stores the path **relative** to ``/data/transload`` (the bind-mount
root inside the backend container); path-traversal is guarded at the
streaming route via ``Path.resolve().relative_to(root)``.
"""
from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "0034_backfill_transload_pdf_ref"
down_revision = "0033_certificates_pdf_ref"
branch_labels = None
depends_on = None


_REL_PATH = "c-1/UTB-2025-Q3-CONSOLIDATED.pdf"


def upgrade() -> None:
    # Key on business identifiers — consignment code + leg_type + document_ref —
    # so the UPDATE matches the right row in every env (local, demo, prod) even
    # if auto-increment ids differ. Idempotent: re-running is a no-op once set.
    op.execute(
        """
        UPDATE shipment_leg AS sl
        SET pdf_ref = '""" + _REL_PATH + """'
        FROM consignment AS c
        WHERE sl.consignment_id = c.id
          AND c.code = 'DEL-CRW-2025-2'
          AND sl.leg_type = 'utb_transload'
          AND sl.document_ref = 'UTB-2025-Q3-CONSOLIDATED'
          AND sl.deleted_at IS NULL
          AND (sl.pdf_ref IS NULL OR sl.pdf_ref = '')
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE shipment_leg AS sl
        SET pdf_ref = NULL
        FROM consignment AS c
        WHERE sl.consignment_id = c.id
          AND c.code = 'DEL-CRW-2025-2'
          AND sl.leg_type = 'utb_transload'
          AND sl.document_ref = 'UTB-2025-Q3-CONSOLIDATED'
          AND sl.pdf_ref = '""" + _REL_PATH + """'
        """
    )
