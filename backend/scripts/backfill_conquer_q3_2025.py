"""Backfill the 8 Conquer Trade DEV-P200 invoices Jan–Sep 2025.

Source: ``DFT_2025/INVOICES_CONQUER/INVOICES TO CONQUER 8.pdf`` (Drive),
8 invoices ``CONQ-250001..250008`` issued by OisteBio GmbH to
``C.I. CONQUERS WORLD TRADE S.A.S.`` (buyer id=23, Colombia).

Each invoice = one ``byproduct_sale`` row with ``product_kind='dev_p200'``.
The companion ``mass_balance_ledger`` row (event_type='byproduct_sale',
product_kind='dev_p200') is *not* inserted here — running
``backfill_warehouse.py --reset`` after this script picks up the new
sales and recomputes the entire chain in chronological order.

Idempotency: ON CONFLICT on (invoice_no) WHERE deleted_at IS NULL
re-uses the existing row instead of duplicating.

Usage:
    docker exec -i dft-project_backend_1 python scripts/backfill_conquer_q3_2025.py [--dry-run]
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

# Buyer C.I. CONQUERS WORLD TRADE S.A.S. — VAT NIT 901.312.960-3, Colombia.
_CONQUER_BUYER_ID = 23

# Source: PDF "INVOICES TO CONQUER 8.pdf" (drive folder DFT_2025/INVOICES_CONQUER/),
# re-extracted 2026-05-27 23:48 UTC after client renumbered the gap (was 250007 missing).
# Dates DD-MM-YYYY → ISO. kg_net = MT * 1000. Pricing $/MT and total USD.
_INVOICES: list[dict] = [
    {"invoice_no": "CONQ-250001", "sale_date": date(2025, 2, 3),
     "qty_mt": Decimal("1112"), "rate_usd_mt": Decimal("580"),
     "subtotal_usd": Decimal("644960.00")},
    {"invoice_no": "CONQ-250002", "sale_date": date(2025, 3, 3),
     "qty_mt": Decimal("923"), "rate_usd_mt": Decimal("552"),
     "subtotal_usd": Decimal("509496.00")},
    {"invoice_no": "CONQ-250003", "sale_date": date(2025, 4, 3),
     "qty_mt": Decimal("1570"), "rate_usd_mt": Decimal("532"),
     "subtotal_usd": Decimal("835240.00")},
    {"invoice_no": "CONQ-250004", "sale_date": date(2025, 5, 5),
     "qty_mt": Decimal("1347"), "rate_usd_mt": Decimal("499"),
     "subtotal_usd": Decimal("672153.00")},
    {"invoice_no": "CONQ-250005", "sale_date": date(2025, 6, 3),
     "qty_mt": Decimal("1079"), "rate_usd_mt": Decimal("472"),
     "subtotal_usd": Decimal("509288.00")},
    {"invoice_no": "CONQ-250006", "sale_date": date(2025, 7, 4),
     "qty_mt": Decimal("1467"), "rate_usd_mt": Decimal("523"),
     "subtotal_usd": Decimal("767241.00")},
    {"invoice_no": "CONQ-250007", "sale_date": date(2025, 8, 4),
     "qty_mt": Decimal("1510"), "rate_usd_mt": Decimal("521"),
     "subtotal_usd": Decimal("786710.00")},
    {"invoice_no": "CONQ-250008", "sale_date": date(2025, 9, 5),
     "qty_mt": Decimal("1058"), "rate_usd_mt": Decimal("497"),
     "subtotal_usd": Decimal("525826.00")},
]


_UPSERT_SQL = text(
    """
    INSERT INTO byproduct_sale (
        product_kind, buyer_id, sale_date, kg_net, invoice_no,
        price_amount, currency, pricing_method, pdf_ref, notes
    )
    VALUES (
        'dev_p200', :buyer_id, :sale_date, :kg_net, :invoice_no,
        :price_amount, 'USD', 'AVG_BRENT_USD_PER_MT', :pdf_ref, :notes
    )
    ON CONFLICT (invoice_no) WHERE deleted_at IS NULL DO UPDATE SET
        sale_date      = EXCLUDED.sale_date,
        kg_net         = EXCLUDED.kg_net,
        price_amount   = EXCLUDED.price_amount,
        pricing_method = EXCLUDED.pricing_method,
        pdf_ref        = EXCLUDED.pdf_ref,
        notes          = EXCLUDED.notes,
        updated_at     = now()
    RETURNING id, (xmax = 0) AS inserted
    """
)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill 8 Conquer Trade DEV-P200 byproduct_sale invoices."
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(
        f"Conquer Q3 backfill: {len(_INVOICES)} invoices, "
        f"buyer_id={_CONQUER_BUYER_ID}, dry_run={args.dry_run}"
    )

    total_kg = Decimal(0)
    total_usd = Decimal(0)

    if args.dry_run:
        for inv in _INVOICES:
            kg = inv["qty_mt"] * 1000
            total_kg += kg
            total_usd += inv["subtotal_usd"]
            print(
                f"  WOULD upsert: {inv['invoice_no']} "
                f"{inv['sale_date']} {kg} kg ${inv['subtotal_usd']}"
            )
        print(f"  TOT: {total_kg} kg, ${total_usd}")
        return

    # Pre-check unique constraint on invoice_no exists; if not, skip ON CONFLICT.
    async with async_session_factory() as db:
        idx = (await db.execute(text(
            "SELECT 1 FROM pg_indexes "
            "WHERE tablename='byproduct_sale' "
            "  AND indexdef ILIKE '%invoice_no%' "
            "  AND indexdef ILIKE '%UNIQUE%' "
            "LIMIT 1"
        ))).first()
        if idx is None:
            # Schema does not have a partial unique index on invoice_no.
            # Fall back to manual idempotency: look up by invoice_no first.
            await _manual_upsert(db, args)
            return

    async with async_session_factory() as db:
        inserted = 0
        updated = 0
        for inv in _INVOICES:
            kg = inv["qty_mt"] * 1000
            total_kg += kg
            total_usd += inv["subtotal_usd"]
            params = {
                "buyer_id": _CONQUER_BUYER_ID,
                "sale_date": inv["sale_date"],
                "kg_net": kg,
                "invoice_no": inv["invoice_no"],
                "price_amount": inv["subtotal_usd"],
                # Path is relative to /data/byproduct (the bind-mount root
                # inside the backend container). Filename matches
                # invoice_no so it stays human-grokable in audit dumps.
                "pdf_ref": f"{inv['invoice_no']}.pdf",
                "notes": (
                    f"DEV-P200 sale to Conquer Trade, "
                    f"PDF source 'INVOICES TO CONQUER 8.pdf' rev 2026-05-27"
                ),
            }
            r = await db.execute(_UPSERT_SQL, params)
            row = r.mappings().one()
            if row["inserted"]:
                inserted += 1
            else:
                updated += 1
            print(
                f"  {'INS' if row['inserted'] else 'UPD'} "
                f"id={row['id']} {inv['invoice_no']} "
                f"{inv['sale_date']} {kg} kg ${inv['subtotal_usd']}"
            )
        await db.commit()

    print(
        f"Done: {inserted} inserted, {updated} updated. "
        f"TOT {total_kg} kg, ${total_usd}."
    )
    print(
        "Next: run scripts/backfill_warehouse.py --reset "
        "to rebuild mass_balance_ledger with these sales."
    )


async def _manual_upsert(db, args) -> None:
    """Fallback when no partial unique index on invoice_no exists."""
    inserted = 0
    updated = 0
    total_kg = Decimal(0)
    total_usd = Decimal(0)
    for inv in _INVOICES:
        kg = inv["qty_mt"] * 1000
        total_kg += kg
        total_usd += inv["subtotal_usd"]
        existing = (await db.execute(text(
            "SELECT id FROM byproduct_sale "
            "WHERE invoice_no = :inv AND deleted_at IS NULL"
        ), {"inv": inv["invoice_no"]})).scalar_one_or_none()
        notes = (
            "DEV-P200 sale to Conquer Trade, "
            "PDF source 'INVOICES TO CONQUER 8.pdf' rev 2026-05-27"
        )
        pdf_ref = f"{inv['invoice_no']}.pdf"
        if existing:
            await db.execute(text(
                "UPDATE byproduct_sale SET "
                "  sale_date=:sale_date, kg_net=:kg_net, "
                "  price_amount=:price_amount, currency='USD', "
                "  pricing_method='AVG_BRENT_USD_PER_MT', "
                "  pdf_ref=:pdf_ref, "
                "  notes=:notes, updated_at=now() "
                "WHERE id=:id"
            ), {
                "sale_date": inv["sale_date"],
                "kg_net": kg,
                "price_amount": inv["subtotal_usd"],
                "pdf_ref": pdf_ref,
                "notes": notes,
                "id": existing,
            })
            updated += 1
            print(f"  UPD id={existing} {inv['invoice_no']}")
        else:
            r = await db.execute(text(
                "INSERT INTO byproduct_sale ("
                "  product_kind, buyer_id, sale_date, kg_net, invoice_no, "
                "  price_amount, currency, pricing_method, pdf_ref, notes "
                ") VALUES ("
                "  'dev_p200', :buyer_id, :sale_date, :kg_net, :invoice_no, "
                "  :price_amount, 'USD', 'AVG_BRENT_USD_PER_MT', :pdf_ref, :notes "
                ") RETURNING id"
            ), {
                "buyer_id": _CONQUER_BUYER_ID,
                "sale_date": inv["sale_date"],
                "kg_net": kg,
                "invoice_no": inv["invoice_no"],
                "price_amount": inv["subtotal_usd"],
                "pdf_ref": pdf_ref,
                "notes": notes,
            })
            new_id = r.scalar_one()
            inserted += 1
            print(f"  INS id={new_id} {inv['invoice_no']}")
    await db.commit()
    print(
        f"Done (manual): {inserted} inserted, {updated} updated. "
        f"TOT {total_kg} kg, ${total_usd}."
    )
    print(
        "Next: run scripts/backfill_warehouse.py --reset "
        "to rebuild mass_balance_ledger with these sales."
    )


if __name__ == "__main__":
    asyncio.run(main())
