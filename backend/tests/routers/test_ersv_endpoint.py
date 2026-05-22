"""Smoke tests for /ersv/{ersv_number}{,/html,/pdf} (W2-RENDER).

Strategy mirrors test_reports_export.py:
- Override get_db with an in-memory fake AsyncSession returning canned rows.
- Override _get_current_user with a fake viewer user so auth dep passes.
- Use TestClient to exercise the full FastAPI stack (validation + audit).
"""

from __future__ import annotations

import os
from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

if TYPE_CHECKING:
    from collections.abc import Iterator

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
# Fake row + session
# ---------------------------------------------------------------------------
def _row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": 21359,
        "entry_date": date(2025, 2, 19),
        "entry_time": time(9, 45),
        "supplier_id": 5,
        "car_kg": Decimal("0.000"),
        "truck_kg": Decimal("24580.000"),
        "special_kg": Decimal("0.000"),
        "total_input_kg": Decimal("24580.000"),
        "notes": None,
        "rectified_at": None,
        "rectification_reason": None,
        "original_values": {"ersv_regen_migration": "0017"},
        "updated_at": datetime(2026, 5, 22, 10, 0, 0),
        "ersv_number": "00042/25",
        "supplier_name": "PyrCom Andina S.A.S.",
        "supplier_code": "PYRCOM",
        "supplier_country": "CO",
        "cert_iscc_ref": "EU-ISCC-COC-2024-PYRCOM-001",
        "cert_valid_until": date(2026, 12, 31),
    }
    base.update(overrides)
    return base


class _Mappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def all(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None


class _Result:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> _Mappings:
        return _Mappings(self._rows)


class _FakeSession:
    """Single-row store; routes call execute() once for the SELECT."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.added: list[Any] = []
        self.committed = False

    def set_rows(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    async def execute(
        self, _stmt: Any, params: dict[str, Any] | None = None
    ) -> _Result:
        del params
        return _Result(self.rows)

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
@pytest.fixture(autouse=True)
def reset_session() -> Iterator[None]:
    _fake_session.rows = []
    _fake_session.added = []
    _fake_session.committed = False
    yield


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
    resp = client_anon.get("/ersv/00042%2F25")
    assert resp.status_code == 401, resp.text


def test_invalid_ersv_format_returns_400(client_authed: TestClient) -> None:
    """Wrong format (e.g. missing slash, wrong digit counts) → 400."""
    _fake_session.set_rows([_row()])
    # 2 digits before slash is below the 3-digit minimum.
    resp = client_authed.get("/ersv/12%2F25")
    assert resp.status_code == 400, resp.text
    assert "ersv_number must match" in resp.json()["detail"]


def test_not_found_returns_404(client_authed: TestClient) -> None:
    _fake_session.set_rows([])
    resp = client_authed.get("/ersv/99999%2F25")
    assert resp.status_code == 404, resp.text


def test_json_metadata_happy_path(client_authed: TestClient) -> None:
    _fake_session.set_rows([_row()])
    resp = client_authed.get("/ersv/00042%2F25")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ersv_number"] == "00042/25"
    assert data["daily_input_id"] == 21359
    assert data["supplier_code"] == "PYRCOM"
    assert data["is_regenerated"] is True
    assert data["cert_iscc_ref"] == "EU-ISCC-COC-2024-PYRCOM-001"
    # JSON route does NOT audit — added list must stay empty.
    assert _fake_session.added == []
    assert _fake_session.committed is False


def test_html_returns_text_html_with_etag(client_authed: TestClient) -> None:
    _fake_session.set_rows([_row()])
    resp = client_authed.get("/ersv/00042%2F25/html")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/html")
    etag = resp.headers.get("etag")
    assert etag is not None and etag.startswith('W/"')
    cache = resp.headers.get("cache-control")
    assert cache == "private, max-age=0, must-revalidate"
    # HTML route does NOT audit.
    assert _fake_session.added == []
    assert _fake_session.committed is False


def test_html_304_when_etag_matches(client_authed: TestClient) -> None:
    _fake_session.set_rows([_row()])
    first = client_authed.get("/ersv/00042%2F25/html")
    etag = first.headers["etag"]

    second = client_authed.get(
        "/ersv/00042%2F25/html", headers={"If-None-Match": etag}
    )
    assert second.status_code == 304, second.text
    # 304 body MUST be empty per HTTP spec.
    assert second.content == b""
    assert second.headers.get("etag") == etag


def test_pdf_returns_pdf_with_no_store_and_audit(client_authed: TestClient) -> None:
    _fake_session.set_rows([_row()])
    resp = client_authed.get("/ersv/00042%2F25/pdf")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"
    assert resp.headers.get("cache-control") == "no-store"
    sha = resp.headers.get("x-content-sha256")
    assert sha is not None and len(sha) == 64
    disp = resp.headers.get("content-disposition", "")
    assert "ersv_00042_25.pdf" in disp

    # PDF route writes a single audit row with action='insert'.
    assert _fake_session.committed is True
    audit_rows = [
        o for o in _fake_session.added if getattr(o, "table_name", None) == "ersv"
    ]
    assert len(audit_rows) == 1
    audit = audit_rows[0]
    assert audit.action == "insert"
    assert audit.changed_by == 99
    assert audit.record_id == 21359
    payload = audit.new_values
    assert payload["kind"] == "ERSV_PDF_EXPORT"
    assert payload["ersv_number"] == "00042/25"
    assert payload["sha256"] == sha
    assert payload["page_count"] >= 1
    assert payload["size_bytes"] == len(resp.content)


def test_jan_3digit_path_param_accepted(client_authed: TestClient) -> None:
    """Jan 2025 frozen format ``153/25`` must validate (3-digit numerator)."""
    jan_row = _row(
        id=21000,
        entry_date=date(2025, 1, 14),
        ersv_number="153/25",
        original_values=None,
    )
    _fake_session.set_rows([jan_row])
    resp = client_authed.get("/ersv/153%2F25")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ersv_number"] == "153/25"
    assert data["is_regenerated"] is False
