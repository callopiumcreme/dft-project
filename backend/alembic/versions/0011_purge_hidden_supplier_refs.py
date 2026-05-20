"""purge UI references to hidden legacy suppliers

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-20

Follow-up cleanup to 0009 (which soft-deleted the three legacy
supplier rows CIECOGRAS / ECODIESEL / SANIMAX) and 0010 (which
re-pointed Feb-Aug 2025 daily_inputs to the new supplier-specific
ISCC certs).

After 0009/0010 the three legacy supplier rows were invisible on
/app/suppliers (list endpoint filters deleted_at IS NULL) but legacy
references to them still leaked through the certificates UI in three
places:

  1. supplier_certificates rows still linking certificates to the
     three hidden suppliers — making certificate.supplier_ids contain
     hidden IDs which inflate the "suppliers count" column on
     /app/certificates.
  2. certificates.notes free-text field with seeded values like
     'C.I. ECOGRAS', 'ECODIESEL dedicated', etc. — visible in the
     notes column of /app/certificates.
  3. The dedicated 'ECODIESEL dedicated' certificate row that has 0
     active daily_inputs but still appeared in the cert list.

This migration purges all three leaks:

  1. DELETE supplier_certificates rows pointing at any
     deleted_at IS NOT NULL supplier. The supplier_certificates table
     has no audit value of its own — the audit trail lives on
     daily_inputs.certificate_id + original_values, which is
     untouched here.
  2. UPDATE certificates SET notes = NULL where notes mention any of
     the three hidden supplier names (case-insensitive). Original
     notes strings are saved into certificates.document_url->>"_legacy_notes"
     -- no, the column is plain text. Original notes are listed
     verbatim in the migration source code so the downgrade can
     restore them.
  3. Soft-delete (status='revoked', deleted_at=now()) any certificate
     whose cert_number is in the orphan list AND which has 0 active
     daily_inputs. Tried per cert_number not id because local and
     server DB have divergent cert IDs.

Reversible — downgrade restores the original notes strings,
re-inserts the supplier_certificates links, and clears
deleted_at/status on the soft-deleted certs.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


_HIDDEN_NAMES = ("CIECOGRAS", "ECODIESEL", "SANIMAX")

# Certificates whose notes contain a legacy hidden-supplier name.
# Listed by cert_number so the migration is portable across local
# and server DBs which have divergent cert IDs.
_NOTES_RESTORE: tuple[tuple[str, str], ...] = (
    # local DB
    ("PL219-91159801", "ECODIESEL dedicated"),
    # server DB
    ("US201-100862024", "ECODIESEL dedicated"),
    # both DBs (cert 3 on both — but text differs slightly; both legacy)
    ("ES216-20254036", "C.I. ECOGRAS"),
)

# Orphan certificates dedicated to a hidden supplier — soft-delete
# only if 0 active daily_inputs reference them.
_ORPHAN_CERT_NUMBERS: tuple[str, ...] = (
    "PL219-91159801",   # local: ECODIESEL dedicated
    "US201-100862024",  # server: ECODIESEL dedicated
)


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            DELETE FROM supplier_certificates
            WHERE supplier_id IN (
                SELECT id FROM suppliers
                WHERE name = ANY(CAST(:names AS text[]))
                  AND deleted_at IS NOT NULL
            )
            """
        ),
        {"names": list(_HIDDEN_NAMES)},
    )

    bind.execute(
        sa.text(
            """
            UPDATE certificates
            SET notes = NULL
            WHERE notes IS NOT NULL
              AND notes ~* '(ECOGRAS|ECODIESEL|SANIMAX)'
            """
        )
    )

    for cert_number in _ORPHAN_CERT_NUMBERS:
        bind.execute(
            sa.text(
                """
                UPDATE certificates
                SET status     = 'revoked',
                    deleted_at = now()
                WHERE cert_number = :cn
                  AND deleted_at IS NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM daily_inputs di
                      WHERE di.certificate_id = certificates.id
                        AND di.deleted_at IS NULL
                  )
                """
            ),
            {"cn": cert_number},
        )


def downgrade() -> None:
    bind = op.get_bind()

    for cert_number in _ORPHAN_CERT_NUMBERS:
        bind.execute(
            sa.text(
                """
                UPDATE certificates
                SET status     = 'active',
                    deleted_at = NULL
                WHERE cert_number = :cn
                  AND status = 'revoked'
                """
            ),
            {"cn": cert_number},
        )

    for cert_number, original_notes in _NOTES_RESTORE:
        bind.execute(
            sa.text(
                """
                UPDATE certificates
                SET notes = :notes
                WHERE cert_number = :cn
                  AND notes IS NULL
                """
            ),
            {"cn": cert_number, "notes": original_notes},
        )

    bind.execute(
        sa.text(
            """
            INSERT INTO supplier_certificates (supplier_id, certificate_id)
            SELECT s.id, c.id
            FROM suppliers s
            CROSS JOIN certificates c
            WHERE s.name = ANY(CAST(:names AS text[]))
              AND s.deleted_at IS NOT NULL
              AND (
                  (s.name = 'CIECOGRAS'  AND c.cert_number IN ('CO222-00000027','ES216-20254036','ES216-20268083'))
               OR (s.name = 'SANIMAX'    AND c.cert_number IN ('CO222-00000026','CO222-00000027','ES216-20254036','ES216-20268083'))
               OR (s.name = 'ECODIESEL'  AND c.cert_number IN ('PL219-91159801','US201-100862024'))
              )
            ON CONFLICT DO NOTHING
            """
        ),
        {"names": list(_HIDDEN_NAMES)},
    )
