"""c14_certificate_schema — new table for the FMS Appendix A C14 Laboratory
Certificates Log (radiocarbon / bio-based carbon content of DEV-P100).

Context:
    The Fuel Measurement & Sampling Procedure (FMS) mandates an
    "Appendix A — C14 Laboratory Certificates Log" that links each monthly
    radiocarbon analysis certificate (EN 16640 Annex B) to the production
    batch and the downstream sustainability declaration. Eight certificates
    Jan–Aug 2025, one per month:
        Jan  Bureau Veritas Amsterdam  NLADM-25-00196-001
        Feb–Aug  AmSpec Amsterdam      642-…/655-…/677-…/691-…/697-…/701-…/784-…
    Each certificate PDF lives under the bind-mounted data/c14/<cert_number>.pdf
    (mirrors product_purchases / contracts PDF serving; no Drive at runtime).

    First pass is read-only (list + inline viewer + audited download);
    CRUD/upload from UI deferred. The sustainability_decl link is seeded with a
    default (DEL-CRW-2025-2) and is rectifiable later once the cert→batch→SD
    mapping is finalised — structure ready for the definitive version.

Migration plan (DDL only — no data rows; seed handled by
scripts/backfill_c14_certificates.py per feedback_backfill_after_migration):

    A. CREATE TABLE c14_certificates
       - id                  bigserial PK
       - cert_number         text UNIQUE NOT NULL  (lab report number)
       - lab                 text   (Bureau Veritas Amsterdam / AmSpec Amsterdam)
       - product             text   (DEV-P100 / Refined Pyrolysis oil)
       - period_month        date   (first of month: 2025-01-01 … 2025-08-01)
       - sampled_date        date
       - tested_date         date
       - report_date         date
       - bio_carbon_pct      numeric(5,2)  (bio-based carbon content %)
       - method              text   (EN 16640 Annex B)
       - sample_ref          text   (lab sample id, e.g. "bt sample 250 ml")
       - batch_ref           text   (production batch link — rectifiable)
       - sustainability_decl text   (downstream SD link — default DEL-CRW-2025-2)
       - pdf_filename         text  (data/c14/<file>.pdf)
       - notes               text
       - created_at          timestamptz NOT NULL DEFAULT now()
       - updated_at          timestamptz NOT NULL DEFAULT now()
       - deleted_at          timestamptz  (soft delete)

    B. Index on period_month (chronological listing) + partial index excluding
       soft-deleted for the default listing.

    C. Audit log meta entry — single 'update' row (record_id=0) tagging
       new_values.kind='schema_extend' per audit_log.action CHECK
       (allows {insert,update,delete,soft_delete,restore,pdf_sign}).

Downgrade:
    DROP TABLE c14_certificates (IF EXISTS). Audit log entry preserved.
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0047_c14_certificate_schema"
down_revision = "0046_product_purchases_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS c14_certificates (
            id                  bigserial PRIMARY KEY,
            cert_number         text NOT NULL UNIQUE,
            lab                 text,
            product             text,
            period_month        date,
            sampled_date        date,
            tested_date         date,
            report_date         date,
            bio_carbon_pct      numeric(5,2),
            method              text,
            sample_ref          text,
            batch_ref           text,
            sustainability_decl text,
            pdf_filename        text,
            notes               text,
            created_at          timestamptz NOT NULL DEFAULT now(),
            updated_at          timestamptz NOT NULL DEFAULT now(),
            deleted_at          timestamptz
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_c14_certificates_period_month "
        "ON c14_certificates (period_month);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_c14_certificates_active "
        "ON c14_certificates (cert_number) WHERE deleted_at IS NULL;"
    )

    op.execute(
        """
        -- audit_log.action CHECK only allows
        -- {insert,update,delete,soft_delete,restore,pdf_sign}.
        -- Use 'update' with record_id=0 marker + new_values.kind
        -- carrying the semantic 'schema_extend' tag.
        INSERT INTO audit_log (table_name, record_id, action,
                               old_values, new_values)
        VALUES (
            'c14_certificates',
            0,
            'update',
            NULL,
            jsonb_build_object(
                'kind', 'schema_extend',
                'migration', '0047_c14_certificate_schema',
                'columns', jsonb_build_array(
                    'id', 'cert_number', 'lab', 'product', 'period_month',
                    'sampled_date', 'tested_date', 'report_date',
                    'bio_carbon_pct', 'method', 'sample_ref', 'batch_ref',
                    'sustainability_decl', 'pdf_filename', 'notes',
                    'created_at', 'updated_at', 'deleted_at'
                )
            )
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS c14_certificates;")
