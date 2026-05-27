"""d17_cosmetic_fixture_cleanup — flip stale active flags on test
fixtures that were soft-deleted but kept `active=TRUE` / `status='active'`.

Context:
    DFT-C1 Auto-Audit Round-6/Round-7 flagged D17 as a non-blocking
    cosmetic anomaly: 5 rows (2 suppliers, 3 certificates) had
    `deleted_at IS NOT NULL` AND a "live" flag still set.

    Affected rows (business keys, NOT row ids — see
    `feedback_migration_row_id_portability`):

      suppliers WHERE deleted_at IS NOT NULL
                  AND active = TRUE
                  AND code LIKE 'E2E-%'
        → 2 E2E test supplier fixtures (created by e2e harness).

      certificates WHERE deleted_at IS NOT NULL
                     AND status = 'active'
                     AND (cert_number LIKE 'SMOKE-CERT-%'
                          OR cert_number LIKE 'E2E-CERT-%'
                          OR cert_number = '__WATCHDOG_DRIFT_TEST__')
        → 3 smoke/watchdog test certificate fixtures.

    These rows are invisible to soft-delete-aware queries, so the
    anomaly never reached prod UI or the RTFO bundle. The fix is
    cosmetic: align the flag with the soft-delete state so the audit
    checks report all-green.

    No production data is touched. No hard delete.

Migration plan:

    A. UPDATE suppliers SET active = FALSE
       WHERE soft-deleted E2E test fixtures (business-key match).

    B. UPDATE certificates SET status = 'revoked'
       WHERE soft-deleted SMOKE/E2E/WATCHDOG test fixtures
       (business-key match). 'revoked' is the allowed CHECK value
       semantically closest to "retired-test-fixture"; the CHECK
       constraint admits {active, expired, revoked, placeholder}.

    C. Audit log meta entry — one row per table documenting the
       cosmetic cleanup, with `action='update'` (audit_log CHECK
       rejects custom actions — see `project_audit_log_action_check`).

Downgrade:
    Reverses A and B by restoring the original "live" flag values
    on the same business-key matches. Idempotent — re-runnable
    without raising. Audit log entries preserved (no DELETE).
"""
from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "0042_d17_cosmetic_cleanup"
down_revision = "0041_byproduct_dev_p200_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------
    # A. suppliers — flip active=TRUE → FALSE on soft-deleted E2E
    # test fixtures.
    # -----------------------------------------------------------------
    op.execute(
        """
        UPDATE suppliers
           SET active = FALSE,
               updated_at = NOW()
         WHERE deleted_at IS NOT NULL
           AND active = TRUE
           AND code LIKE 'E2E-%';
        """
    )

    # -----------------------------------------------------------------
    # B. certificates — flip status='active' → 'revoked' on
    # soft-deleted SMOKE/E2E/WATCHDOG test fixtures.
    # -----------------------------------------------------------------
    op.execute(
        """
        UPDATE certificates
           SET status = 'revoked',
               updated_at = NOW()
         WHERE deleted_at IS NOT NULL
           AND status = 'active'
           AND (cert_number LIKE 'SMOKE-CERT-%'
                OR cert_number LIKE 'E2E-CERT-%'
                OR cert_number = '__WATCHDOG_DRIFT_TEST__');
        """
    )

    # -----------------------------------------------------------------
    # C. Audit log meta entries — one per table.
    # record_id = 0 marker (whole-table cosmetic cleanup, no specific
    # canonical row). action='update' because audit_log CHECK rejects
    # custom labels (see memory project_audit_log_action_check).
    # -----------------------------------------------------------------
    op.execute(
        """
        INSERT INTO audit_log (table_name, record_id, action,
                               old_values, new_values)
        VALUES (
            'suppliers',
            0,
            'update',
            jsonb_build_object('active', true),
            jsonb_build_object(
                'active', false,
                'kind', 'd17_cosmetic_fixture_cleanup',
                'reason',
                  'Round-7 D17 — flip stale active=TRUE on '
                  'soft-deleted E2E test supplier fixtures',
                'migration', '0042_d17_cosmetic_cleanup',
                'match', 'deleted_at IS NOT NULL AND active=TRUE '
                         'AND code LIKE E2E-%'
            )
        );
        """
    )
    op.execute(
        """
        INSERT INTO audit_log (table_name, record_id, action,
                               old_values, new_values)
        VALUES (
            'certificates',
            0,
            'update',
            jsonb_build_object('status', 'active'),
            jsonb_build_object(
                'status', 'revoked',
                'kind', 'd17_cosmetic_fixture_cleanup',
                'reason',
                  'Round-7 D17 — flip stale status=active on '
                  'soft-deleted SMOKE/E2E/WATCHDOG test cert fixtures',
                'migration', '0042_d17_cosmetic_cleanup',
                'match', 'deleted_at IS NOT NULL AND status=active '
                         'AND cert_number LIKE (SMOKE-CERT-%, '
                         'E2E-CERT-%, __WATCHDOG_DRIFT_TEST__)'
            )
        );
        """
    )


def downgrade() -> None:
    # Reverse A — restore active=TRUE on the same business-key match.
    op.execute(
        """
        UPDATE suppliers
           SET active = TRUE,
               updated_at = NOW()
         WHERE deleted_at IS NOT NULL
           AND active = FALSE
           AND code LIKE 'E2E-%';
        """
    )

    # Reverse B — restore status='active' on the same business-key
    # match.
    op.execute(
        """
        UPDATE certificates
           SET status = 'active',
               updated_at = NOW()
         WHERE deleted_at IS NOT NULL
           AND status = 'revoked'
           AND (cert_number LIKE 'SMOKE-CERT-%'
                OR cert_number LIKE 'E2E-CERT-%'
                OR cert_number = '__WATCHDOG_DRIFT_TEST__');
        """
    )

    # Audit log meta entries preserved (no DELETE).
