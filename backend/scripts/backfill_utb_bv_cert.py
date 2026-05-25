"""Backfill UTB B.V. ISCC EU certificate row + link to leg #3 (transload).

Closes gap **G3** of ``docs/gap-analysis-2026-05-25.md`` for the c-1
chain-of-custody. Idempotent — re-running upserts the same row and
re-links the same shipment_leg.

What it does
------------
1. ``INSERT … ON CONFLICT (cert_number) DO UPDATE`` on ``certificates``
   with the UTB B.V. row (cert_number ``EU-ISCC-Cert-NL220-2228065006``,
   scheme ``ISCC EU``, issued 2024-12-16, expires 2025-12-15,
   ``pdf_ref = utb-bv/CERTIFICATE_UTB_BV.pdf``).
2. ``UPDATE shipment_leg`` keyed on the **business key**
   ``(consignment_id, leg_type='utb_transload', deleted_at IS NULL)`` —
   never on auto-increment id (cf. row-id portability rule). Sets
   ``operator_certificate_id`` to the certificate row returned by
   step 1.

PDF placement (out of band, prerequisite):

    mkdir -p data/certificates/utb-bv/
    cp 'deliverables/RTFO-310825/03_supplier_evidence/certificates/CERTIFICATE UTB BV.pdf' \\
       data/certificates/utb-bv/CERTIFICATE_UTB_BV.pdf

Usage (inside backend container):

    docker exec dft-project_backend_1 \\
        python scripts/backfill_utb_bv_cert.py --consignment-id 1

Flags:
    --consignment-id N   target consignment.id (default: 1, the c-1 Q3 leg)
    --dry-run            print plan, no writes
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dft:dftdev_2026@db:5432/dft",
)

# Cert facts extracted from the PDF (pages=1):
#
#     Certificate Number: EU-ISCC-Cert-NL220-2228065006
#     UTB B.V., Kamerlingh Onnesweg 28, 3316 GL Dordrecht, NL
#     ISCC EU — Trader with storage
#     Valid from 16.12.2024 to 15.12.2025
#     Issuing body: DEKRA Certification BV (Arnhem)
#     Place + date of issue: Arnhem, 11.12.2024
#
# Values constant (this is the actual certificate, not a placeholder).
CERT_NUMBER = "EU-ISCC-Cert-NL220-2228065006"
CERT_SCHEME = "ISCC EU"
CERT_ISSUED = date(2024, 12, 16)
CERT_EXPIRES = date(2025, 12, 15)
CERT_PDF_REF = "utb-bv/CERTIFICATE_UTB_BV.pdf"
CERT_NOTES = (
    "DEKRA Certification BV (Arnhem). UTB B.V. Dordrecht NL — "
    "Trader with storage. Place + date of issue: Arnhem, 11.12.2024. "
    "Backfilled from deliverables/RTFO-310825/03_supplier_evidence/."
)


UPSERT_CERT_SQL = text("""
    INSERT INTO certificates (
        cert_number, scheme, status, issued_at, expires_at,
        is_placeholder, pdf_ref, notes
    )
    VALUES (
        :cert_number, :scheme, 'active', :issued_at, :expires_at,
        false, :pdf_ref, :notes
    )
    ON CONFLICT (cert_number) DO UPDATE SET
        scheme       = EXCLUDED.scheme,
        status       = EXCLUDED.status,
        issued_at    = EXCLUDED.issued_at,
        expires_at   = EXCLUDED.expires_at,
        is_placeholder = false,
        pdf_ref      = EXCLUDED.pdf_ref,
        notes        = EXCLUDED.notes,
        updated_at   = now(),
        deleted_at   = NULL
    RETURNING id
""")


LINK_LEG_SQL = text("""
    UPDATE shipment_leg
       SET operator_certificate_id = :cert_id,
           updated_at = now()
     WHERE consignment_id = :consignment_id
       AND leg_type = 'utb_transload'
       AND deleted_at IS NULL
    RETURNING id, document_ref, operator_certificate_id
""")


async def _run(consignment_id: int, dry_run: bool) -> None:
    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        if dry_run:
            print("[dry-run] would UPSERT certificates row:")
            print(f"  cert_number = {CERT_NUMBER}")
            print(f"  scheme      = {CERT_SCHEME}")
            print(f"  issued_at   = {CERT_ISSUED}")
            print(f"  expires_at  = {CERT_EXPIRES}")
            print(f"  pdf_ref     = {CERT_PDF_REF}")
            # S608 false positive: this is a print(), not query execution.
            print(
                "[dry-run] would UPDATE shipment_leg SET operator_certificate_id"  # noqa: S608
                f" = <cert.id> WHERE consignment_id = {consignment_id}"
                " AND leg_type = 'utb_transload' AND deleted_at IS NULL"
            )
            return

        result = await session.execute(
            UPSERT_CERT_SQL,
            {
                "cert_number": CERT_NUMBER,
                "scheme": CERT_SCHEME,
                "issued_at": CERT_ISSUED,
                "expires_at": CERT_EXPIRES,
                "pdf_ref": CERT_PDF_REF,
                "notes": CERT_NOTES,
            },
        )
        cert_id = result.scalar_one()
        print(f"✔ certificates row upserted, id = {cert_id}")

        result = await session.execute(
            LINK_LEG_SQL,
            {"cert_id": cert_id, "consignment_id": consignment_id},
        )
        rows = result.fetchall()
        if not rows:
            print(
                f"⚠ no utb_transload leg found for consignment_id={consignment_id} "
                "— cert row created but no leg linked"
            )
        for r in rows:
            print(
                f"✔ shipment_leg id={r.id} ({r.document_ref}) "
                f"operator_certificate_id={r.operator_certificate_id}"
            )

        await session.commit()
        print("done.")

    await engine.dispose()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--consignment-id",
        type=int,
        default=1,
        help="consignment.id of the transload leg to link (default: 1)",
    )
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    asyncio.run(_run(args.consignment_id, args.dry_run))


if __name__ == "__main__":
    main()
