"""ISCC PoS cert correction for the 4 Feb-2025 ELT suppliers

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-20

Follow-up to migration 0008 (Feb 2025 supplier rename). The four new
ELT tyre suppliers (PYRCOM SAS, KAL TIRE, EFFICIEN TECHNOLOGY, BOLDER
INDUSTRIES) inherited the certificate_id of the old suppliers on every
re-pointed daily_inputs row, because their own ISCC PoS numbers were
not yet known. The client has now provided seven ISCC certificates
covering all entry dates from 2025-02-01 through 2025-08-31:

    PYRCOM SAS           ES216-20249051  17.10.2024 - 16.10.2025
    KAL TIRE             US201-138762024 18.05.2024 - 17.05.2025
    KAL TIRE             US201-138762025 18.05.2025 - 17.05.2026
    EFFICIEN TECHNOLOGY  US201-158772024 26.01.2024 - 25.01.2025
    EFFICIEN TECHNOLOGY  US201-158772025 26.01.2025 - 25.01.2026
    BOLDER INDUSTRIES    US201-120372024 04.04.2024 - 03.04.2025
    BOLDER INDUSTRIES    US201-120372025 04.04.2025 - 03.04.2026

Coverage was verified prior to applying this migration: every
daily_inputs row for the four suppliers falls inside exactly one cert
validity window (0 uncovered rows across 851 daily entries).

PYRCOM caveat (flagged 2026-05-19, unresolved): the PYRCOM ISCC PLUS
cert Annex I declares feedstock = "Mixed plastic waste", whereas the
Girardot project operates on ELT (end-of-life tyres). Client direction
(2026-05-20) is to register the cert as-is and rectify post-hoc if an
ISCC auditor flags the mismatch. The mismatch is recorded in
certificates.notes and in the per-row rectification_reason for audit
traceability.

Audit columns from migration 0006 are used to preserve the original
(inherited) certificate_id in original_values, so the rectification is
reversible and traceable for the ISCC EU audit trail.

Mass-balance MVs aggregate by day, not by certificate — cert
re-pointing changes no totals, so no MV refresh is required.
"""
from __future__ import annotations

from datetime import date

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


# (supplier_name, cert_number, issued_at, expires_at, scheme, notes)
_CERTS: tuple[tuple[str, str, date, date, str, str | None], ...] = (
    (
        "PYRCOM SAS",
        "ES216-20249051",
        date(2024, 10, 17),
        date(2025, 10, 16),
        "ISCC PLUS",
        (
            "Feedstock mismatch flagged 2026-05-19: ISCC PLUS Annex I "
            "declares input = 'Mixed plastic waste', output = Pyrolysis "
            "Oil + Coal. Girardot project operational feedstock = ELT "
            "(end-of-life tyres). Client directive 2026-05-20: register "
            "as-is, rectify post-hoc if ISCC auditor flags."
        ),
    ),
    ("KAL TIRE", "US201-138762024", date(2024, 5, 18), date(2025, 5, 17), "ISCC EU", None),
    ("KAL TIRE", "US201-138762025", date(2025, 5, 18), date(2026, 5, 17), "ISCC EU", None),
    ("EFFICIEN TECHNOLOGY", "US201-158772024", date(2024, 1, 26), date(2025, 1, 25), "ISCC EU", None),
    ("EFFICIEN TECHNOLOGY", "US201-158772025", date(2025, 1, 26), date(2026, 1, 25), "ISCC EU", None),
    ("BOLDER INDUSTRIES", "US201-120372024", date(2024, 4, 4), date(2025, 4, 3), "ISCC EU", None),
    ("BOLDER INDUSTRIES", "US201-120372025", date(2025, 4, 4), date(2026, 4, 3), "ISCC EU", None),
)

_REPOINT_CUTOVER = "2025-02-01"

_RECT_REASON_TPL = (
    "ISCC PoS cert correction (client directive 2026-05-20): "
    "supplier {supplier} re-pointed to cert {cert} "
    "(valid {issued} -> {expires}). Replaces inherited cert from "
    "pre-rename supplier."
)

