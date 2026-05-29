"""retire_ecogras_2025_cert — soft-deprecate cert ES216-20254036
(CI ECOGRAS COLOMBIA SAS, 2025 vintage) missed by migration 0039.

Context:
    Migration 0039 (2026-05-26) retired the legacy supplier trio
    (SANIMAX / CIECOGRAS / ECODIESEL) and their bound certificates
    (ES216-20258083, ES216-20244036, US201-100862024). Paolo's
    "trash" classification covered CI ECOGRAS COLOMBIA SAS as an
    entity, but the 2025 vintage cert ES216-20254036 escaped the
    selector because:

      1. Post-0038 it was bound to LE5TON + LITOPLAS (not to the
         retired CIECOGRAS supplier), so a supplier-driven sweep
         missed it.
      2. Its status was 'active' (not 'expired' like the 2024
         vintage ES216-20244036), so the casual "expired legacy"
         heuristic did not catch it either.
      3. The AUDIT-MISMATCH note added by migration 0035 flagged
         the inconsistency but deferred resolution pending client
         clarification — which arrived 2026-05-29: client confirms
         (a) LE5TON is the `≤5 TON` self-declaration aggregate
         bucket, not a real supplier ISCC-coverable by ECOGRAS;
         (b) ECOGRAS as a whole was meant to be retired in the
         2026-05-26 sweep.

Pre-check ground truth (executed 2026-05-29, head 0043):
    cert    : ES216-20254036 id=3, status='active', deleted_at=NULL,
              pdf_ref='supplier-q3/ES216-20254036_ECOGRAS.pdf',
              notes contain 'AUDIT-MISMATCH 2026-05-26' marker.
    bindings: supplier_certificates rows (3, LE5TON) and (3, LITOPLAS)
              both present; neither supplier soft-deleted.
    live di : 1 row remains pointing at cert 3 — id 22097, LE5TON,
              2025-05-24, 4595 kg. All other LE5TON rows (619 live)
              have certificate_id IS NULL, which is the canonical
              self-declaration pattern for the ≤5 TON aggregate
              bucket. The single outlier is a drift-row from pre-0010
              parsing that was never reconciled.

Migration plan (UPDATEs keyed on business identifiers ONLY — per
`feedback_migration_row_id_portability`; NEVER auto-increment ids):

    A. Re-attribute 1 LE5TON daily_input live row away from cert 3:
       - certificate_id 3 -> NULL  (self-decl bucket pattern)
       Selector: certificate_id = (SELECT id WHERE cert_number =
                 'ES216-20254036') AND deleted_at IS NULL AND
                 supplier_id = (SELECT id WHERE code = 'LE5TON')

    B. Soft-deprecate cert ES216-20254036:
       - deleted_at = NOW()
       - status     = 'revoked'  (CHECK-constraint legal value)
       - notes appended with retirement reason
       Selector: cert_number = 'ES216-20254036'

    C. supplier_certificates bindings (LE5TON, LITOPLAS): LEFT IN
       PLACE — same rationale as migration 0039 §C. Composite PK,
       no deleted_at column; preserving rows keeps the historical
       chain-of-custody readable for ISCC audit per
       `project_iscc_audit_safety`. Soft-deprecating the parent
       cert (deleted_at set) is what hides it from the UI default
       view — bindings become inert because the cert filter strips
       them upstream in `/certificates` (deleted_at IS NULL gate
       in `backend/app/routers/anagrafica.py`).

    D. Audit log:
       - one daily_inputs 'update' entry for row 22097 cert re-
         attribution (new_values.kind='cert_reattribution');
       - one certificates 'soft_delete' entry for cert 3 retire
         (new_values.kind='certificate_retire').
       Both use action values from the {insert, update, delete,
       soft_delete, restore, pdf_sign} CHECK set per
       `project_audit_log_action_check`.

Downgrade reverses A + B (restores cert state to pre-retire +
re-attributes row 22097 back to cert 3). Audit log entries are
NOT removed (audit trail preserved).
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0044_retire_ecogras_2025_cert"
down_revision = "0043_byproduct_sale_pdf_ref"
branch_labels = None
depends_on = None


# Business-key targets.
TARGET_CERT_NUMBER = "ES216-20254036"
SELF_DECL_SUPPLIER_CODE = "LE5TON"


def upgrade() -> None:
    # -----------------------------------------------------------------
    # A. Re-attribute 1 LE5TON daily_input row off cert ES216-20254036
    # -----------------------------------------------------------------
    op.execute(
        """
        WITH reattributed AS (
            UPDATE daily_inputs
            SET certificate_id = NULL
            WHERE certificate_id = (
                    SELECT id FROM certificates
                    WHERE cert_number = 'ES216-20254036'
                  )
              AND supplier_id = (
                    SELECT id FROM suppliers WHERE code = 'LE5TON'
                  )
              AND deleted_at IS NULL
            RETURNING id, supplier_id, entry_date, total_input_kg
        )
        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values)
        SELECT 'daily_inputs', id, 'update',
               jsonb_build_object('certificate_id',
                                  (SELECT id FROM certificates
                                   WHERE cert_number = 'ES216-20254036'),
                                  'cert_number', 'ES216-20254036'),
               jsonb_build_object('certificate_id', NULL,
                                  'kind', 'cert_reattribution',
                                  'reason', 'LE5TON self-decl bucket has no '
                                            || 'ISCC cert; aligns with 619 '
                                            || 'sibling rows already NULL',
                                  'migration', '0044_retire_ecogras_2025_cert')
        FROM reattributed;
        """
    )

    # -----------------------------------------------------------------
    # B. Soft-deprecate cert ES216-20254036 (status -> revoked)
    # -----------------------------------------------------------------
    op.execute(
        """
        WITH retired AS (
            UPDATE certificates
            SET deleted_at = NOW(),
                status = 'revoked',
                notes = COALESCE(notes, '')
                    || E'\nRevoked 2026-05-29 (migration 0044): CI ECOGRAS '
                    || 'COLOMBIA SAS confirmed legacy by client 2026-05-26 '
                    || 'sweep; 2025 vintage cert escaped 0039 selector due '
                    || 'to status=active + binding to LE5TON+LITOPLAS (not '
                    || 'to retired CIECOGRAS supplier). AUDIT-MISMATCH '
                    || 'resolved: PDF intestazione CI ECOGRAS, binding '
                    || 'rows preserved for ISCC chain-of-custody audit '
                    || 'trail. Kept (soft-delete) for historical integrity.'
            WHERE cert_number = 'ES216-20254036'
              AND deleted_at IS NULL
            RETURNING id, cert_number
        )
        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values)
        SELECT 'certificates', r.id, 'soft_delete',
               jsonb_build_object('cert_number', r.cert_number,
                                  'deleted_at', NULL,
                                  'status', 'active'),
               jsonb_build_object('cert_number', r.cert_number,
                                  'deleted_at', NOW(),
                                  'status', 'revoked',
                                  'kind', 'certificate_retire',
                                  'reason', 'client-confirmed legacy 2026-05-26 '
                                            || '(missed by 0039 selector)',
                                  'migration', '0044_retire_ecogras_2025_cert')
        FROM retired r;
        """
    )

    # -----------------------------------------------------------------
    # C. Bindings left in place by design (see docstring §C).
    # -----------------------------------------------------------------


def downgrade() -> None:
    # B-reverse: restore cert ES216-20254036 to active
    op.execute(
        """
        UPDATE certificates
        SET deleted_at = NULL,
            status = 'active'
        WHERE cert_number = 'ES216-20254036';
        """
    )

    # A-reverse: re-attribute the LE5TON drift row back to cert 3.
    # Selector matches the original target by supplier + date so the
    # downgrade is portable across environments (no row-id lookup).
    op.execute(
        """
        UPDATE daily_inputs
        SET certificate_id = (
                SELECT id FROM certificates
                WHERE cert_number = 'ES216-20254036'
            )
        WHERE supplier_id = (SELECT id FROM suppliers WHERE code = 'LE5TON')
          AND entry_date  = DATE '2025-05-24'
          AND total_input_kg = 4595.000
          AND certificate_id IS NULL
          AND deleted_at IS NULL;
        """
    )

    # Audit log preserved (no DELETE).
