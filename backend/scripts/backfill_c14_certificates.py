"""Backfill the FMS Appendix A — C14 Laboratory Certificates Log.

Source: the eight monthly radiocarbon (bio-based carbon content, EN 16640
Annex B) certificates for DEV-P100, Jan–Aug 2025, one per month:

    Jan   Bureau Veritas Amsterdam   NLADM-25-00196-001
    Feb   AmSpec Amsterdam           642-25-07578
    Mar   AmSpec Amsterdam           655-25-09885
    Apr   AmSpec Amsterdam           677-25-04587
    May   AmSpec Amsterdam           691-25-22548
    Jun   AmSpec Amsterdam           697-25-65841
    Jul   AmSpec Amsterdam           701-25-32587
    Aug   AmSpec Amsterdam           784-25-42566

Drive folder: ``DFT_2025/C14LABTEST/``. The companion PDFs are placed under
the ``C14_PDF_DIR`` bind-mount (``backend/data/c14/<cert_number>.pdf``) — the
AmSpec 7-page bundle split one page per month + the Jan Bureau Veritas single
report — this script only seeds the DB rows.

The ``sustainability_decl`` link is seeded with the project default
(DEL-CRW-2025-2) and is rectifiable later once the cert→batch→SD mapping is
finalised. ``batch_ref`` carries the lab client reference where present.

Idempotency: ON CONFLICT (cert_number) DO UPDATE re-uses the existing row and
clears ``deleted_at`` (un-delete), so reruns never duplicate.

Usage:
    docker exec -i dft-project_backend_1 python scripts/backfill_c14_certificates.py [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import text  # noqa: E402

from app.db.session import async_session_factory  # noqa: E402

_METHOD = "EN 16640 Annex B"
_PRODUCT = "DEV-P100"
_SD = "DEL-CRW-2025-2"

# cert: lab report number (UNIQUE). lab: issuing laboratory.
# month: first-of-month period. samp/test: sampled/tested dates.
# pct: bio-based carbon content %. sref: lab sample id. bref: client reference.
_SEED: list[dict] = [
    dict(cert="NLADM-25-00196-001", lab="Bureau Veritas Amsterdam", month=date(2025, 1, 1),
         samp=date(2025, 1, 30), test=date(2025, 1, 30), pct=Decimal("30.90"),
         sref="Oiste P-100", bref=None),
    dict(cert="642-25-07578", lab="AmSpec Amsterdam", month=date(2025, 2, 1),
         samp=date(2025, 2, 25), test=date(2025, 2, 28), pct=Decimal("25.80"),
         sref="bt sample 250 ml", bref="OisteBio GmbH - Febp100-25"),
    dict(cert="655-25-09885", lab="AmSpec Amsterdam", month=date(2025, 3, 1),
         samp=date(2025, 3, 18), test=date(2025, 3, 25), pct=Decimal("29.40"),
         sref="bt sample 200 ml", bref="OisteBio GmbH - Marp100-25"),
    dict(cert="677-25-04587", lab="AmSpec Amsterdam", month=date(2025, 4, 1),
         samp=date(2025, 4, 17), test=date(2025, 4, 23), pct=Decimal("32.40"),
         sref="bt sample 250 ml", bref="OisteBio GmbH - Aprp100-25"),
    dict(cert="691-25-22548", lab="AmSpec Amsterdam", month=date(2025, 5, 1),
         samp=date(2025, 5, 21), test=date(2025, 5, 28), pct=Decimal("27.80"),
         sref="bt sample 250 ml", bref="OisteBio GmbH - Mayp100-25"),
    dict(cert="697-25-65841", lab="AmSpec Amsterdam", month=date(2025, 6, 1),
         samp=date(2025, 6, 20), test=date(2025, 6, 26), pct=Decimal("30.30"),
         sref="bt sample 250 ml", bref="OisteBio GmbH - Junp100-25"),
    dict(cert="701-25-32587", lab="AmSpec Amsterdam", month=date(2025, 7, 1),
         samp=date(2025, 7, 18), test=date(2025, 7, 24), pct=Decimal("31.40"),
         sref="bt sample 200 ml", bref="OisteBio GmbH - Julp100-25"),
    dict(cert="784-25-42566", lab="AmSpec Amsterdam", month=date(2025, 8, 1),
         samp=date(2025, 8, 22), test=date(2025, 8, 29), pct=Decimal("30.30"),
         sref="bt sample 200 ml", bref="OisteBio GmbH - Augp100-25"),
]

_UPSERT = text(
    """
    INSERT INTO c14_certificates (
        cert_number, lab, product, period_month, sampled_date, tested_date,
        report_date, bio_carbon_pct, method, sample_ref, batch_ref,
        sustainability_decl, pdf_filename, deleted_at
    ) VALUES (
        :cert, :lab, :product, :month, :samp, :test,
        :test, :pct, :method, :sref, :bref,
        :sd, :pdf, NULL
    )
    ON CONFLICT (cert_number) DO UPDATE SET
        lab                 = EXCLUDED.lab,
        product             = EXCLUDED.product,
        period_month        = EXCLUDED.period_month,
        sampled_date        = EXCLUDED.sampled_date,
        tested_date         = EXCLUDED.tested_date,
        report_date         = EXCLUDED.report_date,
        bio_carbon_pct      = EXCLUDED.bio_carbon_pct,
        method              = EXCLUDED.method,
        sample_ref          = EXCLUDED.sample_ref,
        batch_ref           = EXCLUDED.batch_ref,
        sustainability_decl = EXCLUDED.sustainability_decl,
        pdf_filename        = EXCLUDED.pdf_filename,
        updated_at          = now(),
        deleted_at          = NULL;
    """
)


async def main(dry_run: bool) -> None:
    async with async_session_factory() as session:
        for row in _SEED:
            params = dict(
                cert=row["cert"], lab=row["lab"], product=_PRODUCT,
                month=row["month"], samp=row["samp"], test=row["test"],
                pct=row["pct"], method=_METHOD, sref=row["sref"],
                bref=row["bref"], sd=_SD, pdf=f"{row['cert']}.pdf",
            )
            if dry_run:
                print(f"[dry-run] {row['cert']:>20}  {row['month']}  "
                      f"{row['pct']}%  {row['lab']}")
                continue
            await session.execute(_UPSERT, params)
        if not dry_run:
            await session.commit()
            print(f"Upserted {len(_SEED)} C14 certificate rows.")
        else:
            print(f"[dry-run] {len(_SEED)} rows would be upserted.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.dry_run))
