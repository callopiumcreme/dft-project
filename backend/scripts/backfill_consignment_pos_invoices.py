"""Split invoice bundle PDF + populate ``invoice_no`` + ``invoice_pdf_ref``.

Each PoS (OISCRO-XXXX-25) has one commercial invoice issued by
OisteBio Swiss GmbH to Crown Oil Ltd.  The 20 invoices for C-1
(DEL-CRW-2025-2) live in a single bundle PDF on Drive
(``DFT_2025/INVOICES TO CROWN/invoices TO CROWN OIL.pdf``); this
script:

1. Splits the bundle into one PDF per page under
   ``/data/invoices/c-<consignment_id>/INV_<invoice_no>.pdf``.
2. Maps each invoice to the matching PoS via
   ``(issuing_date ASC, kg_net ASC)`` — robust because every invoice's
   €/kg ratio matches the daily Platts+120 price, so within a given
   day the smaller €-subtotal lines up with the smaller-kg PoS.
3. UPDATEs ``consignment_pos_customs`` keyed by ``pos_number``
   (stable business key, portable across envs — see
   ``feedback_migration_row_id_portability``).

Idempotent: rewrites the same files + the same DB rows.
Soft-deleted PoS are skipped automatically (``deleted_at IS NULL``).

Usage (run inside backend container, after copying bundle in):

    docker cp invoices_bundle.pdf dft-project_backend_1:/tmp/inv.pdf
    docker exec dft-project_backend_1 \\
        python scripts/backfill_consignment_pos_invoices.py \\
        --consignment-id 1 \\
        --bundle /tmp/inv.pdf

Flags:
    --consignment-id N   restrict to one consignment.id (required)
    --bundle PATH        master bundle PDF (one invoice per page)
    --dry-run            print plan, no writes
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402

from pypdf import PdfReader, PdfWriter  # noqa: E402

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dft:dftdev_2026@db:5432/dft",
)
INVOICES_ROOT = Path(os.environ.get("INVOICES_ROOT", "/data/invoices"))


_INV_RE = re.compile(r"Invoice#\s*(OIS-INV\d+)")
_DATE_RE = re.compile(r"Invoice Date\s*(\d{2}-\d{2}-\d{4})")
_SUB_RE = re.compile(r"Sub Total\s+([\d.,]+)")


def _parse_invoice_page(text_blob: str) -> dict | None:
    """Extract (invoice_no, issuing_date, eur_subtotal) from a page.

    Returns ``None`` if the page does not look like a Crown Oil invoice.
    """
    m_inv = _INV_RE.search(text_blob)
    m_date = _DATE_RE.search(text_blob)
    m_sub = _SUB_RE.search(text_blob)
    if not (m_inv and m_date and m_sub):
        return None
    return {
        "invoice_no": m_inv.group(1),
        "issuing_date": datetime.strptime(m_date.group(1), "%d-%m-%Y").date(),
        # Italian/Swiss format: "32.145,32" → 32145.32
        "eur_subtotal": Decimal(
            m_sub.group(1).replace(".", "").replace(",", ".")
        ),
    }


def _split_bundle(
    bundle: Path, out_dir: Path
) -> list[tuple[dict, Path]]:
    """Write one PDF per page; return per-page (meta, path) pairs."""
    out_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(bundle))
    pairs: list[tuple[dict, Path]] = []
    for page in reader.pages:
        meta = _parse_invoice_page(page.extract_text() or "")
        if meta is None:
            continue
        out_path = out_dir / f"INV_{meta['invoice_no']}.pdf"
        w = PdfWriter()
        w.add_page(page)
        with open(out_path, "wb") as fh:
            w.write(fh)
        pairs.append((meta, out_path))
    return pairs


async def _load_pos_with_customs(
    db: AsyncSession, consignment_id: int
) -> list[dict]:
    rows = (
        await db.execute(
            text(
                "SELECT c.pos_number, c.issuing_date, p.kg_net "
                "FROM consignment_pos_customs c "
                "JOIN consignment_pos p "
                "  ON p.consignment_id = c.consignment_id "
                " AND p.pos_number = c.pos_number "
                "WHERE c.consignment_id = :cid "
                "  AND c.deleted_at IS NULL "
                "  AND p.deleted_at IS NULL"
            ),
            {"cid": consignment_id},
        )
    ).mappings().all()
    return [dict(r) for r in rows]


def _pair_invoices_to_pos(
    invoices: list[dict], pos_rows: list[dict]
) -> list[tuple[str, str, str]]:
    """Return ``[(pos_number, invoice_no, pdf_ref), …]`` 1:1 pairs.

    Pairing rule: bucket by ``issuing_date``, then sort each bucket by
    a monotonic key (kg ASC for PoS, eur_subtotal ASC for invoices) and
    zip index-by-index.  €/kg ratio is constant within a day (Platts +
    120 EUR/MT), so this ordering reproduces the natural pairing.
    """
    from collections import defaultdict

    by_date_inv: dict[date, list[dict]] = defaultdict(list)
    for x in invoices:
        by_date_inv[x["issuing_date"]].append(x)
    for k in by_date_inv:
        by_date_inv[k].sort(key=lambda r: r["eur_subtotal"])

    by_date_pos: dict[date, list[dict]] = defaultdict(list)
    for x in pos_rows:
        by_date_pos[x["issuing_date"]].append(x)
    for k in by_date_pos:
        by_date_pos[k].sort(key=lambda r: r["kg_net"])

    pairs: list[tuple[str, str, str]] = []
    for d in sorted(by_date_pos):
        inv_list = by_date_inv.get(d, [])
        pos_list = by_date_pos[d]
        if len(inv_list) != len(pos_list):
            raise RuntimeError(
                f"len mismatch on {d}: {len(pos_list)} PoS vs "
                f"{len(inv_list)} invoices"
            )
        for ix in range(len(pos_list)):
            p = pos_list[ix]
            iv = inv_list[ix]
            pairs.append((p["pos_number"], iv["invoice_no"], iv["pdf_ref"]))
    return pairs


_UPDATE_SQL = text(
    """
    UPDATE consignment_pos_customs
       SET invoice_no      = :invoice_no,
           invoice_pdf_ref = :invoice_pdf_ref
     WHERE consignment_id  = :consignment_id
       AND pos_number      = :pos_number
       AND deleted_at IS NULL
    """
)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--consignment-id", type=int, required=True)
    parser.add_argument(
        "--bundle",
        type=Path,
        required=True,
        help="Path to master invoice bundle PDF (one invoice per page)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.bundle.is_file():
        print(f"  ERR: bundle not found: {args.bundle}")
        sys.exit(1)

    out_dir = INVOICES_ROOT / f"c-{args.consignment_id}"
    pairs = _split_bundle(args.bundle, out_dir)
    if not pairs:
        print(f"  ERR: no invoice pages parsed from {args.bundle}")
        sys.exit(1)

    invoices = []
    for meta, path in pairs:
        invoices.append(
            {
                **meta,
                # path is stored *relative* to /data/invoices for
                # portability across local + server bind-mount.
                "pdf_ref": f"c-{args.consignment_id}/{path.name}",
            }
        )

    print(f"  split: {len(invoices)} invoice PDFs under {out_dir}")

    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with sm() as db:
        pos_rows = await _load_pos_with_customs(db, args.consignment_id)
        if not pos_rows:
            print(
                f"  ERR: no active PoS+customs rows for "
                f"consignment {args.consignment_id}"
            )
            sys.exit(1)

        try:
            paired = _pair_invoices_to_pos(invoices, pos_rows)
        except RuntimeError as exc:
            print(f"  ERR: {exc}")
            sys.exit(1)

        print(f"  pairs: {len(paired)} PoS ↔ invoice")
        for pn, inv, ref in paired:
            print(f"    {pn} → {inv}  ({ref})")

        if args.dry_run:
            print(f"DRY-RUN: would UPDATE {len(paired)} rows. Aborting.")
            await engine.dispose()
            return

        for pn, inv, ref in paired:
            await db.execute(
                _UPDATE_SQL,
                {
                    "consignment_id": args.consignment_id,
                    "pos_number": pn,
                    "invoice_no": inv,
                    "invoice_pdf_ref": ref,
                },
            )
        await db.commit()

        print(
            f"[{datetime.utcnow().isoformat(timespec='seconds')}Z] "
            f"invoice backfill: {len(paired)} rows updated."
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