_PYRCOM_FEEDSTOCK_SUFFIX = (
    " WARNING: PYRCOM cert annex declares 'Mixed plastic waste' "
    "feedstock; project operational feedstock = ELT. Pending cert "
    "annex correction."
)


def upgrade() -> None:
    bind = op.get_bind()

    cert_ids: dict[str, int] = {}
    for supplier_name, cert_number, issued, expires, scheme, notes in _CERTS:
        cert_id = bind.execute(
            sa.text(
                """
                INSERT INTO certificates
                    (cert_number, scheme, status, issued_at, expires_at,
                     is_placeholder, notes)
                VALUES
                    (:cert_number, :scheme, 'active',
                     CAST(:issued AS date), CAST(:expires AS date),
                     false, :notes)
                RETURNING id
                """
            ),
            {
                "cert_number": cert_number,
                "scheme": scheme,
                "issued": issued,
                "expires": expires,
                "notes": notes,
            },
        ).scalar_one()
        cert_ids[cert_number] = cert_id

        supplier_id = bind.execute(
            sa.text(
                "SELECT id FROM suppliers WHERE name = :n AND deleted_at IS NULL"
            ),
            {"n": supplier_name},
        ).scalar_one()

        bind.execute(
            sa.text(
                """
                INSERT INTO supplier_certificates (supplier_id, certificate_id)
                VALUES (:s, :c)
                ON CONFLICT DO NOTHING
                """
            ),
            {"s": supplier_id, "c": cert_id},
        )

    for supplier_name, cert_number, issued, expires, _scheme, _notes in _CERTS:
        cert_id = cert_ids[cert_number]
        reason = _RECT_REASON_TPL.format(
            supplier=supplier_name,
            cert=cert_number,
            issued=issued.isoformat(),
            expires=expires.isoformat(),
        )
        if supplier_name == "PYRCOM SAS":
            reason = reason + _PYRCOM_FEEDSTOCK_SUFFIX

        bind.execute(
            sa.text(
                """
                UPDATE daily_inputs
                SET certificate_id       = :new_cert_id,
                    rectified_at         = now(),
                    rectification_source = 'other',
                    rectification_reason = :reason,
                    original_values      = COALESCE(original_values, '{}'::jsonb)
                        || jsonb_build_object(
                               'certificate_id',
                               COALESCE(
                                   (original_values->>'certificate_id')::bigint,
                                   certificate_id))
                WHERE supplier_id = (
                        SELECT id FROM suppliers
                        WHERE name = :supplier_name AND deleted_at IS NULL)
                  AND entry_date >= DATE '"""
                + _REPOINT_CUTOVER
                + """'
                  AND entry_date BETWEEN CAST(:issued AS date) AND CAST(:expires AS date)
                  AND deleted_at IS NULL
                  AND certificate_id <> :new_cert_id
                """
            ),
            {
                "new_cert_id": cert_id,
                "supplier_name": supplier_name,
                "issued": issued,
                "expires": expires,
                "reason": reason,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()

    cert_numbers = [c[1] for c in _CERTS]
    cert_id_rows = bind.execute(
        sa.text(
            "SELECT id FROM certificates WHERE cert_number = ANY(CAST(:nums AS text[]))"
        ),
        {"nums": cert_numbers},
    ).fetchall()
    cert_ids = [r[0] for r in cert_id_rows]
    if not cert_ids:
        return

    bind.execute(
        sa.text(
            """
            UPDATE daily_inputs
            SET certificate_id       = (original_values->>'certificate_id')::bigint,
                rectified_at         = NULL,
                rectification_source = NULL,
                rectification_reason = NULL,
                original_values      = NULLIF(
                    original_values - 'certificate_id',
                    '{}'::jsonb)
            WHERE certificate_id = ANY(CAST(:ids AS bigint[]))
              AND original_values ? 'certificate_id'
            """
        ),
        {"ids": cert_ids},
    )

    bind.execute(
        sa.text(
            "DELETE FROM supplier_certificates WHERE certificate_id = ANY(CAST(:ids AS bigint[]))"
        ),
        {"ids": cert_ids},
    )

    bind.execute(
        sa.text(
            "DELETE FROM certificates WHERE id = ANY(CAST(:ids AS bigint[]))"
        ),
        {"ids": cert_ids},
    )
