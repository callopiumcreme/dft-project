"""Tests for the UTB transload PDF streaming route.

Story: DFTEN-166 (E8-G1). Covers:
  - 200 OK + application/pdf content-type when the leg row exists and
    the PDF is present on disk (uses c-1 DEL-CRW-2025-2 / UTB-2025-Q3-CONSOLIDATED).
  - 400 when the ref shape is invalid (path-traversal defence at URL layer).
  - 404 when the ref is well-formed but no matching leg row exists.

The test uses ``monkeypatch`` to point ``_TRANSLOAD_ROOT`` at the repo's
local ``data/transload`` directory because the streaming code resolves
paths against that root (default ``/data/transload`` is the in-container
bind-mount; host pytest needs the host path).
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.session import get_db
from app.main import app
from app.routers import consignments as consignments_router


_REPO_ROOT = Path(__file__).resolve().parents[2]
_TRANSLOAD_HOST_ROOT = _REPO_ROOT / "data" / "transload"

_engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    _engine, expire_on_commit=False
)


async def _override_get_db() -> AsyncIterator[AsyncSession]:
    async with _factory() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def transload_root(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ``_TRANSLOAD_ROOT`` at the host ``data/transload`` directory.

    The route module reads the env at import time, so to redirect it for
    host-side pytest we patch the module attribute directly.
    """
    monkeypatch.setattr(
        consignments_router, "_TRANSLOAD_ROOT", _TRANSLOAD_HOST_ROOT
    )
    return _TRANSLOAD_HOST_ROOT


# ---------------------------------------------------------------------------
# 200 OK happy path — c-1 / UTB-2025-Q3-CONSOLIDATED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transload_pdf_stream_200(
    client: AsyncClient,
    admin_headers: dict[str, str],
    transload_root: Path,
) -> None:
    """GET /consignments/1/transload/UTB-2025-Q3-CONSOLIDATED.pdf → 200 PDF."""
    pdf_on_disk = transload_root / "c-1" / "UTB-2025-Q3-CONSOLIDATED.pdf"
    if not pdf_on_disk.is_file():
        pytest.skip(
            f"Transload PDF artefact missing at {pdf_on_disk}; "
            "run scripts/render_transload_consolidated.py first."
        )

    resp = await client.get(
        "/consignments/1/transload/UTB-2025-Q3-CONSOLIDATED.pdf",
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    # Default disposition is inline so the popup iframe renders the PDF.
    assert "inline" in resp.headers.get("content-disposition", "")
    # First bytes of a PDF are b"%PDF-"; sanity-check the streamed body.
    assert resp.content.startswith(b"%PDF-"), "Response body does not look like a PDF"


@pytest.mark.asyncio
async def test_transload_pdf_stream_download_disposition(
    client: AsyncClient,
    admin_headers: dict[str, str],
    transload_root: Path,
) -> None:
    """``?download=1`` flips Content-Disposition from inline to attachment."""
    pdf_on_disk = transload_root / "c-1" / "UTB-2025-Q3-CONSOLIDATED.pdf"
    if not pdf_on_disk.is_file():
        pytest.skip("Transload PDF artefact missing on disk.")

    resp = await client.get(
        "/consignments/1/transload/UTB-2025-Q3-CONSOLIDATED.pdf?download=1",
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    assert "attachment" in resp.headers.get("content-disposition", "")


# ---------------------------------------------------------------------------
# 400 — path-traversal defence (URL layer)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transload_pdf_rejects_invalid_ref_shape(
    client: AsyncClient,
    admin_headers: dict[str, str],
    transload_root: Path,
) -> None:
    """Refs containing slashes / dots / lowercase must be rejected (400).

    The regex anchors to ``[A-Z0-9]+(?:-[A-Z0-9]+){0,8}`` — any attempt to
    inject ``../`` or absolute paths breaks the format check before
    Path.resolve() runs.
    """
    bad_refs = [
        "../etc/passwd",
        "UTB/../../../etc/passwd",
        "utb-2025-q3-consolidated",  # lowercase — must be uppercase
        "UTB.2025.Q3",  # dots not allowed
        "UTB 2025 Q3",  # whitespace not allowed
    ]
    for bad in bad_refs:
        resp = await client.get(
            f"/consignments/1/transload/{bad}.pdf",
            headers=admin_headers,
        )
        # 400 from our regex check, OR 404 from FastAPI routing if the URL
        # cannot match the route at all (e.g. slashes break the path param).
        assert resp.status_code in (400, 404), (
            f"Expected 400/404 for bad ref {bad!r}, got {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# 404 — well-formed ref but no matching leg row
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transload_pdf_unknown_ref_returns_404(
    client: AsyncClient,
    admin_headers: dict[str, str],
    transload_root: Path,
) -> None:
    """Well-formed but unknown reference → 404."""
    resp = await client.get(
        "/consignments/1/transload/UTB-2099-Q9-NEVERWAS.pdf",
        headers=admin_headers,
    )
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# 401 — no auth header
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transload_pdf_requires_auth(
    client: AsyncClient,
    transload_root: Path,
) -> None:
    """Without an Authorization header the route returns 401."""
    resp = await client.get(
        "/consignments/1/transload/UTB-2025-Q3-CONSOLIDATED.pdf",
    )
    assert resp.status_code == 401, resp.text
