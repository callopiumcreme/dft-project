"""Tests for ``app.services.ersv_pool`` — Round-3 N6 / N7 paper-record marker.

Covers:
- in-window dates emit the literal marker on every personal-data field
  (driver / cédula / plate / hora_salida_date_eu / hora_salida_time).
- out-of-window dates fall back to the deterministic generator and never
  emit the marker (back-compat — legacy / future electronic-capture rows).
- transport_company stays deterministic in both branches (supplier→carrier
  set is real; plan §2 scopes the marker strictly to personal data).
- supplier-table lookups (loading_address / distance_km /
  holder_country_label) are unaffected by the window.
- the exposed window constants match the frontend SSoT
  (``landing/src/config/paper-records-window.ts``).
- ``is_in_paper_records_window`` accepts None safely and is inclusive on
  both bounds.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://dft:testonly@localhost:5432/dft"
)
os.environ.setdefault("JWT_SECRET", "changeme-dft-secret-key-2026")

import pytest

from app.services.ersv_pool import (
    PAPER_RECORD_MARKER,
    PAPER_RECORDS_WINDOW_END,
    PAPER_RECORDS_WINDOW_START,
    build_pool_fields,
    is_in_paper_records_window,
)

# ---------------------------------------------------------------------------
# Constants — must mirror landing/src/config/paper-records-window.ts.
# This test is the explicit drift guard for the N1 enforcement.
# ---------------------------------------------------------------------------
EXPECTED_WINDOW_START = date(2025, 1, 1)
EXPECTED_WINDOW_END = date(2025, 8, 31)
EXPECTED_MARKER = "[Paper record — Girardot archive]"


def test_window_constants_match_frontend() -> None:
    """Drift guard — TS and Python window bounds must agree (N1)."""
    assert PAPER_RECORDS_WINDOW_START == EXPECTED_WINDOW_START
    assert PAPER_RECORDS_WINDOW_END == EXPECTED_WINDOW_END


def test_marker_literal_is_stable() -> None:
    """Drift guard — the verifier-facing marker text must not silently mutate."""
    assert PAPER_RECORD_MARKER == EXPECTED_MARKER


@pytest.mark.parametrize(
    ("d", "expected"),
    [
        (date(2025, 1, 1), True),   # inclusive lower bound
        (date(2025, 1, 31), True),
        (date(2025, 4, 15), True),
        (date(2025, 8, 31), True),  # inclusive upper bound
        (date(2024, 12, 31), False),
        (date(2025, 9, 1), False),
        (date(2026, 1, 1), False),
        (None, False),
    ],
)
def test_is_in_paper_records_window(d: date | None, expected: bool) -> None:
    assert is_in_paper_records_window(d) is expected


# ---------------------------------------------------------------------------
# Marker behaviour — in-window
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "entry_date",
    [date(2025, 1, 2), date(2025, 2, 1), date(2025, 4, 15), date(2025, 8, 31)],
)
def test_in_window_emits_marker_on_personal_data(entry_date: date) -> None:
    out = build_pool_fields(
        "00042/25",
        entry_date,
        daily_input_id=21359,
        position_in_day=1,
        total_in_day=3,
        supplier_code="PYRCOM",
    )
    # Personal-data fields ALL marker.
    assert out["driver_name"] == PAPER_RECORD_MARKER
    assert out["driver_cedula"] == PAPER_RECORD_MARKER
    assert out["vehicle_plate"] == PAPER_RECORD_MARKER
    assert out["hora_salida_date_eu"] == PAPER_RECORD_MARKER
    assert out["hora_salida_time"] == PAPER_RECORD_MARKER

    # ISO salida date stays real (used by downstream consumers for
    # tech-level ordering; no personal-data exposure).
    assert out["hora_salida_date_iso"] == (entry_date - timedelta(days=1)).isoformat()

    # Transport company and supplier-table lookups remain real.
    assert out["transport_company"] == "Soluciones Ambientales 4R"
    assert out["loading_address"] == "Cr. La Mesa Km 4, 250040 Mosquera"
    assert out["distance_km"] == 120
    assert out["holder_country_label"] == "COLOMBIA"


def test_in_window_no_pool_field_leaks_personal_data() -> None:
    """No pool field whose name suggests personal data may carry a real name."""
    out = build_pool_fields(
        "00042/25",
        date(2025, 3, 15),
        daily_input_id=21359,
        position_in_day=1,
        total_in_day=2,
        supplier_code="KALTIRE",
    )
    # Sample of pool name fragments that flagged real Colombian names
    # pre-Step 2. If any of these appears verbatim inside the marker
    # fields, the generator has regressed and the marker substitution
    # is incomplete.
    forbidden_substrings = (
        "Ramírez", "Hernández", "Torres", "Restrepo", "Marín",
        "Quintero", "Patiño", "Castaño", "López", "Sepúlveda",
        "Cárdenas", "Vargas",
    )
    for field in (
        "driver_name", "driver_cedula", "vehicle_plate",
        "hora_salida_date_eu", "hora_salida_time",
    ):
        value = str(out[field])
        for needle in forbidden_substrings:
            assert needle not in value, (
                f"Personal name fragment {needle!r} leaked into "
                f"marker field {field!r}: {value!r}"
            )


# ---------------------------------------------------------------------------
# Out-of-window — back-compat: deterministic generator still functional.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "entry_date",
    [date(2024, 12, 31), date(2025, 9, 1), date(2025, 12, 1), date(2026, 1, 15)],
)
def test_out_of_window_emits_deterministic_values(entry_date: date) -> None:
    out = build_pool_fields(
        "99999/25",
        entry_date,
        daily_input_id=99999,
        position_in_day=1,
        total_in_day=1,
        supplier_code="PYRCOM",
    )
    # Marker MUST NOT appear out-of-window.
    for field in (
        "driver_name", "driver_cedula", "vehicle_plate",
        "hora_salida_date_eu", "hora_salida_time",
    ):
        assert PAPER_RECORD_MARKER not in str(out[field]), (
            f"Out-of-window field {field!r} unexpectedly contains marker: "
            f"{out[field]!r}"
        )
    # Sanity — driver looks like a real name (contains a space).
    assert " " in str(out["driver_name"])
    # Placa shape ``AAA-NNN``.
    placa = str(out["vehicle_plate"])
    assert len(placa) == 7 and placa[3] == "-"
    # Cedula contains dots (Colombian thousands separator).
    assert "." in str(out["driver_cedula"])


def test_out_of_window_is_deterministic_across_calls() -> None:
    """Same row key → same generated values across two calls (N1 stability)."""
    args = dict(
        ersv_number="00050/24",
        entry_date=date(2024, 11, 5),
        daily_input_id=1234,
        position_in_day=2,
        total_in_day=4,
        supplier_code="ESENTTIA",
    )
    a = build_pool_fields(**args)  # type: ignore[arg-type]
    b = build_pool_fields(**args)  # type: ignore[arg-type]
    assert a == b
