"""consignment_pos_customs — EAD (Export Accompanying Document) per PoS

Outbound from the EU is filed through Dutch customs by **BiNova BV** as
NL declarant (a legal-entity requirement: OisteBio Swiss GmbH cannot
file customs declarations from NL ports directly).  Each container
shipment produces one DMS Export Accompanying Document (EAD) with a
unique MRN (Movement Reference Number) and an LRN (Local Reference
Number).  Operationally each EAD maps 1:1 with one OisteBio PoS
(OISCRO-XXXX-25 series) by (issuance_date, kg_net, container).

Until this migration the landing UI rendered ISCC PoS PDFs under the
"Outbound" section and labelled the column "eRSV outbound" — both
wrong: PoS is the ISCC declaration (correct in chain) but the
**customs** document is the EAD/DMS PDF, and "eRSV" is a Colombia-only
format (used for inbound feedstock + Girardot→Cartagena inland), never
for the EU→UK leg.  This table introduces the customs record so the
landing can show the correct EAD docs without renaming or replacing
the underlying PoS row.

Storage:
  * PDF lives on disk under ``/data/customs/c-<consignment_id>/...``
    (bind-mounted read-only into the backend container, see
    ``docker-compose.yml``).  ``pdf_ref`` holds the path relative to
    ``/data/customs`` so it stays portable across local/server.
  * The backend exposes a small auth-gated streaming endpoint that
    serves the file by MRN; the landing renders it in a popup with a
    download fallback.  **No Drive runtime dependency.**

Soft-delete: ``deleted_at`` for parity with ``consignment_pos``.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision = "0030_pos_customs"
down_revision = "0029_warehouse_ytd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE consignment_pos_customs (
            id              BIGSERIAL PRIMARY KEY,
            consignment_id  BIGINT NOT NULL
                              REFERENCES consignment(id) ON DELETE CASCADE,
            pos_number      TEXT   NOT NULL,
            mrn             TEXT   NOT NULL,
            lrn             TEXT,
            customs_office  TEXT,
            container_no    TEXT,
            gross_kg        NUMERIC(14,3),
            net_kg          NUMERIC(14,3),
            invoice_no      TEXT,
            declarant_name  TEXT,
            declarant_vat   TEXT,
            issuing_date    DATE,
            pdf_ref         TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at      TIMESTAMPTZ
        )
        """
    )

    # Each (consignment, PoS) has at most one *active* customs record.
    op.execute(
        """
        CREATE UNIQUE INDEX ux_pos_customs_active
          ON consignment_pos_customs (consignment_id, pos_number)
          WHERE deleted_at IS NULL
        """
    )
    # MRN is globally unique among active rows.
    op.execute(
        """
        CREATE UNIQUE INDEX ux_pos_customs_mrn_active
          ON consignment_pos_customs (mrn)
          WHERE deleted_at IS NULL
        """
    )
    op.execute(
        "CREATE INDEX ix_pos_customs_consignment "
        "ON consignment_pos_customs (consignment_id) "
        "WHERE deleted_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS consignment_pos_customs")
