"""Tests for ersv_renderer service (W2-RENDER).

Covers:
- known number → row fetched, PDF bytes valid (%PDF-).
- unknown number → ErsvNotFoundError.
- Jan 2025 frozen row (3-digit) → no regen watermark.
- Feb-Aug 2025 regen row (5-digit + 0017 marker) → regen banner present.
- ETag is stable across two consecutive HTML renders.
- Decimal kg values round-trip into the rendered HTML (formatting).
- Multi-match warning fires when the LIMIT 2 query returns 2 rows.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://dft:testonly@localhost:5432/dft"
)
os.environ.setdefault("JWT_SECRET", "changeme-dft-secret-key-2026")

import pytest

from app.services.ersv_renderer import (
    ErsvNotFoundError,
    fetch_ersv_row,
    is_regenerated,
    render_ersv_to_html,
    render_ersv_to_pdf,
)


# ---------------------------------------------------------------------------
# Fake AsyncSession
# ---------------------------------------------------------------------------
def _row(**overrides: Any) -> dict[str, Any]:
    """Baseline row matching _FETCH_SQL projection — overrides applied last."""
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
        "original_values": None,
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
    """Returns whichever rows are seeded for the next execute() call."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.last_params: dict[str, Any] | None = None

    async def execute(
        self, _stmt: Any, params: dict[str, Any] | None = None
    ) -> _Result:
        self.last_params = params
        return _Result(self.rows)


# ---------------------------------------------------------------------------
# Tests — fetch / classification
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("marker", "expected"),
    [
        ({"ersv_regen_migration": "0017"}, True),
        ({"ersv_regen_migration": "0016"}, False),
        ({}, False),
        (None, False),
        ("not a dict", False),
    ],
)
def test_is_regenerated_marker(marker: Any, expected: bool) -> None:
    assert is_regenerated(marker) is expected


def test_fetch_ersv_row_unknown_raises() -> None:
    session = _FakeSession(rows=[])
    with pytest.raises(ErsvNotFoundError) as exc:
        asyncio.run(fetch_ersv_row(session, "99999/25"))  # type: ignore[arg-type]
    assert exc.value.ersv_number == "99999/25"


def test_fetch_ersv_row_known_returns_first(caplog: pytest.LogCaptureFixture) -> None:
    session = _FakeSession(rows=[_row()])
    caplog.set_level(logging.WARNING)
    out = asyncio.run(fetch_ersv_row(session, "00042/25"))  # type: ignore[arg-type]
    assert out["ersv_number"] == "00042/25"
    assert out["supplier_code"] == "PYRCOM"
    # No multi-match warning when only one row matches.
    assert "Multiple daily_inputs rows match" not in caplog.text


def test_fetch_ersv_row_multi_match_logs_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Two rows back → first wins, warning logged."""
    first = _row(id=21359, supplier_code="PYRCOM")
    second = _row(id=21396, supplier_code="EFFICIEN", supplier_id=6)
    session = _FakeSession(rows=[first, second])
    caplog.set_level(logging.WARNING, logger="app.services.ersv_renderer")
    out = asyncio.run(fetch_ersv_row(session, "00042/25"))  # type: ignore[arg-type]
    assert out["id"] == 21359
    assert "Multiple daily_inputs rows match" in caplog.text


# ---------------------------------------------------------------------------
# Tests — HTML rendering
# ---------------------------------------------------------------------------
def test_render_html_known_row_renders_kg_values() -> None:
    session = _FakeSession(rows=[_row()])
    artefact = asyncio.run(render_ersv_to_html(session, "00042/25"))  # type: ignore[arg-type]
    assert artefact.ersv_number == "00042/25"
    assert artefact.daily_input_id == 21359
    # 24 580.000 kg → formatted EU style.
    assert "24 580,00 kg" in artefact.html
    assert artefact.etag.startswith('W/"')
    assert len(artefact.etag) == len('W/""') + 16


def test_render_html_jan_3digit_no_watermark() -> None:
    """Jan 2025 row (frozen, no 0017 marker) MUST NOT show the regen banner."""
    jan_row = _row(
        id=21000,
        entry_date=date(2025, 1, 14),
        ersv_number="153/25",
        original_values=None,
    )
    session = _FakeSession(rows=[jan_row])
    artefact = asyncio.run(render_ersv_to_html(session, "153/25"))  # type: ignore[arg-type]
    assert "RECONSTRUCTED DOCUMENT" not in artefact.html
    assert 'class="regen-banner"' not in artefact.html
    assert 'class="sig-overlay"' not in artefact.html


def test_render_html_regen_row_shows_watermark() -> None:
    """Feb-Aug 2025 row carrying the 0017 marker MUST show the banner + overlay."""
    regen_row = _row(
        original_values={
            "ersv_regen_migration": "0017",
            "ersv_number_before_0017": None,
        }
    )
    session = _FakeSession(rows=[regen_row])
    artefact = asyncio.run(render_ersv_to_html(session, "00042/25"))  # type: ignore[arg-type]
    assert "RECONSTRUCTED DOCUMENT" in artefact.html
    assert 'class="regen-banner"' in artefact.html
    assert 'class="sig-overlay"' in artefact.html
    assert "UNSIGNED" in artefact.html
    assert "0017" in artefact.html
    assert "2026-05-22" in artefact.html


def test_render_html_etag_is_stable_across_renders() -> None:
    """Two renders of the same row produce the same ETag (stable across calls)."""
    session = _FakeSession(rows=[_row()])
    a1 = asyncio.run(render_ersv_to_html(session, "00042/25"))  # type: ignore[arg-type]
    a2 = asyncio.run(render_ersv_to_html(session, "00042/25"))  # type: ignore[arg-type]
    assert a1.etag == a2.etag


# ---------------------------------------------------------------------------
# Tests — PDF rendering (smoke)
# ---------------------------------------------------------------------------
def test_render_pdf_returns_pdf_bytes() -> None:
    """Smoke: PDF starts with %PDF, sha256 length 64, ≥1 page."""
    session = _FakeSession(rows=[_row()])
    artefact = asyncio.run(render_ersv_to_pdf(session, "00042/25"))  # type: ignore[arg-type]
    assert artefact.pdf_bytes[:4] == b"%PDF"
    assert len(artefact.pdf_sha256) == 64
    assert artefact.page_count >= 1
    assert artefact.pdf_path is None  # No output_path passed → tmpdir cleaned up.


def test_render_pdf_unknown_raises() -> None:
    session = _FakeSession(rows=[])
    with pytest.raises(ErsvNotFoundError):
        asyncio.run(render_ersv_to_pdf(session, "99999/25"))  # type: ignore[arg-type]
