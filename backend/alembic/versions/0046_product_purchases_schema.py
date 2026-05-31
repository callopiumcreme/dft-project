"""product_purchases_schema — new table for supplier-issued Sustainability
Declarations (PoS) of purchased feedstock.

Context:
    "Product Purchases" operational chapter (landing/app, Operations group).
    Publishes upstream supplier PoS that document feedstock OisteBio
    purchased (ELT) — e.g. ESENTTIA ES2025-014, KAL-OIS-007, ET-OB-25-006,
    OISTEBIO-2025-001, 2025-OISTE-004. Each PoS PDF lives under the
    bind-mounted data/pos/<pos_number>.pdf (mirrors contracts PDF serving;
    no Drive at runtime).

    First pass is read-only (list + inline viewer + audited download);
    CRUD/upload from UI deferred per scope decision 2026-05-30.

Migration plan (DDL only — no data rows inserted here; seed handled by
scripts/backfill_product_purchases.py per feedback_backfill_after_migration):

    A. CREATE TABLE product_purchases
       - id              bigserial PK
       - pos_number      text UNIQUE NOT NULL   (supplier PoS unique number)
       - supplier_id     bigint FK suppliers(id)     ON DELETE SET NULL
       - certificate_id  bigint FK certificates(id)  ON DELETE SET NULL
       - contract_id     bigint FK contracts(id)     ON DELETE SET NULL
       - issuance_date   date
       - dispatch_label  text   (free text: a date OR an aggregate label
                                  e.g. "aggregated deliveries from 7 january
                                  to 31 January")
       - quantity_kg     numeric(14,3)
       - feedstock       text   (e.g. "ELT END OF LIFE TIRES")
       - notes           text
       - created_at      timestamptz NOT NULL DEFAULT now()
       - updated_at      timestamptz NOT NULL DEFAULT now()
       - deleted_at      timestamptz            (soft delete)

    B. Index on supplier_id (list filter) + partial index excluding
       soft-deleted for the default listing.

    C. Audit log meta entry — single 'update' row (record_id=0) tagging
       new_values.kind='schema_extend' per audit_log.action CHECK
       (allows {insert,update,delete,soft_delete,restore,pdf_sign}).

Downgrade:
    DROP TABLE product_purchases (IF EXISTS). Audit log entry preserved.
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0046_product_purchases_schema"
down_revision = "0045_le5ton_cert_drift_cleanup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS product_purchases (
            id              bigserial PRIMARY KEY,
            pos_number      text NOT NULL UNIQUE,
            supplier_id     bigint REFERENCES suppliers(id)    ON DELETE SET NULL,
            certificate_id  bigint REFERENCES certificates(id) ON DELETE SET NULL,
            contract_id     bigint REFERENCES contracts(id)    ON DELETE SET NULL,
            issuance_date   date,
            dispatch_label  text,
            quantity_kg     numeric(14,3),
            feedstock       text,
            notes           text,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            deleted_at      timestamptz
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_product_purchases_supplier_id "
        "ON product_purchases (supplier_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_product_purchases_active "
        "ON product_purchases (pos_number) WHERE deleted_at IS NULL;"
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
            'product_purchases',
            0,
            'update',
            NULL,
            jsonb_build_object(
                'kind', 'schema_extend',
                'migration', '0046_product_purchases_schema',
                'columns', jsonb_build_array(
                    'id', 'pos_number', 'supplier_id', 'certificate_id',
                    'contract_id', 'issuance_date', 'dispatch_label',
                    'quantity_kg', 'feedstock', 'notes',
                    'created_at', 'updated_at', 'deleted_at'
                )
            )
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS product_purchases;")
