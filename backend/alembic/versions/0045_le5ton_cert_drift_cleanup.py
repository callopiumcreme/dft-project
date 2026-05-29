"""le5ton_cert_drift_cleanup — null-out the last LE5TON daily_input
row pointing at a cert (LITOPLAS CO222-00000026), aligning with the
canonical self-decl bucket pattern (certificate_id IS NULL).

Context:
    LE5TON (code, supplier_id 7) is the `≤5 TON` self-declaration
    aggregate bucket — Jan-Aug 2025 small-supplier consolidation,
    no single legal entity, no ISCC certificate coverage. The
    canonical pattern across the bucket is `certificate_id IS NULL`.

    Two drift rows survived prior cert-reality migrations:

      - id 22097 (2025-05-24, 4595 kg) → cert ES216-20254036
        (ECOGRAS 2025). Resolved by migration 0044 §A on 2026-05-29.
      - id 21299 (2025-02-12, 17345 kg) → cert CO222-00000026
        (LITOPLAS). Same drift class, not in 0044 scope because the
        cert itself is active and bound to LITOPLAS (legitimate);
        the bug is the row's mis-attribution to a self-decl entity
        that the cert does not cover.

    0045 mirrors 0044 §A on the second drift row so the LE5TON
    bucket reaches a uniform 620/620 `certificate_id IS NULL`
    state and the auditor-facing chain does not show LE5TON as
    covered by any ISCC EU cert (which it never was).

Pre-check ground truth (executed 2026-05-29, head 0044):
    live LE5TON rows with certificate_id IS NOT NULL: 1
      → id 21299, 2025-02-12, supplier_id 7, total_input_kg
        17345.000, certificate_id 1 (CO222-00000026, LITOPLAS,
        ISCC PLUS, active, not soft-deleted).
    live LE5TON rows with certificate_id IS NULL: 620 (canonical).

Migration plan (UPDATEs keyed on business identifiers ONLY — per
`feedback_migration_row_id_portability`):

    A. Re-attribute the 1 LE5TON daily_input live row off
       cert CO222-00000026:
       - certificate_id 1 -> NULL  (self-decl bucket pattern)
       Selector: certificate_id = (SELECT id WHERE cert_number =
                 'CO222-00000026') AND supplier_id = (SELECT id
                 WHERE code = 'LE5TON') AND deleted_at IS NULL.

    B. supplier_certificates bindings: NOT touched. LE5TON is not
       bound to CO222-00000026 in supplier_certificates (only the
       daily_input row had the drift); only LITOPLAS is bound to
       CO222-00000026, which is correct.

    C. Audit log: one daily_inputs 'update' entry, with
       new_values.kind='cert_reattribution' tag per
       `project_audit_log_action_check` (action must come from the
       {insert, update, delete, soft_delete, restore, pdf_sign}
       CHECK set).

Downgrade reverses A by re-attributing the row back to cert
CO222-00000026 using supplier + date + kg as the portable
business-key. Audit log entries are NOT removed.
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0045_le5ton_cert_drift_cleanup"
down_revision = "0044_retire_ecogras_2025_cert"
branch_labels = None
depends_on = None


# Business-key targets.
TARGET_CERT_NUMBER = "CO222-00000026"
SELF_DECL_SUPPLIER_CODE = "LE5TON"


def upgrade() -> None:
    # -----------------------------------------------------------------
    # A. Re-attribute the LE5TON drift row off cert CO222-00000026
    # -----------------------------------------------------------------
    op.execute(
        """
        WITH reattributed AS (
            UPDATE daily_inputs
            SET certificate_id = NULL
            WHERE certificate_id = (
                    SELECT id FROM certificates
                    WHERE cert_number = 'CO222-00000026'
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
                                   WHERE cert_number = 'CO222-00000026'),
                                  'cert_number', 'CO222-00000026'),
               jsonb_build_object('certificate_id', NULL,
                                  'kind', 'cert_reattribution',
                                  'reason', 'LE5TON self-decl bucket has no '
                                            || 'ISCC cert; aligns with 620 '
                                            || 'sibling rows already NULL '
                                            || '(post-0044 head)',
                                  'migration', '0045_le5ton_cert_drift_cleanup')
        FROM reattributed;
        """
    )


def downgrade() -> None:
    # A-reverse: re-attribute the LE5TON drift row back to cert
    # CO222-00000026. Selector uses supplier + date + kg so the
    # downgrade is portable across environments (no row-id lookup).
    op.execute(
        """
        UPDATE daily_inputs
        SET certificate_id = (
                SELECT id FROM certificates
                WHERE cert_number = 'CO222-00000026'
            )
        WHERE supplier_id = (SELECT id FROM suppliers WHERE code = 'LE5TON')
          AND entry_date  = DATE '2025-02-12'
          AND total_input_kg = 17345.000
          AND certificate_id IS NULL
          AND deleted_at IS NULL;
        """
    )

    # Audit log preserved (no DELETE).
