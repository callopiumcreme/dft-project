"""retire_legacy_suppliers — soft-deprecate SANIMAX, CIECOGRAS,
ECODIESEL and their bound certificates as confirmed legacy / non-
active by the client on 2026-05-26.

Context:
    Drive `gdrive:DFT_2025/RTFO-310825/03_supplier_evidence/certificates/`
    is the canonical active-supplier set for DEL-CRW-2025-2 (Q3 2025
    Crown Oil bundle). Folder contents: BIOWASTE, BOLDER INDUSTRIES,
    EFFICIEN TECHNOLOGY, ESENTTIA, KAL TIRE, LITOPLAS, PYRCOM,
    plus the OisteBio own EU cert and UTB off-taker cert.

    Suppliers SANIMAX (id 2), CIECOGRAS (id 4), ECODIESEL (id 6) are
    NOT present in that authoritative active set. Paolo confirmed
    2026-05-26 verbatim: "abbiamo solo i fornitori attivi, tutto il
    resto non esiste più... sanimax/ecodiesel e cecogras... trash".

    Migration 0038 (2026-05-26) restored these three suppliers from a
    previous soft-delete to support cert re-attribution analysis.
    After cert re-attribution, all daily_inputs against these
    suppliers were soft-deleted (1532 SANIMAX, 1314 CIECOGRAS, 0
    ECODIESEL). Current live activity for the trio is zero. With
    the client's explicit "trash" classification, the supplier rows
    themselves can now be soft-deprecated without orphaning live
    data.

Pre-check ground truth (executed 2026-05-26, head 0038):
    suppliers : SANIMAX/CIECOGRAS/ECODIESEL all deleted_at=NULL,
                all di_active=0, all kg_active=0
    certs     : ES216-20258083 (SANIMAX, status=active, 1514 di all
                soft-deleted), ES216-20244036 (CIECOGRAS, expired,
                0 di), US201-100862024 (ECODIESEL, expired, 0 di)
    bindings  : 1-to-1 supplier_certificates rows, clean
    other FKs : off_taker / shipment_leg references = 0

Migration plan (UPDATEs keyed on business identifiers ONLY — per
`feedback_migration_row_id_portability`; NEVER auto-increment ids):

    A. Soft-deprecate 3 suppliers:
       - deleted_at = NOW()
       - active     = FALSE
       - notes appended with retirement reason
       Selector: code IN ('SANIMAX','CIECOGRAS','ECODIESEL')

    B. Soft-deprecate 3 certificates:
       - deleted_at = NOW()
       - status     = 'revoked'  (CHECK-constraint legal value)
       - notes appended with retirement reason
       Selector: cert_number IN ('ES216-20258083','ES216-20244036',
                                 'US201-100862024')

    C. supplier_certificates bindings: LEFT IN PLACE.
       Table has no deleted_at column and composite PK. Cascade only
       triggers on hard delete (not soft). Preserving bindings keeps
       historical chain-of-custody readable for ISCC audit (per
       `project_iscc_audit_safety`).

    D. Audit log: one 'supplier_retire' + one 'certificate_retire'
       entry per affected row, with old_values/new_values payloads
       capturing the state transition.

Downgrade reverses A and B (restores deleted_at=NULL, active=TRUE,
status='active'/'expired' to original). Audit log entries are NOT
removed (audit trail preserved).
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0039_retire_legacy_suppliers"
down_revision = "0038_cert_reality_sync"
branch_labels = None
depends_on = None


# Business-key tuples driving the migration.
LEGACY_SUPPLIER_CODES = ("SANIMAX", "CIECOGRAS", "ECODIESEL")
LEGACY_CERT_NUMBERS = (
    "ES216-20258083",  # SANIMAX (was active)
    "ES216-20244036",  # CIECOGRAS (was expired)
    "US201-100862024",  # ECODIESEL (was expired)
)


def upgrade() -> None:
    # -----------------------------------------------------------------
    # A. Soft-deprecate suppliers
    # -----------------------------------------------------------------
    op.execute(
        """
        WITH retired AS (
            UPDATE suppliers
            SET deleted_at = NOW(),
                active = FALSE,
                notes = COALESCE(notes, '')
                    || E'\nRetired 2026-05-26 (migration 0039): supplier '
                    || 'confirmed legacy / non-active by client. Not in '
                    || 'Drive RTFO-310825/03_supplier_evidence/certificates '
                    || 'authoritative active set. All daily_inputs already '
                    || 'soft-deleted; supplier row soft-deprecated for '
                    || 'audit-trail preservation (no hard delete).'
            WHERE code IN ('SANIMAX', 'CIECOGRAS', 'ECODIESEL')
              AND deleted_at IS NULL
            RETURNING id, code, name, active
        )
        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values)
        SELECT 'suppliers', id, 'soft_delete',
               jsonb_build_object('code', code,
                                  'deleted_at', NULL,
                                  'active', true),
               jsonb_build_object('code', code,
                                  'deleted_at', NOW(),
                                  'active', false,
                                  'kind', 'supplier_retire',
                                  'reason', 'client-confirmed legacy 2026-05-26',
                                  'migration', '0039_retire_legacy_suppliers')
        FROM retired;
        """
    )

    # -----------------------------------------------------------------
    # B. Soft-deprecate certificates (status -> revoked, deleted_at set)
    # -----------------------------------------------------------------
    op.execute(
        """
        WITH retired AS (
            UPDATE certificates
            SET deleted_at = NOW(),
                status = 'revoked',
                notes = COALESCE(notes, '')
                    || E'\nRevoked 2026-05-26 (migration 0039): bound to '
                    || 'legacy supplier retired same migration. No active '
                    || 'daily_inputs. Kept for historical chain integrity '
                    || '(soft-delete, no hard purge).'
            WHERE cert_number IN ('ES216-20258083',
                                  'ES216-20244036',
                                  'US201-100862024')
              AND deleted_at IS NULL
            RETURNING id, cert_number, status
        )
        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values)
        SELECT 'certificates', r.id, 'soft_delete',
               jsonb_build_object('cert_number', r.cert_number,
                                  'deleted_at', NULL,
                                  'status', CASE r.cert_number
                                      WHEN 'ES216-20258083' THEN 'active'
                                      ELSE 'expired'
                                  END),
               jsonb_build_object('cert_number', r.cert_number,
                                  'deleted_at', NOW(),
                                  'status', 'revoked',
                                  'kind', 'certificate_retire',
                                  'reason', 'supplier retired 2026-05-26',
                                  'migration', '0039_retire_legacy_suppliers')
        FROM retired r;
        """
    )

    # -----------------------------------------------------------------
    # C. Bindings left in place by design (see docstring).
    # -----------------------------------------------------------------


def downgrade() -> None:
    # B-reverse: restore certificates to pre-retire state
    op.execute(
        """
        UPDATE certificates
        SET deleted_at = NULL,
            status = CASE cert_number
                WHEN 'ES216-20258083' THEN 'active'
                ELSE 'expired'
            END
        WHERE cert_number IN ('ES216-20258083',
                              'ES216-20244036',
                              'US201-100862024');
        """
    )

    # A-reverse: restore suppliers
    op.execute(
        """
        UPDATE suppliers
        SET deleted_at = NULL,
            active = TRUE
        WHERE code IN ('SANIMAX', 'CIECOGRAS', 'ECODIESEL');
        """
    )

    # Audit log preserved (no DELETE).
