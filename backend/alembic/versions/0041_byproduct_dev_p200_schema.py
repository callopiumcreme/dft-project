"""byproduct_dev_p200_schema — extend byproduct_sale to accept DEV-P200
fossil-equivalent product kind, add pricing-metadata columns required
to ingest Conquer Trade Q3 2025 invoices (8 invoices pending, folder
`gdrive:DFT_2025/INVOICES_CONQUER/`).

Context:
    DFT-C1 Red-Audit Round-4 criterion C11 = FAIL (gap noto): existing
    CHECK constraint on byproduct_sale.product_kind only admitted
    ('plus_oil','carbon_black','metal_scrap'). DEV-P200 (fossil-
    equivalent pyrolysis oil) sold to Conquer Trade has no slot.

    Client confirmation 2026-05-27 (questionnaire `gdrive:DFT_2025/
    AUDIT report/messaggio_cliente.docx` + reply via `gdrive:DFT_2025/
    AGGIORNAMENTI PROGETTO DFT.docx` mtime 2026-05-26 20:47 + direct
    chat clarification 2026-05-27):
      A1. product_kind label              → 'dev_p200'
      A3. currency                        → 'USD'
          pricing_method                  → 'brent_monthly_avg'
                                            (invoice issued start of
                                            following month, price =
                                            Brent monthly avg × density
                                            0.86 → USD/MT)
          incoterm                        → 'EXW_GIRARDOT'
                                            (Ex Works Girardot plant;
                                            Conquer Trade bears
                                            transit risk + cost from
                                            gate onward)
      A4. invoice_no source               → file name stem
                                            'CONQ-2025-NNNN' = the
                                            invoice_number itself
                                            (handled by import script,
                                            no schema change here)

    Quality-grade params (A2) intentionally NOT stored — client
    confirmed quality parameters are NOT included on Conquer invoices
    ("NON METTIAMO INFO PARAMETRI IN FATTURA").

Migration plan (DDL only — no data UPDATE; per
`feedback_migration_row_id_portability` business-key keying not
applicable because no rows are mutated):

    A. DROP existing CHECK constraint
       'byproduct_sale_product_kind_check' and recreate including
       'dev_p200'.

    B. ADD COLUMN price_amount  numeric(14,2)  NULL
       — invoice line amount in original currency.
       Existing `price_eur` left in place for backward compatibility
       with legacy plus_oil/carbon_black/metal_scrap rows.

    C. ADD COLUMN currency        text  NULL
       — ISO-4217 code; expected values 'USD','EUR','COP'.
       Free text (no CHECK) to remain forward-compatible with future
       currencies; convention enforced at application layer.

    D. ADD COLUMN pricing_method  text  NULL
       — pricing rule documentation; current Conquer usage
       'brent_monthly_avg' (price = Brent average of month N, billed
       early month N+1). Free text for forward extension.

    E. ADD COLUMN incoterm        text  NULL
       — Incoterms 2020 + delivery point token; current Conquer usage
       'DAP_PUERTO_ORION_CARTAGENA' (Delivered At Place, Puerto Orion
       port Cartagena CO; OisteBio bears transit risk Girardot →
       port). Free text for forward extension.

    F. Audit log meta entry — single 'schema_extend' row documenting
       the migration and the four new columns + CHECK widening.

Downgrade:
    Reverses E→D→C→B (DROP COLUMN, IF EXISTS for safety).
    Restores original CHECK constraint. If any dev_p200 row exists
    (deleted_at IS NULL), downgrade raises to refuse silent data
    loss — operator must remediate before downgrading.
    Audit log entry preserved.
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0041_byproduct_dev_p200_schema"
down_revision = "0040_wipe_c14_parse_frags"
branch_labels = None
depends_on = None


# Existing kinds + the new addition.
LEGACY_KINDS = ("plus_oil", "carbon_black", "metal_scrap")
NEW_KIND = "dev_p200"


def upgrade() -> None:
    # -----------------------------------------------------------------
    # A. CHECK constraint widening — drop & recreate.
    # -----------------------------------------------------------------
    op.execute(
        "ALTER TABLE byproduct_sale "
        "DROP CONSTRAINT IF EXISTS byproduct_sale_product_kind_check;"
    )
    op.execute(
        """
        ALTER TABLE byproduct_sale
        ADD CONSTRAINT byproduct_sale_product_kind_check
        CHECK (product_kind IN (
            'plus_oil',
            'carbon_black',
            'metal_scrap',
            'dev_p200'
        ));
        """
    )

    # -----------------------------------------------------------------
    # B-E. New nullable columns (no DEFAULT — preserves NULL semantics
    # for historical rows; only Conquer-era rows will populate these).
    # -----------------------------------------------------------------
    op.execute(
        "ALTER TABLE byproduct_sale "
        "ADD COLUMN IF NOT EXISTS price_amount numeric(14,2);"
    )
    op.execute(
        "ALTER TABLE byproduct_sale "
        "ADD COLUMN IF NOT EXISTS currency text;"
    )
    op.execute(
        "ALTER TABLE byproduct_sale "
        "ADD COLUMN IF NOT EXISTS pricing_method text;"
    )
    op.execute(
        "ALTER TABLE byproduct_sale "
        "ADD COLUMN IF NOT EXISTS incoterm text;"
    )

    # -----------------------------------------------------------------
    # F. Audit log meta entry — one row documenting the DDL change.
    # record_id = 0 marker (no specific row affected; whole-table DDL).
    # -----------------------------------------------------------------
    op.execute(
        """
        -- audit_log.action CHECK only allows
        -- {insert,update,delete,soft_delete,restore,pdf_sign}.
        -- Use 'update' with record_id=0 marker + new_values.kind
        -- carrying the semantic 'schema_extend' tag.
        INSERT INTO audit_log (table_name, record_id, action,
                               old_values, new_values)
        VALUES (
            'byproduct_sale',
            0,
            'update',
            jsonb_build_object(
                'check_kinds', jsonb_build_array(
                    'plus_oil', 'carbon_black', 'metal_scrap'
                )
            ),
            jsonb_build_object(
                'check_kinds', jsonb_build_array(
                    'plus_oil', 'carbon_black', 'metal_scrap', 'dev_p200'
                ),
                'columns_added', jsonb_build_array(
                    'price_amount', 'currency',
                    'pricing_method', 'incoterm'
                ),
                'kind', 'byproduct_dev_p200_schema_extend',
                'reason', 'DFT-C1 C11 gap closure + Conquer Q3 2025 '
                          'invoices ingest preparation '
                          '(client confirm 2026-05-27)',
                'migration', '0041_byproduct_dev_p200_schema'
            )
        );
        """
    )


def downgrade() -> None:
    # Safety guard: refuse downgrade if dev_p200 data exists.
    op.execute(
        """
        DO $$
        DECLARE
            n integer;
        BEGIN
            SELECT COUNT(*) INTO n
            FROM byproduct_sale
            WHERE product_kind = 'dev_p200'
              AND deleted_at IS NULL;
            IF n > 0 THEN
                RAISE EXCEPTION
                    'Cannot downgrade 0041: % dev_p200 rows live. '
                    'Soft-delete or re-classify first.', n;
            END IF;
        END $$;
        """
    )

    # Drop the four new columns (IF EXISTS makes downgrade idempotent).
    op.execute(
        "ALTER TABLE byproduct_sale "
        "DROP COLUMN IF EXISTS incoterm;"
    )
    op.execute(
        "ALTER TABLE byproduct_sale "
        "DROP COLUMN IF EXISTS pricing_method;"
    )
    op.execute(
        "ALTER TABLE byproduct_sale "
        "DROP COLUMN IF EXISTS currency;"
    )
    op.execute(
        "ALTER TABLE byproduct_sale "
        "DROP COLUMN IF EXISTS price_amount;"
    )

    # Restore original CHECK constraint.
    op.execute(
        "ALTER TABLE byproduct_sale "
        "DROP CONSTRAINT IF EXISTS byproduct_sale_product_kind_check;"
    )
    op.execute(
        """
        ALTER TABLE byproduct_sale
        ADD CONSTRAINT byproduct_sale_product_kind_check
        CHECK (product_kind IN (
            'plus_oil',
            'carbon_black',
            'metal_scrap'
        ));
        """
    )

    # Audit log meta entry preserved (no DELETE).
