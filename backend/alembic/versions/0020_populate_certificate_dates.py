"""Populate missing certificate issued_at / expires_at

Revision ID: 0020
Revises: 0019
Create Date: 2026-05-22

Backfill ISCC EU certificate dates extracted from filenames in
``DFT_2025/CERTIFICATES`` Drive folder and the RTFO-310825 bundle
under ``03_supplier_evidence/certificates/``.

UPDATEs (4 cert rows missing issued_at/expires_at):
    CO222-00000026 LITOPLAS  → 2024-10-15 / 2025-10-14
    CO222-00000027 ESENTTIA  → 2024-10-17 / 2025-10-16
    PL21990602701  BIOWASTE  → 2024-11-26 / 2025-11-25
    ES216-20254036 CIECOGRAS → 2025-06-20 / 2026-06-19
        (source: CI ECOGRAS COLOMBIA SAS EU-ISCC-Cert filename
        dates "20JUN25-19JUN26"; supplier CIECOGRAS soft-deleted in
        0011 but the certificate itself remains valid and is now
        linked only to LITOPLAS + LE5TON via supplier_certificates)

OUT OF SCOPE / flagged for review (NOT modified by this migration):
    ES216-20268083 — DB seed (0002) number does NOT match Drive
        copy ``SANIMAX DE COLOMBIA SAS EU-ISCC-Cert-ES216-20258083
        02JAN25-01JAN26.pdf`` (5-vs-6 digit diff in 4th position).
        Per ISCC audit safety rule, historical compliance doc IDs
        must NOT be silently rewritten. Decision to fix the number
        or the link belongs to manual audit review.
"""
from __future__ import annotations

from datetime import date

from alembic import op
from sqlalchemy import text

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


UPDATES = [
    # (cert_number, issued_at, expires_at)
    ("CO222-00000026", date(2024, 10, 15), date(2025, 10, 14)),
    ("CO222-00000027", date(2024, 10, 17), date(2025, 10, 16)),
    ("PL21990602701",  date(2024, 11, 26), date(2025, 11, 25)),
    ("ES216-20254036", date(2025, 6, 20),  date(2026, 6, 19)),
]


def upgrade() -> None:
    conn = op.get_bind()
    for cert_number, issued, expires in UPDATES:
        result = conn.execute(
            text(
                """
                UPDATE certificates
                SET issued_at = :issued,
                    expires_at = :expires,
                    updated_at = NOW()
                WHERE cert_number = :cert_number
                  AND deleted_at IS NULL
                """
            ),
            {"issued": issued, "expires": expires, "cert_number": cert_number},
        )
        if result.rowcount != 1:
            raise RuntimeError(
                f"UPDATE {cert_number} affected {result.rowcount} rows, expected 1"
            )


def downgrade() -> None:
    conn = op.get_bind()
    for cert_number, *_ in UPDATES:
        conn.execute(
            text(
                """
                UPDATE certificates
                SET issued_at = NULL,
                    expires_at = NULL,
                    updated_at = NOW()
                WHERE cert_number = :cert_number
                """
            ),
            {"cert_number": cert_number},
        )
