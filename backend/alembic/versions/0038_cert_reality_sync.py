"""cert_reality_sync — fix cert typos, re-bind cert 4 to SANIMAX,
restore wrongly soft-deleted suppliers, re-attribute mis-attributed
daily_inputs, add 3 missing certs (ECOGRAS 2024, ECODIESEL, OISTEBIO own).

Story:
    Drive `gdrive:DFT_2025/RTFO-310825/03_supplier_evidence/certificates/`
    holds the authoritative ISCC cert PDFs for the DEL-CRW-2025-2 Q3 2025
    audit bundle. Local DB drift discovered 2026-05-26:

      1. Cert id 4 stored as `ES216-20268083` — actual cert number per
         PDF is `ES216-20258083` (off-by-one digit in pos 8). The cert
         belongs to SANIMAX DE COLOMBIA SAS (1514 daily_inputs against
         this cert are SANIMAX). Current supplier_certificates bindings
         wrongly point to ESENTTIA + LITOPLAS, who have their own certs
         (ids 1 + 2) and only 38 mis-attributed daily_inputs against
         this cert.

      2. Cert id 6 stored as `PL21990602701` — actual cert number per
         PDF and ISCC public registry is `PL219-90602701` (missing
         hyphen after country prefix). 1351 daily_inputs BIOWASTE.

      3. Suppliers SANIMAX (id 2), CIECOGRAS (id 4), ECODIESEL (id 6)
         were soft-deleted on 2026-05-20 — incorrect, they have
         active daily_inputs in Q3 2025.

      4. ECOGRAS 2024 vintage cert `ES216-20244036`, ECODIESEL cert
         `US201-100862024`, OisteBio own cert `LV227-00000597` are
         present on Drive but absent from DB.

Migration plan (all UPDATEs keyed on business identifiers, NOT
auto-increment ids — per `feedback_migration_row_id_portability`):

    A. Restore 3 wrongly soft-deleted suppliers (SANIMAX, CIECOGRAS,
       ECODIESEL) — `deleted_at = NULL`, `active = TRUE`.

    B. Fix cert typos:
       - `ES216-20268083` → `ES216-20258083` (note: SANIMAX cert)
       - `PL21990602701`  → `PL219-90602701` (note: BIOWASTE canonical)

    C. Re-bind cert `ES216-20258083`:
       - DELETE bindings to ESENTTIA + LITOPLAS (wrong attribution)
       - INSERT binding to SANIMAX (correct supplier)

    D. Re-attribute daily_inputs against `ES216-20258083`:
       - 20 ESENTTIA rows → cert `CO222-00000027` (ESENTTIA proper)
       - 18 LITOPLAS rows → cert `CO222-00000026` (LITOPLAS proper)
       - 7  CIECOGRAS rows → cert `ES216-20254036` (ECOGRAS 2025)
       (All have proper certs already in DB; the rows were mis-keyed
       at ingestion time before migration 0010 cert-correction; 0010
       fixed only the headline LITOPLAS↔ECOGRAS swap, missed these.)

    E. Insert 3 new certificates with pdf_ref:
       - `ES216-20244036` (ECOGRAS 2024) → bound to CIECOGRAS
       - `US201-100862024` (ECODIESEL) → bound to ECODIESEL
       - `LV227-00000597` (OISTEBIO own) → no supplier binding (own)

    F. UPDATE pdf_ref for 5 certs whose PDFs were just synced to
       `data/certificates/supplier-q3/`:
       - `ES216-20258083` (SANIMAX)
       - `PL219-90602701` (BIOWASTE)
       - `US201-138762024` (KALTIRE 2024)
       - `US201-158772024` (EFFICIEN 2024)
       - `US201-120372024` (BOLDER 2024)

    G. Audit log: every cert_number rename, every supplier restore,
       every binding change, every daily_inputs re-attribution.

Downgrade reverses A-F (drops new certs, restores typos, re-soft-
deletes suppliers, restores wrong bindings, reverts daily_inputs).
G audit_log entries are NOT removed (audit trail preserved).
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0038_cert_reality_sync"
down_revision = "0037_audit_log_pdf_sign_action"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------
    # PRE. Ensure `certificates.pdf_ref` exists.
    #
    # This column is referenced by sections E + F below (INSERT ...
    # pdf_ref ... and UPDATE ... SET pdf_ref ...), but no earlier
    # migration on disk explicitly adds it — it was added to LOCAL by
    # an out-of-band hotfix and never captured in alembic. On a fresh
    # environment (prod 2026-05-27 deploy) the chain reaches 0038 with
    # the column missing and INSERT raises UndefinedColumnError.
    #
    # IF NOT EXISTS keeps the patch idempotent: harmless on LOCAL where
    # the column already exists, additive on prod where it does not.
    # -----------------------------------------------------------------
    op.execute(
        "ALTER TABLE certificates "
        "ADD COLUMN IF NOT EXISTS pdf_ref text;"
    )

    # -----------------------------------------------------------------
    # A. Restore wrongly soft-deleted suppliers
    # -----------------------------------------------------------------
    op.execute(
        """
        WITH restored AS (
            UPDATE suppliers
            SET deleted_at = NULL,
                active = TRUE,
                notes = COALESCE(notes, '')
                    || E'\nRestored 2026-05-26 (migration 0038): supplier '
                    || 'wrongly soft-deleted 2026-05-20 despite active '
                    || 'daily_inputs in Q3 2025.'
            WHERE code IN ('SANIMAX', 'CIECOGRAS', 'ECODIESEL')
              AND deleted_at IS NOT NULL
            RETURNING id, code, name
        )
        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values)
        SELECT 'suppliers', id, 'restore',
               jsonb_build_object('deleted_at', '2026-05-20', 'active', false),
               jsonb_build_object('deleted_at', NULL, 'active', true,
                                  'reason', 'Q3 2025 daily_inputs reattribution')
        FROM restored;
        """
    )

    # -----------------------------------------------------------------
    # B. Fix cert_number typos (preserve original in notes + audit_log)
    # -----------------------------------------------------------------
    # B1: ES216-20268083 → ES216-20258083 (SANIMAX cert)
    op.execute(
        """
        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values)
        SELECT 'certificates', id, 'update',
               jsonb_build_object('cert_number', 'ES216-20268083'),
               jsonb_build_object('cert_number', 'ES216-20258083',
                                  'reason', 'typo fix: pos 8 6→5; PDF= SANIMAX ES216-20258083')
        FROM certificates WHERE cert_number = 'ES216-20268083';
        """
    )
    op.execute(
        """
        UPDATE certificates
        SET cert_number = 'ES216-20258083',
            notes = COALESCE(notes, '')
                || E'\nMigration 0038 (2026-05-26): cert_number corrected from '
                || 'ES216-20268083 → ES216-20258083 (typo, pos-8 digit 6→5). '
                || 'Authoritative PDF: SANIMAX DE COLOMBIA SAS EU-ISCC-Cert-'
                || 'ES216-20258083 02JAN25 - 01JAN26.'
        WHERE cert_number = 'ES216-20268083';
        """
    )

    # B2: PL21990602701 → PL219-90602701 (BIOWASTE canonical)
    op.execute(
        """
        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values)
        SELECT 'certificates', id, 'update',
               jsonb_build_object('cert_number', 'PL21990602701'),
               jsonb_build_object('cert_number', 'PL219-90602701',
                                  'reason', 'canonical format: insert missing hyphen')
        FROM certificates WHERE cert_number = 'PL21990602701';
        """
    )
    op.execute(
        """
        UPDATE certificates
        SET cert_number = 'PL219-90602701',
            notes = COALESCE(notes, '')
                || E'\nMigration 0038 (2026-05-26): cert_number normalised from '
                || 'PL21990602701 → PL219-90602701 (canonical ISCC format with '
                || 'hyphen after country prefix). Authoritative PDF: BIOWASTE '
                || 'COLOMBIA SAS EU-ISCC-Cert-PL219-90602701 26NOV24 - 25NOV25.'
        WHERE cert_number = 'PL21990602701';
        """
    )

    # -----------------------------------------------------------------
    # C. Re-bind cert ES216-20258083 (SANIMAX)
    # -----------------------------------------------------------------
    # C1: Audit-log the wrong bindings before deletion
    op.execute(
        """
        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values)
        SELECT 'supplier_certificates', c.id, 'delete',
               jsonb_build_object('supplier_id', sc.supplier_id,
                                  'supplier_code', s.code,
                                  'certificate_id', c.id,
                                  'cert_number', c.cert_number),
               jsonb_build_object('reason', 'wrong binding: cert is SANIMAX, not '
                                  || s.code)
        FROM certificates c
        JOIN supplier_certificates sc ON sc.certificate_id = c.id
        JOIN suppliers s ON s.id = sc.supplier_id
        WHERE c.cert_number = 'ES216-20258083'
          AND s.code IN ('ESENTTIA', 'LITOPLAS');
        """
    )

    # C2: Delete wrong bindings (composite-PK; supplier_certificates has
    # no deleted_at column — true delete + audit_log trail)
    op.execute(
        """
        DELETE FROM supplier_certificates
        WHERE certificate_id = (
            SELECT id FROM certificates WHERE cert_number = 'ES216-20258083'
        )
        AND supplier_id IN (
            SELECT id FROM suppliers WHERE code IN ('ESENTTIA', 'LITOPLAS')
        );
        """
    )

    # C3: Insert correct binding SANIMAX → ES216-20258083
    op.execute(
        """
        WITH inserted AS (
            INSERT INTO supplier_certificates (supplier_id, certificate_id)
            SELECT s.id, c.id
            FROM suppliers s
            CROSS JOIN certificates c
            WHERE s.code = 'SANIMAX'
              AND c.cert_number = 'ES216-20258083'
            ON CONFLICT DO NOTHING
            RETURNING supplier_id, certificate_id
        )
        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values)
        SELECT 'supplier_certificates', certificate_id, 'insert',
               NULL,
               jsonb_build_object('supplier_id', supplier_id,
                                  'supplier_code', 'SANIMAX',
                                  'certificate_id', certificate_id,
                                  'cert_number', 'ES216-20258083',
                                  'reason', 'correct binding per PDF authority')
        FROM inserted;
        """
    )

    # -----------------------------------------------------------------
    # D. Re-attribute daily_inputs (mis-keyed at ingest, pre-0010)
    # -----------------------------------------------------------------
    # D1: Audit-log all re-attributions in one shot
    op.execute(
        """
        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values)
        SELECT 'daily_inputs', di.id, 'update',
               jsonb_build_object('certificate_id', di.certificate_id,
                                  'cert_number', 'ES216-20258083',
                                  'supplier', s.code),
               jsonb_build_object('certificate_id',
                                  CASE s.code
                                      WHEN 'ESENTTIA' THEN
                                          (SELECT id FROM certificates
                                           WHERE cert_number='CO222-00000027')
                                      WHEN 'LITOPLAS' THEN
                                          (SELECT id FROM certificates
                                           WHERE cert_number='CO222-00000026')
                                      WHEN 'CIECOGRAS' THEN
                                          (SELECT id FROM certificates
                                           WHERE cert_number='ES216-20254036')
                                  END,
                                  'reason',
                                  'cert ES216-20258083 belongs to SANIMAX; '
                                  || s.code || ' has own cert')
        FROM daily_inputs di
        JOIN suppliers s ON s.id = di.supplier_id
        WHERE di.certificate_id = (
            SELECT id FROM certificates WHERE cert_number = 'ES216-20258083'
        )
        AND s.code IN ('ESENTTIA', 'LITOPLAS', 'CIECOGRAS');
        """
    )

    # D2: UPDATE the rows themselves
    op.execute(
        """
        UPDATE daily_inputs di
        SET certificate_id = CASE s.code
            WHEN 'ESENTTIA' THEN
                (SELECT id FROM certificates WHERE cert_number = 'CO222-00000027')
            WHEN 'LITOPLAS' THEN
                (SELECT id FROM certificates WHERE cert_number = 'CO222-00000026')
            WHEN 'CIECOGRAS' THEN
                (SELECT id FROM certificates WHERE cert_number = 'ES216-20254036')
        END
        FROM suppliers s
        WHERE s.id = di.supplier_id
          AND di.certificate_id = (
              SELECT id FROM certificates WHERE cert_number = 'ES216-20258083'
          )
          AND s.code IN ('ESENTTIA', 'LITOPLAS', 'CIECOGRAS');
        """
    )

    # -----------------------------------------------------------------
    # E. Insert 3 new certs + bindings
    # -----------------------------------------------------------------
    # E1: ECOGRAS 2024 (ES216-20244036) → CIECOGRAS
    op.execute(
        """
        INSERT INTO certificates (cert_number, scheme, status, issued_at,
                                  expires_at, pdf_ref, notes)
        VALUES ('ES216-20244036', 'ISCC EU', 'expired',
                '2024-06-20', '2025-06-19',
                'supplier-q3/ES216-20244036_ECOGRAS_2024.pdf',
                'CI ECOGRAS COLOMBIA SAS — 2024 vintage, expired 2025-06-19; '
                || 'kept for historical chain integrity. Added by migration 0038 '
                || '(2026-05-26).')
        ON CONFLICT (cert_number) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO supplier_certificates (supplier_id, certificate_id)
        SELECT s.id, c.id
        FROM suppliers s CROSS JOIN certificates c
        WHERE s.code = 'CIECOGRAS' AND c.cert_number = 'ES216-20244036'
        ON CONFLICT DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values)
        SELECT 'certificates', id, 'insert', NULL,
               jsonb_build_object('cert_number', cert_number, 'scheme', scheme,
                                  'reason', 'ECOGRAS 2024 vintage from Drive')
        FROM certificates WHERE cert_number = 'ES216-20244036';
        """
    )

    # E2: ECODIESEL (US201-100862024) → ECODIESEL supplier
    op.execute(
        """
        INSERT INTO certificates (cert_number, scheme, status, issued_at,
                                  expires_at, pdf_ref, notes)
        VALUES ('US201-100862024', 'ISCC EU', 'expired',
                '2024-07-24', '2025-07-23',
                'supplier-q3/US201-100862024_ECODIESEL.pdf',
                'ECODIESEL COLOMBIA SA — 2024 vintage, expired 2025-07-23. '
                || 'Added by migration 0038 (2026-05-26).')
        ON CONFLICT (cert_number) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO supplier_certificates (supplier_id, certificate_id)
        SELECT s.id, c.id
        FROM suppliers s CROSS JOIN certificates c
        WHERE s.code = 'ECODIESEL' AND c.cert_number = 'US201-100862024'
        ON CONFLICT DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values)
        SELECT 'certificates', id, 'insert', NULL,
               jsonb_build_object('cert_number', cert_number, 'scheme', scheme,
                                  'reason', 'ECODIESEL cert from Drive')
        FROM certificates WHERE cert_number = 'US201-100862024';
        """
    )

    # E3: OisteBio own cert (LV227-00000597) — no supplier binding
    op.execute(
        """
        INSERT INTO certificates (cert_number, scheme, status, pdf_ref, notes)
        VALUES ('LV227-00000597', 'ISCC EU', 'active',
                'oistebio/LV227-00000597_OISTEBIO.pdf',
                'OisteBio Swiss GmbH own ISCC EU certificate — RTFO compliance '
                || 'cert covering the processing-unit chain-of-custody for the '
                || 'DEV-P100 product. Added by migration 0038 (2026-05-26).')
        ON CONFLICT (cert_number) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values)
        SELECT 'certificates', id, 'insert', NULL,
               jsonb_build_object('cert_number', cert_number, 'scheme', scheme,
                                  'reason', 'OisteBio own ISCC EU cert from Drive')
        FROM certificates WHERE cert_number = 'LV227-00000597';
        """
    )

    # -----------------------------------------------------------------
    # F. UPDATE pdf_ref for newly-synced PDFs
    # -----------------------------------------------------------------
    op.execute(
        """
        UPDATE certificates SET
            pdf_ref = 'supplier-q3/ES216-20258083_SANIMAX.pdf'
        WHERE cert_number = 'ES216-20258083' AND pdf_ref IS NULL;
        """
    )
    op.execute(
        """
        UPDATE certificates SET
            pdf_ref = 'supplier-q3/PL219-90602701_BIOWASTE.pdf'
        WHERE cert_number = 'PL219-90602701' AND pdf_ref IS NULL;
        """
    )
    op.execute(
        """
        UPDATE certificates SET
            pdf_ref = 'supplier-q3/US201-138762024_KALTIRE.pdf'
        WHERE cert_number = 'US201-138762024' AND pdf_ref IS NULL;
        """
    )
    op.execute(
        """
        UPDATE certificates SET
            pdf_ref = 'supplier-q3/US201-158772024_EFFICIEN.pdf'
        WHERE cert_number = 'US201-158772024' AND pdf_ref IS NULL;
        """
    )
    op.execute(
        """
        UPDATE certificates SET
            pdf_ref = 'supplier-q3/US201-120372024_BOLDER.pdf'
        WHERE cert_number = 'US201-120372024' AND pdf_ref IS NULL;
        """
    )

    op.execute(
        """
        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values)
        SELECT 'certificates', id, 'update',
               jsonb_build_object('pdf_ref', NULL),
               jsonb_build_object('pdf_ref', pdf_ref,
                                  'reason', 'PDF synced from Drive 0038')
        FROM certificates
        WHERE cert_number IN ('ES216-20258083', 'PL219-90602701',
                              'US201-138762024', 'US201-158772024',
                              'US201-120372024');
        """
    )


def downgrade() -> None:
    # F-reverse: clear pdf_ref for 5 newly-linked
    op.execute(
        """
        UPDATE certificates SET pdf_ref = NULL
        WHERE cert_number IN ('ES216-20258083', 'PL219-90602701',
                              'US201-138762024', 'US201-158772024',
                              'US201-120372024');
        """
    )

    # E-reverse: drop 3 new certs (bindings cascade)
    op.execute(
        """
        DELETE FROM certificates
        WHERE cert_number IN ('ES216-20244036', 'US201-100862024',
                              'LV227-00000597');
        """
    )

    # D-reverse: re-attribute daily_inputs back to ES216-20258083
    op.execute(
        """
        UPDATE daily_inputs di
        SET certificate_id = (
            SELECT id FROM certificates WHERE cert_number = 'ES216-20258083'
        )
        FROM suppliers s
        WHERE s.id = di.supplier_id
          AND s.code IN ('ESENTTIA', 'LITOPLAS', 'CIECOGRAS')
          AND di.certificate_id IN (
              SELECT id FROM certificates
              WHERE cert_number IN ('CO222-00000027', 'CO222-00000026',
                                    'ES216-20254036')
          )
          -- guard: only revert rows whose audit_log shows they were re-attributed
          AND EXISTS (
              SELECT 1 FROM audit_log al
              WHERE al.table_name = 'daily_inputs'
                AND al.record_id = di.id
                AND al.action = 'update'
                AND al.old_values->>'cert_number' = 'ES216-20258083'
          );
        """
    )

    # C-reverse: drop SANIMAX binding, restore ESENTTIA + LITOPLAS
    op.execute(
        """
        DELETE FROM supplier_certificates
        WHERE certificate_id = (
            SELECT id FROM certificates WHERE cert_number = 'ES216-20258083'
        ) AND supplier_id = (
            SELECT id FROM suppliers WHERE code = 'SANIMAX'
        );
        """
    )
    op.execute(
        """
        INSERT INTO supplier_certificates (supplier_id, certificate_id)
        SELECT s.id, c.id
        FROM suppliers s CROSS JOIN certificates c
        WHERE s.code IN ('ESENTTIA', 'LITOPLAS')
          AND c.cert_number = 'ES216-20258083'
        ON CONFLICT DO NOTHING;
        """
    )

    # B-reverse: restore cert_number typos
    op.execute(
        """
        UPDATE certificates SET cert_number = 'ES216-20268083'
        WHERE cert_number = 'ES216-20258083';
        """
    )
    op.execute(
        """
        UPDATE certificates SET cert_number = 'PL21990602701'
        WHERE cert_number = 'PL219-90602701';
        """
    )

    # A-reverse: re-soft-delete restored suppliers
    op.execute(
        """
        UPDATE suppliers
        SET deleted_at = NOW(), active = FALSE
        WHERE code IN ('SANIMAX', 'CIECOGRAS', 'ECODIESEL');
        """
    )

    # G: audit_log entries left in place — preserve audit history
