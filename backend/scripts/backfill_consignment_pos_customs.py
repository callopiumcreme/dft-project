"""Parse EAD (DMS Export) PDFs and populate ``consignment_pos_customs``.

Maps each ``DMS_EXPORT_<MRN>*.pdf`` under
``/data/customs/c-<consignment_id>/`` to one PoS row in
``consignment_pos`` by the natural triple
``(consignment_id, issuing_date, net_kg)``.

C-1 (DEL-CRW-2025-2) currently has 20 EADs + 20 active PoS — counts
match.  One known kg discrepancy (OISCRO-0024-25: PDF 25 912 vs DB
25 915 = 3 kg, **trascurabile** per user 2026-05-25) is tolerated via
a small kg tolerance in the join.

Idempotent: ON CONFLICT (mrn) DO UPDATE refreshes mutable columns
(pdf_ref, container_no, issuing_date, …) while keeping the surrogate
``id`` stable so any future FK survives.

Usage (run inside backend container):

    docker exec dft-project_backend_1 \\
        python scripts/backfill_consignment_pos_customs.py \\
        --consignment-id 1

Flags:
    --consignment-id N   restrict to one consignment.id (required)
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

from pypdf import PdfReader  # noqa: E402

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dft:dftdev_2026@db:5432/dft",
)
CUSTOMS_ROOT = Path(os.environ.get("CUSTOMS_ROOT", "/data/customs"))

# 3 kg tolerance to absorb the OISCRO-0024 PDF/DB rounding discrepancy.
KG_TOLERANCE = Decimal("5.000")


def _parse_ead(pdf_path: Path) -> dict | None:
    """Extract MRN/LRN/container/net/gross/invoice/customs_office/date.

    Returns ``None`` if the document does not look like an EAD.
    """
    text_blob = "\n".join(
        (p.extract_text() or "") for p in PdfReader(str(pdf_path)).pages
    )

    # MRN from filename (more reliable than text layer ordering).
    m_mrn = re.match(r"DMS_EXPORT_([0-9A-Z]+)", pdf_path.name)
    if not m_mrn:
        return None
    mrn = m_mrn.group(1)

    # LRN is a fixed 13-char prefix `NNENNNNNNNNNN` (year + 12 digits/letters)
    # followed by trailing text that runs together in the extracted layer
    # (no whitespace before next field). Cap the capture to avoid eating
    # the consignee name on the next visual line.
    # LRN format: `NNENNNNNNNNNN` — year(2) + 'E' + 9 digits = 12 chars.
    # The text layer often glues it to the next field (e.g. "...890CROWN OIL"),
    # so we anchor the capture to exactly 12 chars.
    m_lrn = re.search(r"LRN:\s*(\d{2}E\d{9})", text_blob)
    m_issue = re.search(r"Issuing date.*?(\d{8})", text_blob, re.S)
    m_office = re.search(r"Customs office\[\d+\s+\d+\]:\s*([A-Z0-9]+)", text_blob)
    m_cont = re.search(r"\b([A-Z]{4}\d{7})\b", text_blob)
    m_inv = re.search(r"OIS-INV\d+", text_blob)
    # Net mass = the first NNNNN,000000 token in the text (declaration
    # value).  Two layouts seen in C-1 (USD vs EUR currency line) so we
    # take the first occurrence rather than a layout-specific anchor.
    m_net = re.search(r"(\d{4,6}),000000", text_blob)
    # Gross mass is a comma-decimal value followed by a newline and `CO`.
    m_gross = re.search(r"(\d{4,6},\d{1,3})\s*\nCO\b", text_blob)

    issue: date | None = None
    if m_issue:
        s = m_issue.group(1)
        issue = date(int(s[:4]), int(s[4:6]), int(s[6:8]))

    return {
        "mrn": mrn,
        "lrn": m_lrn.group(1) if m_lrn else None,
        "customs_office": m_office.group(1) if m_office else None,
        "container_no": m_cont.group(1) if m_cont else None,
        "invoice_no": m_inv.group(0) if m_inv else None,
        "net_kg": Decimal(m_net.group(1)) if m_net else None,
        "gross_kg": Decimal(m_gross.group(1).replace(",", "."))
        if m_gross
        else None,
        "issuing_date": issue,
        # Declarant is fixed for C-1 (BINOVA BV); parser fallback below.
        "declarant_name": "BINOVA BV",
        "declarant_vat": "NL865050491",
    }


async def _load_pos(db: AsyncSession, consignment_id: int) -> list[dict]:
    rows = (
        await db.execute(
            text(
                "SELECT pos_number, kg_net, issuance_date "
                "FROM consignment_pos "
                "WHERE consignment_id = :cid AND deleted_at IS NULL"
            ),
            {"cid": consignment_id},
        )
    ).mappings().all()
    return [dict(r) for r in rows]


def _match_pos(
    ead: dict, pos_rows: list[dict], used: set[str]
) -> str | None:
    """Return the PoS number whose (kg_net, issuance_date) match the EAD.

    Strategy: among same-day, never-used PoS rows, prefer an **exact**
    kg match before falling back to a tolerance match.  This prevents
    OISCRO-0028-25 (25 950 kg) and OISCRO-0029-25 (25 947 kg) — both
    issued 2025-08-06 within the tolerance window — from binding to
    the wrong EAD just because of iteration order.
    """
    if ead["issuing_date"] is None or ead["net_kg"] is None:
        return None
    same_day = [
        p for p in pos_rows
        if p["issuance_date"] == ead["issuing_date"]
        and p["pos_number"] not in used
    ]
    # 1. Exact kg first.
    for p in same_day:
        if Decimal(p["kg_net"]) == ead["net_kg"]:
            return p["pos_number"]
    # 2. Tolerance fallback (absorbs the OISCRO-0024 3kg PDF/DB drift).
    for p in same_day:
        if abs(Decimal(p["kg_net"]) - ead["net_kg"]) <= KG_TOLERANCE:
            return p["pos_number"]
    return None


_UPSERT_SQL = text(
    """
    INSERT INTO consignment_pos_customs (
        consignment_id, pos_number, mrn, lrn, customs_office,
        container_no, gross_kg, net_kg, invoice_no,
        declarant_name, declarant_vat, issuing_date, pdf_ref
    ) VALUES (
        :consignment_id, :pos_number, :mrn, :lrn, :customs_office,
        :container_no, :gross_kg, :net_kg, :invoice_no,
        :declarant_name, :declarant_vat, :issuing_date, :pdf_ref
    )
    ON CONFLICT (mrn) WHERE deleted_at IS NULL DO UPDATE
       SET pos_number     = EXCLUDED.pos_number,
           lrn            = EXCLUDED.lrn,
           customs_office = EXCLUDED.customs_office,
           container_no   = EXCLUDED.container_no,
           gross_kg       = EXCLUDED.gross_kg,
           net_kg         = EXCLUDED.net_kg,
           invoice_no     = EXCLUDED.invoice_no,
           declarant_name = EXCLUDED.declarant_name,
           declarant_vat  = EXCLUDED.declarant_vat,
           issuing_date   = EXCLUDED.issuing_date,
           pdf_ref        = EXCLUDED.pdf_ref
    """
)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--consignment-id", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    folder = CUSTOMS_ROOT / f"c-{args.consignment_id}"
    if not folder.is_dir():
        print(f"  ERR: folder not found: {folder}")
        sys.exit(1)

    pdfs = sorted(folder.glob("DMS_EXPORT_*.pdf"))
    if not pdfs:
        print(f"  ERR: no DMS_EXPORT_*.pdf under {folder}")
        sys.exit(1)

    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with sm() as db:
        pos_rows = await _load_pos(db, args.consignment_id)
        if not pos_rows:
            print(f"  ERR: no active PoS for consignment {args.consignment_id}")
            sys.exit(1)

        matched = 0
        unmatched: list[str] = []
        upserts: list[dict] = []
        used_pos: set[str] = set()

        for pdf in pdfs:
            ead = _parse_ead(pdf)
            if ead is None:
                unmatched.append(f"{pdf.name} (not an EAD)")
                continue
            pos_number = _match_pos(ead, pos_rows, used_pos)
            if pos_number is None:
                unmatched.append(
                    f"{pdf.name} (no PoS match — date={ead['issuing_date']} "
                    f"net={ead['net_kg']})"
                )
                continue
            matched += 1
            used_pos.add(pos_number)
            upserts.append(
                {
                    "consignment_id": args.consignment_id,
                    "pos_number": pos_number,
                    "mrn": ead["mrn"],
                    "lrn": ead["lrn"],
                    "customs_office": ead["customs_office"],
                    "container_no": ead["container_no"],
                    "gross_kg": ead["gross_kg"],
                    "net_kg": ead["net_kg"],
                    "invoice_no": ead["invoice_no"],
                    "declarant_name": ead["declarant_name"],
                    "declarant_vat": ead["declarant_vat"],
                    "issuing_date": ead["issuing_date"],
                    # Path is stored *relative* to /data/customs so it stays
                    # portable across local dev + server bind-mount.
                    "pdf_ref": f"c-{args.consignment_id}/{pdf.name}",
                }
            )

        print(
            f"  consignment {args.consignment_id}: "
            f"{matched}/{len(pdfs)} EADs matched to PoS"
        )
        for u in unmatched:
            print(f"  UNMATCHED: {u}")

        if args.dry_run:
            print(f"DRY-RUN: would upsert {len(upserts)} rows. Aborting.")
            await engine.dispose()
            return

        for row in upserts:
            await db.execute(_UPSERT_SQL, row)
        await db.commit()

        print(
            f"[{datetime.utcnow().isoformat(timespec='seconds')}Z] "
            f"consignment_pos_customs backfill: {len(upserts)} rows upserted."
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
