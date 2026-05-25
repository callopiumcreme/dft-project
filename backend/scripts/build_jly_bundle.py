"""Server-side concat of OIS-INV commercial invoices into the JLY bundle.

Closes gap **G2** of ``docs/gap-analysis-2026-05-25.md``. The Crown Oil
RTFO-310825 bundle references "JLY001-JLY020" — a single multi-page PDF
bundle of the 20 OIS-INV commercial invoices that map 1:1 to the
OisteBio Purchase Order IDs ``OIST-JLY001`` … ``OIST-JLY020`` embedded
in each invoice's metadata.

What this script does
---------------------
1. Globs ``INV_OIS-INV*.pdf`` under ``data/invoices/c-<id>/`` (host)
   = ``/data/invoices/c-<id>/`` (container).
2. Concatenates them in lexical order via ``pypdf.PdfWriter``.
3. Writes ``data/delivery_uk/c-<id>/JLY001-020-bundle.pdf`` (target
   directory created if needed).
4. UPDATEs ``shipment_leg.pdf_ref`` keyed on the **business key**
   ``(consignment_id, leg_type='delivery_uk', deleted_at IS NULL)`` —
   never on auto-increment id (row-id portability rule).
5. Prints sha256 of the output for the audit trail.

Idempotency:
- Re-running overwrites the bundle file (pypdf output is deterministic
  given the same inputs in the same order, modulo embedded mod-dates).
- The UPDATE statement sets the same ``pdf_ref`` on each run.

Usage (inside backend container):

    docker exec dft-project_backend_1 \\
        python scripts/build_jly_bundle.py --consignment-id 1 --dry-run
    docker exec dft-project_backend_1 \\
        python scripts/build_jly_bundle.py --consignment-id 1
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from pypdf import PdfReader, PdfWriter  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dft:dftdev_2026@db:5432/dft",
)
INVOICES_ROOT = Path(os.environ.get("INVOICES_ROOT", "/data/invoices"))
DELIVERY_UK_ROOT = Path(os.environ.get("DELIVERY_UK_ROOT", "/data/delivery_uk"))
BUNDLE_FILENAME = "JLY001-020-bundle.pdf"


UPDATE_LEG_SQL = text("""
    UPDATE shipment_leg
       SET pdf_ref = :new_ref,
           updated_at = now()
     WHERE consignment_id = :consignment_id
       AND leg_type = 'delivery_uk'
       AND deleted_at IS NULL
    RETURNING id, document_ref, pdf_ref
""")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _concat(src_dir: Path, target: Path) -> tuple[list[Path], int]:
    """Concat every ``INV_OIS-INV*.pdf`` under *src_dir* into *target*.

    Returns (sources, total_pages). Raises if no sources found.
    """
    sources = sorted(src_dir.glob("INV_OIS-INV*.pdf"))
    if not sources:
        raise FileNotFoundError(f"no INV_OIS-INV*.pdf under {src_dir}")

    writer = PdfWriter()
    total_pages = 0
    for src in sources:
        reader = PdfReader(str(src))
        for page in reader.pages:
            writer.add_page(page)
            total_pages += 1

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as fp:
        writer.write(fp)
    return sources, total_pages


async def _link_leg(consignment_id: int, new_ref: str) -> None:
    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        result = await session.execute(
            UPDATE_LEG_SQL,
            {"consignment_id": consignment_id, "new_ref": new_ref},
        )
        rows = result.fetchall()
        if not rows:
            print(
                f"⚠ no delivery_uk leg found for consignment_id={consignment_id} "
                "— bundle written but no leg linked"
            )
        for r in rows:
            print(
                f"✔ shipment_leg id={r.id} ({r.document_ref}) "
                f"pdf_ref={r.pdf_ref}"
            )
        await session.commit()
    await engine.dispose()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--consignment-id",
        type=int,
        required=True,
        help="consignment.id whose delivery_uk leg gets the bundle linked",
    )
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    src_dir = INVOICES_ROOT / f"c-{args.consignment_id}"
    target = DELIVERY_UK_ROOT / f"c-{args.consignment_id}" / BUNDLE_FILENAME
    new_ref = f"c-{args.consignment_id}/{BUNDLE_FILENAME}"

    if not src_dir.is_dir():
        sys.exit(f"source dir missing: {src_dir}")

    if args.dry_run:
        sources = sorted(src_dir.glob("INV_OIS-INV*.pdf"))
        if not sources:
            sys.exit(f"no INV_OIS-INV*.pdf under {src_dir}")
        print(f"[dry-run] would concat {len(sources)} files from {src_dir}:")
        for s in sources:
            print(f"  - {s.name}")
        print(f"[dry-run] would write   {target}")
        print(
            "[dry-run] would UPDATE shipment_leg SET pdf_ref="  # noqa: S608
            f"'{new_ref}' WHERE consignment_id={args.consignment_id} "
            "AND leg_type='delivery_uk' AND deleted_at IS NULL"
        )
        return

    sources, total_pages = _concat(src_dir, target)
    sha = _sha256(target)
    size = target.stat().st_size
    print(
        f"✔ wrote {target} ({size} bytes, {total_pages} pages from "
        f"{len(sources)} sources)"
    )
    print(f"  sha256 = {sha}")

    asyncio.run(_link_leg(args.consignment_id, new_ref))


if __name__ == "__main__":
    main()
