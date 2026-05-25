"""CLI wrapper for ``app.services.rtfo_bundle.build_verifier_bundle``.

Offline / smoke-test entry point — closes DFTEN-151 (E5-S5.6) without
needing the HTTP layer. Lets the verifier bundle be regenerated for any
consignment id from inside the backend container, with the same code
path the eventual POST /reports/verifier-bundle endpoint will call.

Usage (inside backend container)::

    docker exec dft-project_backend_1 \\
        python scripts/build_verifier_bundle.py --consignment-id 1
    docker exec dft-project_backend_1 \\
        python scripts/build_verifier_bundle.py --consignment-id 1 \\
            --out-root /tmp/verifier_bundles --generated-at 2026-05-25T00:00:00Z
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.services.rtfo_bundle import (  # noqa: E402
    VerifierBundleError,
    build_verifier_bundle,
)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dft:dftdev_2026@db:5432/dft",
)


async def _run(consignment_id: int, out_root: Path, gen_at: datetime | None) -> None:
    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with SessionLocal() as session:
            result = await build_verifier_bundle(
                session, consignment_id, out_root, generated_at=gen_at
            )
    finally:
        await engine.dispose()

    print(f"✔ verifier bundle for consignment_id={result.consignment_id}")
    print(f"  bundle PDF : {result.bundle_pdf_path}")
    print(
        f"  size       : {result.bundle_pdf_size_bytes} bytes, "
        f"{result.bundle_pdf_page_count} pages"
    )
    print(f"  sha256     : {result.bundle_pdf_sha256}")
    print(f"  ZIP        : {result.zip_path}")
    print(f"  ZIP size   : {result.zip_size_bytes} bytes")
    print(f"  ZIP sha256 : {result.zip_sha256}")
    print(f"  MANIFEST   : {result.manifest_path}")
    print(f"  generated  : {result.generated_at.isoformat()}")
    print("  sections   :")
    for s in result.sections:
        print(
            f"    - {s.pdf_path.name}: {s.pdf_size_bytes} bytes, "
            f"{s.page_count} pages, sha {s.pdf_sha256[:12]}…"
        )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--consignment-id", type=int, required=True)
    p.add_argument(
        "--out-root",
        type=Path,
        default=Path(os.environ.get("VERIFIER_BUNDLES_ROOT", "/tmp/verifier_bundles")),  # noqa: S108
        help="output root (default /tmp/verifier_bundles inside container)",
    )
    p.add_argument(
        "--generated-at",
        type=str,
        default=None,
        help="ISO-8601 UTC timestamp to embed in the bundle (default: now)",
    )
    args = p.parse_args()

    gen_at: datetime | None = None
    if args.generated_at:
        # Accept both "Z" and "+00:00" suffixes.
        s = args.generated_at.replace("Z", "+00:00")
        gen_at = datetime.fromisoformat(s).astimezone(UTC)

    try:
        asyncio.run(_run(args.consignment_id, args.out_root, gen_at))
    except VerifierBundleError as e:
        sys.exit(f"FAIL: {e}")


if __name__ == "__main__":
    main()
