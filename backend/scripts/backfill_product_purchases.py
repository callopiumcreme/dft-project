"""Backfill the supplier feedstock PoS into ``product_purchases``.

Source: the collective monthly Sustainability Declarations (ISCC PLUS SD
template v3.5.2 / v3.6) issued by the four ELT feedstock suppliers to
OisteBio GmbH, plus the January plastics collective from ESENTTIA.

Drive folder: ``DFT_2025/POS E FATTURE MANCANTI/POS_generati/`` (28 ELT PoS,
4 suppliers x Feb–Aug 2025) + ``.../esentiia_pos/ISCCPLUS_SD_v3.6_14.pdf``
(ESENTTIA ES2025-014, Jan). The companion PDFs are copied to the
``POS_PDF_DIR`` bind-mount (``backend/data/pos/<pos_number>.pdf``) by the
caller (rclone) — this script only seeds the DB rows.

Each row links to the supplier (by code), the supplier certificate stated
on the PoS (by ``cert_number``, cell C19) and the purchase contract (by
``code``, cell P19). ``quantity_kg`` is cell I41 (certified material, mt)
* 1000 — verified equal to the monthly ``daily_inputs`` totals per supplier.

Idempotency: ON CONFLICT (pos_number) DO UPDATE re-uses the existing row
and clears ``deleted_at`` (un-delete), so reruns never duplicate.

Usage:
    docker exec -i dft-project_backend_1 python scripts/backfill_product_purchases.py [--dry-run]
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

# pos: unique business key (cell J3). sup: suppliers.code. iss: issuance (J6).
# qty_kg: certified material (I41 mt * 1000). cert: cert_number (C19).
# ctr: contract code (P19). disp: date-of-dispatch label (J30). feed: J35.
_SEED: list[dict] = [
    dict(pos="OISTEBIO-2025-001", sup="BOLDER", iss=date(2025, 2, 28), qty_kg=Decimal("224359.000"), cert="US201-120372024", ctr="BO150225", disp="01.02.2025 - 28.02.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="OISTEBIO-2025-007", sup="BOLDER", iss=date(2025, 3, 31), qty_kg=Decimal("182759.000"), cert="US201-120372024", ctr="BO150225", disp="01.03.2025 - 31.03.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="OISTEBIO-2025-009", sup="BOLDER", iss=date(2025, 4, 30), qty_kg=Decimal("319308.000"), cert="US201-120372025", ctr="BO150225", disp="01.04.2025 - 30.04.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="OISTEBIO-2025-011", sup="BOLDER", iss=date(2025, 5, 31), qty_kg=Decimal("250535.000"), cert="US201-120372025", ctr="BO150225", disp="01.05.2025 - 31.05.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="OISTEBIO-2025-015", sup="BOLDER", iss=date(2025, 6, 30), qty_kg=Decimal("193206.000"), cert="US201-120372025", ctr="BO150225", disp="01.06.2025 - 30.06.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="OISTEBIO-2025-019", sup="BOLDER", iss=date(2025, 7, 31), qty_kg=Decimal("388642.000"), cert="US201-120372025", ctr="BO150225", disp="01.07.2025 - 31.07.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="OISTEBIO-2025-024", sup="BOLDER", iss=date(2025, 8, 31), qty_kg=Decimal("372597.000"), cert="US201-120372025", ctr="BO150225", disp="01.08.2025 - 31.08.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="ET-OB-25-006", sup="EFFICIEN", iss=date(2025, 2, 28), qty_kg=Decimal("898747.000"), cert="US201-158772025", ctr="EF010225", disp="01.02.2025 - 28.02.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="ET-OB-25-009", sup="EFFICIEN", iss=date(2025, 3, 31), qty_kg=Decimal("1044711.000"), cert="US201-158772025", ctr="EF010225", disp="01.03.2025 - 31.03.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="ET-OB-25-012", sup="EFFICIEN", iss=date(2025, 4, 30), qty_kg=Decimal("983066.000"), cert="US201-158772025", ctr="EF010225", disp="01.04.2025 - 30.04.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="ET-OB-25-019", sup="EFFICIEN", iss=date(2025, 5, 31), qty_kg=Decimal("1025174.000"), cert="US201-158772025", ctr="EF010225", disp="01.05.2025 - 31.05.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="ET-OB-25-027", sup="EFFICIEN", iss=date(2025, 6, 30), qty_kg=Decimal("879813.000"), cert="US201-158772025", ctr="EF010225", disp="01.06.2025 - 30.06.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="ET-OB-25-031", sup="EFFICIEN", iss=date(2025, 7, 31), qty_kg=Decimal("1031819.000"), cert="US201-158772025", ctr="EF010225", disp="01.07.2025 - 31.07.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="ET-OB-25-039", sup="EFFICIEN", iss=date(2025, 8, 31), qty_kg=Decimal("895513.000"), cert="US201-158772025", ctr="EF010225", disp="01.08.2025 - 31.08.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="KAL-OIS-007", sup="KALTIRE", iss=date(2025, 2, 28), qty_kg=Decimal("687236.000"), cert="US201-138762024", ctr="KT200125", disp="01.02.2025 - 28.02.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="KAL-OIS-012", sup="KALTIRE", iss=date(2025, 3, 31), qty_kg=Decimal("889067.000"), cert="US201-138762024", ctr="KT200125", disp="01.03.2025 - 31.03.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="KAL-OIS-017", sup="KALTIRE", iss=date(2025, 4, 30), qty_kg=Decimal("733657.000"), cert="US201-138762024", ctr="KT200125", disp="01.04.2025 - 30.04.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="KAL-OIS-025", sup="KALTIRE", iss=date(2025, 5, 31), qty_kg=Decimal("839062.000"), cert="US201-138762025", ctr="KT200125", disp="01.05.2025 - 31.05.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="KAL-OIS-029", sup="KALTIRE", iss=date(2025, 6, 30), qty_kg=Decimal("794011.000"), cert="US201-138762025", ctr="KT200125", disp="01.06.2025 - 30.06.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="KAL-OIS-033", sup="KALTIRE", iss=date(2025, 7, 31), qty_kg=Decimal("1092526.000"), cert="US201-138762025", ctr="KT200125", disp="01.07.2025 - 31.07.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="KAL-OIS-041", sup="KALTIRE", iss=date(2025, 8, 31), qty_kg=Decimal("759200.000"), cert="US201-138762025", ctr="KT200125", disp="01.08.2025 - 31.08.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="2025-OISTE-004", sup="PYRCOM", iss=date(2025, 2, 28), qty_kg=Decimal("491518.000"), cert="ES216-20249051", ctr="PY250125", disp="01.02.2025 - 28.02.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="2025-OISTE-006", sup="PYRCOM", iss=date(2025, 3, 31), qty_kg=Decimal("471975.000"), cert="ES216-20249051", ctr="PY250125", disp="01.03.2025 - 31.03.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="2025-OISTE-008", sup="PYRCOM", iss=date(2025, 4, 30), qty_kg=Decimal("419057.000"), cert="ES216-20249051", ctr="PY250125", disp="01.04.2025 - 30.04.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="2025-OISTE-014", sup="PYRCOM", iss=date(2025, 5, 31), qty_kg=Decimal("499159.000"), cert="ES216-20249051", ctr="PY250125", disp="01.05.2025 - 31.05.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="2025-OISTE-016", sup="PYRCOM", iss=date(2025, 6, 30), qty_kg=Decimal("661806.000"), cert="ES216-20249051", ctr="PY250125", disp="01.06.2025 - 30.06.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="2025-OISTE-019", sup="PYRCOM", iss=date(2025, 7, 31), qty_kg=Decimal("692867.000"), cert="ES216-20249051", ctr="PY250125", disp="01.07.2025 - 31.07.2025", feed="ELT End-of-Life Tyres"),
    dict(pos="2025-OISTE-024", sup="PYRCOM", iss=date(2025, 8, 31), qty_kg=Decimal("623785.000"), cert="ES216-20249051", ctr="PY250125", disp="01.08.2025 - 31.08.2025", feed="ELT End-of-Life Tyres"),
    # ESENTTIA January plastics collective (template v3.6). qty = aggregated
    # 07–31 Jan deliveries (1395.369 mt) per the issued PoS, < the full-month
    # daily_inputs total (1549.811 mt) which also covers 01–06 Jan.
    dict(pos="ES2025-014", sup="ESENTTIA", iss=date(2025, 2, 3), qty_kg=Decimal("1395369.000"), cert="CO222-00000027", ctr="ES400125", disp="aggregated deliveries from 7 january to 31 January", feed="Mixed plastic waste"),
]


_UPSERT_SQL = text(
    """
    INSERT INTO product_purchases (
        pos_number, supplier_id, certificate_id, contract_id,
        issuance_date, dispatch_label, quantity_kg, feedstock, notes
    )
    VALUES (
        :pos_number, :supplier_id, :certificate_id, :contract_id,
        :issuance_date, :dispatch_label, :quantity_kg, :feedstock, :notes
    )
    ON CONFLICT (pos_number) DO UPDATE SET
        supplier_id    = EXCLUDED.supplier_id,
        certificate_id = EXCLUDED.certificate_id,
        contract_id    = EXCLUDED.contract_id,
        issuance_date  = EXCLUDED.issuance_date,
        dispatch_label = EXCLUDED.dispatch_label,
        quantity_kg    = EXCLUDED.quantity_kg,
        feedstock      = EXCLUDED.feedstock,
        notes          = EXCLUDED.notes,
        deleted_at     = NULL,
        updated_at     = now()
    RETURNING id, (xmax = 0) AS inserted
    """
)

_NOTE = "Supplier feedstock PoS (collective monthly SD). Backfill from Drive POS_generati."


async def _load_maps(db) -> tuple[dict, dict, dict]:
    sup = {
        c: i
        for c, i in (
            await db.execute(text("SELECT code, id FROM suppliers WHERE deleted_at IS NULL"))
        ).all()
    }
    cert = {
        n: i
        for n, i in (
            await db.execute(
                text("SELECT cert_number, id FROM certificates WHERE deleted_at IS NULL")
            )
        ).all()
    }
    ctr = {
        c: i
        for c, i in (
            await db.execute(text("SELECT code, id FROM contracts WHERE deleted_at IS NULL"))
        ).all()
    }
    return sup, cert, ctr


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill supplier feedstock PoS into product_purchases."
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"product_purchases backfill: {len(_SEED)} PoS, dry_run={args.dry_run}")

    async with async_session_factory() as db:
        sup_map, cert_map, ctr_map = await _load_maps(db)

        missing: list[str] = []
        for r in _SEED:
            if r["sup"] not in sup_map:
                missing.append(f"{r['pos']}: supplier {r['sup']!r}")
            if r["cert"] not in cert_map:
                missing.append(f"{r['pos']}: cert {r['cert']!r}")
            if r["ctr"] not in ctr_map:
                missing.append(f"{r['pos']}: contract {r['ctr']!r}")
        if missing:
            print("ABORT — unresolved business keys:")
            for m in missing:
                print(f"  {m}")
            sys.exit(1)

        total_kg = Decimal(0)
        inserted = 0
        updated = 0
        for r in _SEED:
            total_kg += r["qty_kg"]
            params = {
                "pos_number": r["pos"],
                "supplier_id": sup_map[r["sup"]],
                "certificate_id": cert_map[r["cert"]],
                "contract_id": ctr_map[r["ctr"]],
                "issuance_date": r["iss"],
                "dispatch_label": r["disp"],
                "quantity_kg": r["qty_kg"],
                "feedstock": r["feed"],
                "notes": _NOTE,
            }
            if args.dry_run:
                print(
                    f"  WOULD upsert {r['pos']:18} sup={r['sup']:9} "
                    f"{r['iss']} {r['qty_kg']} kg cert={r['cert']}"
                )
                continue
            res = await db.execute(_UPSERT_SQL, params)
            row = res.mappings().one()
            if row["inserted"]:
                inserted += 1
            else:
                updated += 1
            print(
                f"  {'INS' if row['inserted'] else 'UPD'} id={row['id']} "
                f"{r['pos']:18} sup={r['sup']:9} {r['iss']} {r['qty_kg']} kg"
            )

        if args.dry_run:
            print(f"  TOT: {total_kg} kg over {len(_SEED)} PoS")
            return

        await db.commit()

    print(f"Done: {inserted} inserted, {updated} updated. TOT {total_kg} kg.")
    print(
        "PDFs must be present at POS_PDF_DIR (backend/data/pos/<pos_number>.pdf) "
        "for the in-app viewer to serve them."
    )


if __name__ == "__main__":
    asyncio.run(main())
