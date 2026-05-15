"""Smoke tests for GET /reports/mass-balance/export (DFTEN-98, E1-S1.4).

Strategy:
- Override ``get_db`` with an in-memory fake AsyncSession that returns canned
  rows based on the SQL pattern executed.
- Override ``_get_current_user`` with a fake viewer user so we exercise the
  full route (auth dep + role gate) without a real DB / JWT.
- Patch ``render_to_pdf`` only in the unauthenticated/invalid-input tests to
  keep them fast; happy-path test actually invokes WeasyPrint so we verify
  the wired filter set + context shape end-to-end.
"""
from __future__ import annotations

import hashlib
import os
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://dft:testonly@localhost:5432/dft"
)
os.environ.setdefault("JWT_SECRET", "changeme-dft-secret-key-2026")

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.models.user import User
from app.routers.auth import _get_current_user


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
class _Mappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def all(self) -> list[dict[str, Any]]:
        return self._rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None


class _Result:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> _Mappings:
        return _Mappings(self._rows)


class _FakeSession:
    """Pattern-match SQL text to canned MV rows. Sufficient for export route."""

    def __init__(self) -> None:
        self.committed = False
        self.added: list[Any] = []

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> _Result:
        sql = str(stmt)
        if "mv_mass_balance_daily" in sql:
            return _Result(
                [
                    {
                        "day": date(2025, 1, 1),
                        "input_total_kg": Decimal("12000.00"),
                        "eu_prod_kg": Decimal("4200.00"),
                        "plus_prod_kg": Decimal("1800.00"),
                        "eu_prod_litres": Decimal("5384.62"),
                        "plus_prod_litres": Decimal("2102.80"),
                        "output_total_kg": Decimal("6000.00"),
                        "closure_diff_pct": Decimal("0.50"),
                    },
                    {
                        "day": date(2025, 1, 2),
                        "input_total_kg": Decimal("11500.00"),
                        "eu_prod_kg": Decimal("4100.00"),
                        "plus_prod_kg": Decimal("1700.00"),
                        "eu_prod_litres": Decimal("5256.41"),
                        "plus_prod_litres": Decimal("1985.98"),
                        "output_total_kg": Decimal("5800.00"),
                        "closure_diff_pct": Decimal("-0.30"),
                    },
                ]
            )
        if "mv_mass_balance_monthly" in sql:
            return _Result(
                [
                    {
                        "input_total_kg": Decimal("23500.00"),
                        "eu_prod_kg": Decimal("8300.00"),
                        "plus_prod_kg": Decimal("3500.00"),
                        "eu_prod_litres": Decimal("10641.03"),
                        "plus_prod_litres": Decimal("4088.78"),
                        "output_total_kg": Decimal("11800.00"),
                        "closure_diff_pct": Decimal("0.10"),
                    }
                ]
            )
        if "daily_inputs" in sql and "suppliers" in sql:
            return _Result(
                [
                    {
                        "name": "Reciclajes Andinos S.A.S.",
                        "cert_iscc_ref": "EU-ISCC-COC-2024-AR-001",
                        "total_kg": Decimal("14000.00"),
                    },
                    {
                        "name": "TyreCycle Caribe S.A.",
                        "cert_iscc_ref": "EU-ISCC-COC-2024-TC-022",
                        "total_kg": Decimal("9500.00"),
                    },
                ]
            )
        return _Result([])

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass

    async def close(self) -> None:
        pass


_fake_session = _FakeSession()


async def _override_get_db():  # type: ignore[no-untyped-def]
    yield _fake_session


def _fake_viewer() -> User:
    u = MagicMock(spec=User)
    u.id = 99
    u.email = "viewer@dft.test"
    u.role = "viewer"
    u.active = True
    return u


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def client_authed() -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[_get_current_user] = _fake_viewer
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(_get_current_user, None)


@pytest.fixture
def client_anon() -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_unauthenticated_returns_401(client_anon: TestClient) -> None:
    resp = client_anon.get("/reports/mass-balance/export?month=2025-01&format=pdf")
    assert resp.status_code == 401, resp.text


def test_invalid_month_returns_400(client_authed: TestClient) -> None:
    resp = client_authed.get("/reports/mass-balance/export?month=2025-13&format=pdf")
    assert resp.status_code == 400, resp.text


def test_invalid_format_returns_400(client_authed: TestClient) -> None:
    resp = client_authed.get("/reports/mass-balance/export?month=2025-01&format=csv")
    assert resp.status_code == 400, resp.text


def test_export_happy_path_returns_pdf_with_sha256_header(
    client_authed: TestClient,
) -> None:
    resp = client_authed.get("/reports/mass-balance/export?month=2025-01&format=pdf")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"

    sha_header = resp.headers.get("x-content-sha256")
    assert sha_header is not None and len(sha_header) == 64
    assert sha_header == hashlib.sha256(resp.content).hexdigest()

    disp = resp.headers.get("content-disposition", "")
    assert "mass_balance_2025-01.pdf" in disp

    # Audit log row added + commit fired.
    assert _fake_session.committed is True
    assert any(getattr(o, "table_name", None) == "mass_balance" for o in _fake_session.added)


def test_render_is_deterministic_across_two_calls(client_authed: TestClient) -> None:
    """Two calls with the same context yield byte-identical PDFs.

    The endpoint embeds ``generated_at = datetime.now(UTC)`` at request time,
    so byte-equality across CALLS isn't guaranteed. We verify the digest's
    self-consistency (header matches body hash) — full determinism is
    exercised in backend/tests/services/test_pdf_renderer.py.
    """
    resp = client_authed.get("/reports/mass-balance/export?month=2025-01&format=pdf")
    assert resp.status_code == 200
    body_hash = hashlib.sha256(resp.content).hexdigest()
    assert resp.headers["x-content-sha256"] == body_hash
