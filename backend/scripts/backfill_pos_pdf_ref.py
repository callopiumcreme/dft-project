"""Backfill ``consignment_pos.pdf_ref`` from ``gdrive:…`` to local paths.

Closes gap **G6** of ``docs/gap-analysis-2026-05-25.md``. The DB still
carries historical ``gdrive:DFT_2025/…`` references — violating the
**NO Drive runtime** rule and breaking the auth-gated PoS stream route.
This script:

1. Selects every active ``consignment_pos`` row with
   ``pdf_ref LIKE 'gdrive:%'``.
2. Computes a local relative path
   ``c-<consignment_id>/<basename(pdf_ref)>``.
3. Verifies the file exists under ``/data/pos_documents`` (refuses to
   rewrite a row whose file is not on disk — keeps the historical
   ``gdrive:`` ref instead of silently breaking the stream route).
4. UPDATEs ``pdf_ref`` keyed on the **business key**
   ``(consignment_id, pos_number, deleted_at IS NULL)``. Auto-increment
   ids are never used (cf. row-id portability rule).

The script is idempotent: a second run finds no ``gdrive:%`` rows and
returns silently. ``--dry-run`` prints the planned UPDATEs without
touching the DB.

Usage (inside backend container):

    docker exec dft-project_backend_1 \\
        python scripts/backfill_pos_pdf_ref.py --dry-run
    docker exec dft-project_backend_1 \\
        python scripts/backfill_pos_pdf_ref.py

Bind-mount required (added in same commit to ``docker-compose.yml``):

    ./data/pos_documents:/data/pos_documents:ro
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dft:dftdev_2026@db:5432/dft",
)
POS_ROOT = Path(os.environ.get("POS_ROOT", "/data/pos_documents"))


SELECT_STALE_SQL = text("""
    SELECT consignment_id, pos_number, pdf_ref
      FROM consignment_pos
     WHERE deleted_at IS NULL
       AND pdf_ref LIKE 'gdrive:%'
     ORDER BY consignment_id, pos_number
""")


UPDATE_REF_SQL = text("""
    UPDATE consignment_pos
       SET pdf_ref = :new_ref
     WHERE consignment_id = :consignment_id
       AND pos_number = :pos_number
       AND deleted_at IS NULL
""")


def _local_ref(consignment_id: int, gdrive_ref: str) -> str:
    """Map ``gdrive:DFT_2025/<folder>/<file>.pdf`` → ``c-<id>/<file>.pdf``."""
    # Strip the ``gdrive:`` scheme and any leading folder structure; the
    # local layout collapses everything to one folder per consignment.
    basename = gdrive_ref.rsplit("/", 1)[-1]
    return f"c-{consignment_id}/{basename}"


async def _run(dry_run: bool) -> None:
    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    root = POS_ROOT.resolve()

    async with SessionLocal() as session:
        rows = (await session.execute(SELECT_STALE_SQL)).all()
        if not rows:
            print("no gdrive: rows left — nothing to do.")
            await engine.dispose()
            return

        print(f"found {len(rows)} gdrive: rows to rewrite (root = {root})")
        rewrites: list[tuple[int, str, str]] = []
        missing: list[tuple[int, str, str]] = []

        for r in rows:
            new_ref = _local_ref(r.consignment_id, r.pdf_ref)
            local = (root / new_ref).resolve()
            try:
                local.relative_to(root)
            except ValueError:
                print(
                    f"  ✗ {r.consignment_id}/{r.pos_number}: "
                    f"computed path escapes root — skipped"
                )
                continue
            if not local.is_file():
                missing.append((r.consignment_id, r.pos_number, new_ref))
                continue
            rewrites.append((r.consignment_id, r.pos_number, new_ref))

        for cid, pn, new_ref in rewrites:
            print(f"  ✔ {cid}/{pn} → {new_ref}")
        for cid, pn, new_ref in missing:
            print(f"  ✗ {cid}/{pn} → {new_ref}  (MISSING on disk — skipped)")

        if dry_run:
            print(f"[dry-run] would UPDATE {len(rewrites)} rows, skip {len(missing)}")
            await engine.dispose()
            return

        if not rewrites:
            print("nothing to write (all files missing).")
            await engine.dispose()
            return

        for cid, pn, new_ref in rewrites:
            await session.execute(
                UPDATE_REF_SQL,
                {
                    "consignment_id": cid,
                    "pos_number": pn,
                    "new_ref": new_ref,
                },
            )
        await session.commit()
        print(
            f"done: {len(rewrites)} rows rewritten, "
            f"{len(missing)} left as gdrive: (PDF missing on disk)"
        )

    await engine.dispose()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    asyncio.run(_run(args.dry_run))


if __name__ == "__main__":
    main()
