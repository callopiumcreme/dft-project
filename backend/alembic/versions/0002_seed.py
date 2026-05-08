"""seed real anagrafiche from xlsx 2025 (7 suppliers, 9 certs, 5 contracts, junction)

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-08

Source: docs/analisi-xlsx-2025.md (Girardot producciòn Enero 2025.xlsx, 9 sheets, 2429 entries).
Idempotent: ON CONFLICT DO NOTHING.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


SUPPLIERS = [
    # name, code, country, is_aggregate, notes
    ("ESENTTIA", "ESENTTIA", "CO", False, "producer principale"),
    ("SANIMAX", "SANIMAX", "CO", False, None),
    ("LITOPLAS", "LITOPLAS", "CO", False, None),
    ("CIECOGRAS", "CIECOGRAS", "CO", False, None),
    ("BIOWASTE", "BIOWASTE", "CO", False, "cert PL21990602701"),
    ("ECODIESEL", "ECODIESEL", "CO", False, "new in SEP 2025"),
    ("≤5 TON", "LE5TON", "CO", True, "aggregato anonimo small suppliers"),
]

CERTIFICATES = [
    # cert_number, scheme, status, is_placeholder, notes
    ("CO222-00000026", "ISCC EU", "active", False, "shared multi-supplier"),
    ("CO222-00000027", "ISCC EU", "active", False, "shared multi-supplier"),
    ("ES216-20254036", "ISCC EU", "active", False, "shared multi-supplier"),
    ("ES216-20268083", "ISCC EU", "active", False, "shared multi-supplier"),
    ("PL219-91159801", "ISCC EU", "active", False, "ECODIESEL dedicated"),
    ("PL21990602701", "ISCC EU", "active", False, "BIOWASTE dedicated"),
    ("-", "PLACEHOLDER", "placeholder", True, "no-cert placeholder for ≤5 TON"),
    ("SD", "SELF-DECL", "placeholder", True, "self-declaration short"),
    ("SELF DECL. ISCC", "SELF-DECL", "placeholder", True, "self-declaration full"),
]

CERT_SUPPLIERS = [
    ("CO222-00000026", ["ESENTTIA", "LITOPLAS", "SANIMAX", "LE5TON"]),
    ("CO222-00000027", ["CIECOGRAS", "ESENTTIA", "LITOPLAS", "SANIMAX"]),
    ("ES216-20254036", ["CIECOGRAS", "LITOPLAS", "SANIMAX", "LE5TON"]),
    ("ES216-20268083", ["CIECOGRAS", "ESENTTIA", "LITOPLAS", "SANIMAX"]),
    ("PL219-91159801", ["ECODIESEL"]),
    ("PL21990602701", ["BIOWASTE"]),
    ("-", ["LE5TON"]),
    ("SD", ["LE5TON"]),
    ("SELF DECL. ISCC", ["LE5TON"]),
]

CONTRACTS = [
    # code, supplier_code (None for shared placeholder), is_placeholder, notes
    ("BW200224", "BIOWASTE", False, None),
    ("ES400125", "ESENTTIA", False, None),
    ("LP300324", "LITOPLAS", False, None),
    ("SD", "LE5TON", True, "self-declaration"),
    ("-", None, True, "shared placeholder (CIECOGRAS, ESENTTIA, SANIMAX, ≤5 TON)"),
]


def upgrade() -> None:
    conn = op.get_bind()

    insert_supplier = text(
        "INSERT INTO suppliers (name, code, country, is_aggregate, notes) "
        "VALUES (:name, :code, :country, :is_aggregate, :notes) "
        "ON CONFLICT (code) DO NOTHING"
    )
    for name, code, country, is_agg, notes in SUPPLIERS:
        conn.execute(
            insert_supplier,
            {"name": name, "code": code, "country": country, "is_aggregate": is_agg, "notes": notes},
        )

    insert_cert = text(
        "INSERT INTO certificates (cert_number, scheme, status, is_placeholder, notes) "
        "VALUES (:cert_number, :scheme, :status, :is_placeholder, :notes) "
        "ON CONFLICT (cert_number) DO NOTHING"
    )
    for cert_number, scheme, status, is_ph, notes in CERTIFICATES:
        conn.execute(
            insert_cert,
            {
                "cert_number": cert_number,
                "scheme": scheme,
                "status": status,
                "is_placeholder": is_ph,
                "notes": notes,
            },
        )

    link_cert = text(
        "INSERT INTO supplier_certificates (supplier_id, certificate_id) "
        "SELECT s.id, c.id FROM suppliers s, certificates c "
        "WHERE s.code = :supplier_code AND c.cert_number = :cert_number "
        "ON CONFLICT DO NOTHING"
    )
    for cert_number, supplier_codes in CERT_SUPPLIERS:
        for supplier_code in supplier_codes:
            conn.execute(link_cert, {"supplier_code": supplier_code, "cert_number": cert_number})

    insert_contract_no_supplier = text(
        "INSERT INTO contracts (code, supplier_id, is_placeholder, notes) "
        "VALUES (:code, NULL, :is_placeholder, :notes) "
        "ON CONFLICT (code) DO NOTHING"
    )
    insert_contract_with_supplier = text(
        "INSERT INTO contracts (code, supplier_id, is_placeholder, notes) "
        "SELECT :code, s.id, :is_placeholder, :notes FROM suppliers s "
        "WHERE s.code = :supplier_code "
        "ON CONFLICT (code) DO NOTHING"
    )
    for code, supplier_code, is_ph, notes in CONTRACTS:
        if supplier_code is None:
            conn.execute(
                insert_contract_no_supplier,
                {"code": code, "is_placeholder": is_ph, "notes": notes},
            )
        else:
            conn.execute(
                insert_contract_with_supplier,
                {
                    "code": code,
                    "is_placeholder": is_ph,
                    "notes": notes,
                    "supplier_code": supplier_code,
                },
            )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text("DELETE FROM contracts WHERE code IN ('BW200224','ES400125','LP300324','SD','-')")
    )
    conn.execute(text("DELETE FROM supplier_certificates"))
    conn.execute(
        text(
            "DELETE FROM certificates WHERE cert_number IN "
            "('CO222-00000026','CO222-00000027','ES216-20254036','ES216-20268083',"
            "'PL219-91159801','PL21990602701','-','SD','SELF DECL. ISCC')"
        )
    )
    conn.execute(
        text(
            "DELETE FROM suppliers WHERE code IN "
            "('ESENTTIA','SANIMAX','LITOPLAS','CIECOGRAS','BIOWASTE','ECODIESEL','LE5TON')"
        )
    )
