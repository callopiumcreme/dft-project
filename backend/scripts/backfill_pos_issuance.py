"""Backfill ``consignment_pos.issuance_date`` from POS PDF documents.

The PoS PDF carries its own ``Date of issuance of the PoS`` (V_unknown, new
template, YYYY-MM-DD) or ``Date of Issuance of the PoS:`` (V3.1, old
template, DD.MM.YYYY). That date is the legal moment custody of the EU oil
transfers to Crown Oil and is the correct ``event_date`` for the
``pos_issue`` mass-balance ledger row.

This script reads the PDFs from ``--pdf-dir`` (default
``/tmp/pos_pdfs``), parses the issuance date, and updates
``consignment_pos.issuance_date`` keyed on ``pos_number`` (the unique
short code on the PDF, e.g. ``OISCRO-0013-25``). Rows whose
``issuance_date`` is already populated are skipped unless ``--force`` is
passed. Rows whose PDF is missing or unparseable are reported but never
fail the script.

Known refuse fixup: PO#1186 / 1240 / 1242 print ``29.02.2025`` which is an
invalid date (2025 is not a leap year). Per operator decision logged in
the runbook, those three are remapped to ``2025-03-01`` before the
UPDATE. The remap table is explicit so it shows up in any audit diff.

Usage:
    docker exec -i dft-project_backend_1 \\
        python scripts/backfill_pos_issuance.py [--dry-run] [--force] \\
        [--pdf-dir /tmp/pos_pdfs]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from datetime import date
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

import fitz  # PyMuPDF  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dft:dftdev_2026@db:5432/dft",
)


# Maps a literal date string found in the PDF to a corrected date string.
# Used only for known refusi the operator has explicitly approved fixing.
_DATE_REMAP: dict[str, str] = {
    "29.02.2025": "01.03.2025",
}


# pos_number on the PDF that the script tries before falling back to the
# filename stem. New template PDFs (``OISCRO-0013-25`` etc.) put their
# pos_number under ``Unique Number of the PoS``. Old V3.1 PDFs use
# ``ISCC-OISCRO-NNNN-25``.
_POS_NUM_RE = re.compile(r"((?:ISCC-)?OISCRO-\d{4})[\s_-]*-\s*(\d{2})(?!\d)")
_ISSUE_NEW_RE = re.compile(
    r"Date of issuance of the PoS[^\n]*\n\s*(\d{4}-\d{2}-\d{2})"
)
_DATE_DOT_RE = re.compile(r"\b(\d{1,2})\.(\d{2})\.(\d{4})\b")


def _normalize_pos_number(m: re.Match) -> str:
    """Reassemble a canonical ``OISCRO-NNNN-YY`` from a 2-group match.

    The regex captures (base, year-suffix) separately because some PDFs
    print the value with a stray space or underscore between the ``NNNN``
    and ``-YY`` parts (``OISCRO-0016 -25``, ``OISCRO-0016_-25``). The
    ``ISCC-`` prefix on V3.1 PDFs is also stripped here.
    """
    base = m.group(1)
    yy = m.group(2)
    if base.startswith("ISCC-"):
        base = base[5:]
    return f"{base}-{yy}"


def _extract_issuance(pdf_path: Path) -> date | None:
    """Return the issuance date parsed from the PDF, or ``None`` if the
    document does not match either known template.

    Strategy:
      1. Look for the new-template label (``Date of issuance of the PoS
         (YYYY-MM-DD):``) and parse the ISO date directly.
      2. Fall back to the old V3.1 template: collect every ``DD.MM.YYYY``
         occurrence, drop the 2012 cert footer, pick the *latest* 2025
         date (issuance is always ≥ dispatch on these documents). Apply
         ``_DATE_REMAP`` to known refusi before parsing.
    """
    text_all = "\n".join(p.get_text() for p in fitz.open(pdf_path))

    m_new = _ISSUE_NEW_RE.search(text_all)
    if m_new is not None:
        return date.fromisoformat(m_new.group(1))

    dotted = _DATE_DOT_RE.findall(text_all)
    candidates: set[str] = set()
    for d, mo, y in dotted:
        if y != "2025":
            continue
        raw = f"{int(d):02d}.{mo}.{y}"
        candidates.add(_DATE_REMAP.get(raw, raw))
    if not candidates:
        return None
    latest = sorted(candidates)[-1]
    d, mo, y = latest.split(".")
    return date(int(y), int(mo), int(d))


def _extract_pos_number(pdf_path: Path) -> str:
    """Return the POS number found inside the PDF, falling back to a
    pattern parsed from the filename if the PDF body does not carry it."""
    text_all = "\n".join(p.get_text() for p in fitz.open(pdf_path))
    # Filename first — the canonical ``OISCRO-NNNN-YY`` form is always
    # present there; PDF bodies occasionally drop the ``-YY`` suffix or
    # insert a stray space (typos on the supplier side).
    m = _POS_NUM_RE.search(pdf_path.stem) or _POS_NUM_RE.search(text_all)
    if m is None:
        raise ValueError(f"No POS number found in {pdf_path.name}")
    return _normalize_pos_number(m)


async def _backfill(
    db: AsyncSession,
    pdf_dir: Path,
    *,
    dry_run: bool,
    force: bool,
) -> tuple[int, int, list[str]]:
    """Returns (updated_count, skipped_count, missing_pos_numbers)."""
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    updated = 0
    skipped = 0
    missing: list[str] = []

    for pdf in pdfs:
        try:
            pos_num = _extract_pos_number(pdf)
            iss = _extract_issuance(pdf)
        except Exception as exc:
            print(f"  ! {pdf.name}: parse failed — {exc}")
            continue

        if iss is None:
            print(f"  ! {pdf.name}: no issuance date found in PDF")
            continue

        row = (
            await db.execute(
                text(
                    "SELECT consignment_id, issuance_date "
                    "FROM consignment_pos "
                    "WHERE pos_number = :n AND deleted_at IS NULL"
                ),
                {"n": pos_num},
            )
        ).first()

        if row is None:
            missing.append(pos_num)
            print(f"  ? {pos_num}: no consignment_pos row in DB — skipped")
            continue

        if row.issuance_date is not None and not force:
            skipped += 1
            print(
                f"  · {pos_num}: already has issuance_date="
                f"{row.issuance_date} — skipped (use --force to overwrite)"
            )
            continue

        if dry_run:
            print(f"  ~ {pos_num}: would set issuance_date={iss}")
            updated += 1
            continue

        await db.execute(
            text(
                "UPDATE consignment_pos SET issuance_date = :d "
                "WHERE pos_number = :n AND deleted_at IS NULL"
            ),
            {"d": iss, "n": pos_num},
        )
        updated += 1
        print(f"  ✓ {pos_num}: issuance_date={iss}")

    return updated, skipped, missing


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite issuance_date even if already populated.",
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=Path("/tmp/pos_pdfs"),  # noqa: S108 — documented CLI default, override via --pdf-dir
        help="Directory containing POS PDFs (default /tmp/pos_pdfs).",
    )
    args = parser.parse_args()

    if not args.pdf_dir.is_dir():
        print(f"ERROR: pdf-dir not found: {args.pdf_dir}", file=sys.stderr)
        sys.exit(2)

    print(
        f"backfill_pos_issuance — pdf_dir={args.pdf_dir}, "
        f"dry_run={args.dry_run}, force={args.force}"
    )

    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        updated, skipped, missing = await _backfill(
            db, args.pdf_dir, dry_run=args.dry_run, force=args.force
        )
        if not args.dry_run:
            await db.commit()
    await engine.dispose()

    print(
        f"\nsummary: updated={updated} skipped={skipped} "
        f"missing_in_db={len(missing)}"
    )
    if missing:
        print(f"  POS numbers without a DB row: {', '.join(missing)}")


if __name__ == "__main__":
    asyncio.run(main())
