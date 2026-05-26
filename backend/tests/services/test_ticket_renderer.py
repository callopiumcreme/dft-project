"""Tests for ``app.services.ticket_renderer`` — Round-3 N6 / N7 marker
on the báscula operator field (PESADO POR).

Plan §2 Step 2 binds the marker to all personal-data fields. The
weigher value lives in ticket_renderer (not in ersv_pool), so this
test file is the per-file divergence guard recorded in the Step 2
commit body.

Coverage:
- in-window date → ``weigher == PAPER_RECORD_MARKER`` and the marker
  also appears on driver / cédula / placa via the pool pass-through.
- in-window text preview contains the marker on the PESADO POR line.
- out-of-window date → ``weigher`` is one of ``WEIGHERS``, never the
  marker; preview shows the deterministic name.
"""

from __future__ import annotations

import datetime as dt
import os
from decimal import Decimal
from typing import Any

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://dft:testonly@localhost:5432/dft"
)
os.environ.setdefault("JWT_SECRET", "changeme-dft-secret-key-2026")

from app.services.ersv_pool import PAPER_RECORD_MARKER
from app.services.ticket_renderer import (
    WEIGHERS,
    build_ticket_data,
    render_ticket_preview_text,
)


def _row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": 21359,
        "entry_date": dt.date(2025, 2, 19),
        "entry_time": dt.time(9, 45),
        "ersv_number": "00042/25",
        "supplier_code": "PYRCOM",
        "supplier_name": "PyrCom Andina S.A.S.",
        "car_kg": Decimal("0.000"),
        "truck_kg": Decimal("24580.000"),
        "special_kg": Decimal("0.000"),
        "total_input_kg": Decimal("24580.000"),
    }
    base.update(overrides)
    return base


def test_in_window_weigher_is_marker() -> None:
    data = build_ticket_data(_row(), position_in_day=1, total_in_day=3)
    assert data["weigher"] == PAPER_RECORD_MARKER
    # Pool pass-through must also emit marker on driver / cédula / placa.
    assert data["driver_name"] == PAPER_RECORD_MARKER
    assert data["driver_cedula"] == PAPER_RECORD_MARKER
    assert data["vehicle_plate"] == PAPER_RECORD_MARKER


def test_in_window_text_preview_shows_marker_on_pesado_por() -> None:
    """Operator name renders on the line FOLLOWING the ``PESADO POR``
    header (see ``render_ticket_preview_text``). In-window that line
    must carry the paper-record marker."""
    data = build_ticket_data(_row(), position_in_day=1, total_in_day=3)
    text = render_ticket_preview_text(data)
    lines = text.splitlines()
    idx = next(
        (i for i, line in enumerate(lines) if "PESADO POR" in line), None
    )
    assert idx is not None, "no PESADO POR line in ticket preview"
    assert idx + 1 < len(lines), "operator line missing after PESADO POR"
    operator_line = lines[idx + 1]
    assert "Paper record" in operator_line, (
        f"operator line does not carry marker: {operator_line!r}"
    )
    # PLACA / CONDUCTOR / CEDULA lines also carry marker.
    placa_line = next(line for line in lines if line.startswith("PLACA:"))
    cond_line = next(line for line in lines if line.startswith("CONDUCTOR:"))
    ced_line = next(line for line in lines if line.startswith("CEDULA:"))
    assert "Paper record" in placa_line
    assert "Paper record" in cond_line
    assert "Paper record" in ced_line


def test_out_of_window_weigher_is_deterministic() -> None:
    out_row = _row(
        id=21900,
        entry_date=dt.date(2025, 10, 12),
        ersv_number="00500/25",
    )
    data = build_ticket_data(out_row, position_in_day=1, total_in_day=1)
    assert data["weigher"] in WEIGHERS
    assert PAPER_RECORD_MARKER not in str(data["weigher"])
    assert PAPER_RECORD_MARKER not in str(data["driver_name"])
    assert PAPER_RECORD_MARKER not in str(data["vehicle_plate"])


def test_out_of_window_text_preview_has_no_marker() -> None:
    out_row = _row(
        id=21900,
        entry_date=dt.date(2025, 10, 12),
        ersv_number="00500/25",
    )
    data = build_ticket_data(out_row, position_in_day=1, total_in_day=1)
    text = render_ticket_preview_text(data)
    assert "Paper record" not in text
