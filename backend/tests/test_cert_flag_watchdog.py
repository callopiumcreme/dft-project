"""Tests for ``scripts.cert_flag_watchdog`` — Round-3 Step 3 (N10).

Coverage:
- ``check_drift`` PASS on the exact baseline.
- ``check_drift`` DRIFT (new cert appearing) on seeded drift.
- ``check_drift`` DRIFT (missing baseline cert) on partial state.
- ``check_drift`` reports the symmetric diff cleanly (no overlap leakage).
- ``fetch_counts`` correctly projects ``cert_number`` from a fake session.
- ``format_human_report`` emits ``OK`` on PASS and ``DRIFT`` + diff lines
  on FAIL.
- ``DriftReport.to_json`` round-trips through ``json.loads`` with the
  fields the watchdog CLI promises.

The watchdog itself talks to ``certificates`` via SQLAlchemy; the tests
keep the DB out of scope by using a fake ``execute()`` that returns
pre-seeded mappings — same pattern as ``test_ersv_renderer._FakeSession``.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://dft:testonly@localhost:5432/dft"
)
os.environ.setdefault("JWT_SECRET", "changeme-dft-secret-key-2026")

# Watchdog lives under ``backend/scripts`` which is NOT on sys.path by
# default (scripts run as top-level files, not as a package). Add the
# backend root so ``import scripts.cert_flag_watchdog`` works.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from scripts.cert_flag_watchdog import (  # noqa: E402
    EXPECTED_AUDIT_MISMATCH_CERTS,
    EXPECTED_SCHEME_DRIFT_CERTS,
    DriftReport,
    FlagCounts,
    check_drift,
    fetch_counts,
    format_human_report,
)


# ---------------------------------------------------------------------------
# Fake AsyncSession — single execute() returns the next seeded mappings.
# ---------------------------------------------------------------------------
class _Mappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def all(self) -> list[dict[str, Any]]:
        return list(self._rows)


class _Result:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> _Mappings:
        return _Mappings(self._rows)


class _FakeSession:
    """Two-shot session: first execute() returns audit-mismatch rows,
    second returns scheme-drift rows. Matches the call order inside
    ``fetch_counts``."""

    def __init__(
        self,
        audit_rows: list[dict[str, Any]],
        scheme_rows: list[dict[str, Any]],
    ) -> None:
        self._results = [_Result(audit_rows), _Result(scheme_rows)]
        self.calls = 0

    async def execute(
        self, _stmt: Any, _params: dict[str, Any] | None = None
    ) -> _Result:
        if self.calls >= len(self._results):
            raise AssertionError("execute() called more times than seeded")
        out = self._results[self.calls]
        self.calls += 1
        return out


# ---------------------------------------------------------------------------
# Constants — baseline known at Round-3 close (2026-05-26).
# Drift guard: if these constants ever change in the watchdog, this test
# file must change in the same commit.
# ---------------------------------------------------------------------------
BASELINE_AUDIT_MISMATCH = (
    "CO222-00000026",
    "ES216-20254036",
)
BASELINE_SCHEME_DRIFT = (
    "CO222-00000026",
    "CO222-00000027",
    "US201-120372025",
    "US201-138762025",
    "US201-158772025",
)


def test_baseline_constants_match_watchdog_module() -> None:
    """Drift guard — test baseline must mirror watchdog module constants."""
    assert set(EXPECTED_AUDIT_MISMATCH_CERTS) == set(BASELINE_AUDIT_MISMATCH)
    assert set(EXPECTED_SCHEME_DRIFT_CERTS) == set(BASELINE_SCHEME_DRIFT)


# ---------------------------------------------------------------------------
# check_drift — pure logic
# ---------------------------------------------------------------------------
def test_check_drift_exact_baseline_is_ok() -> None:
    observed = FlagCounts(
        audit_mismatch_certs=BASELINE_AUDIT_MISMATCH,
        scheme_drift_certs=BASELINE_SCHEME_DRIFT,
    )
    report = check_drift(observed)
    assert report.ok is True
    assert report.new_audit_mismatch == ()
    assert report.missing_audit_mismatch == ()
    assert report.new_scheme_drift == ()
    assert report.missing_scheme_drift == ()


def test_check_drift_baseline_set_is_order_independent() -> None:
    """``check_drift`` compares sets — feeding reversed tuples is still OK."""
    observed = FlagCounts(
        audit_mismatch_certs=tuple(reversed(BASELINE_AUDIT_MISMATCH)),
        scheme_drift_certs=tuple(reversed(BASELINE_SCHEME_DRIFT)),
    )
    report = check_drift(observed)
    assert report.ok is True


def test_check_drift_new_audit_mismatch_cert_reports_drift() -> None:
    """Seeded drift: an extra AUDIT-MISMATCH cert appeared."""
    observed = FlagCounts(
        audit_mismatch_certs=BASELINE_AUDIT_MISMATCH + ("CO999-99999999",),
        scheme_drift_certs=BASELINE_SCHEME_DRIFT,
    )
    report = check_drift(observed)
    assert report.ok is False
    assert report.new_audit_mismatch == ("CO999-99999999",)
    assert report.missing_audit_mismatch == ()
    assert report.new_scheme_drift == ()
    assert report.missing_scheme_drift == ()


def test_check_drift_new_scheme_drift_cert_reports_drift() -> None:
    """Seeded drift: an extra scheme-mismatch cert appeared."""
    observed = FlagCounts(
        audit_mismatch_certs=BASELINE_AUDIT_MISMATCH,
        scheme_drift_certs=BASELINE_SCHEME_DRIFT + ("US201-NEW0000001",),
    )
    report = check_drift(observed)
    assert report.ok is False
    assert report.new_scheme_drift == ("US201-NEW0000001",)
    assert report.missing_scheme_drift == ()


def test_check_drift_missing_baseline_cert_reports_drift() -> None:
    """A baseline cert silently disappeared (soft-deleted? cert_number
    changed?). Watchdog must catch it."""
    observed = FlagCounts(
        audit_mismatch_certs=("CO222-00000026",),  # ES216-20254036 missing
        scheme_drift_certs=BASELINE_SCHEME_DRIFT,
    )
    report = check_drift(observed)
    assert report.ok is False
    assert report.missing_audit_mismatch == ("ES216-20254036",)
    assert report.new_audit_mismatch == ()


def test_check_drift_symmetric_diff_is_clean() -> None:
    """If a baseline cert is replaced by a new one, both sides report."""
    observed = FlagCounts(
        audit_mismatch_certs=("CO222-00000026", "ZZ000-99999999"),
        scheme_drift_certs=BASELINE_SCHEME_DRIFT,
    )
    report = check_drift(observed)
    assert report.ok is False
    assert report.new_audit_mismatch == ("ZZ000-99999999",)
    assert report.missing_audit_mismatch == ("ES216-20254036",)


def test_check_drift_empty_observed_reports_all_missing() -> None:
    """DB wiped or wrong schema — watchdog reports every baseline cert
    as missing rather than silently returning OK on count=0."""
    observed = FlagCounts(audit_mismatch_certs=(), scheme_drift_certs=())
    report = check_drift(observed)
    assert report.ok is False
    assert set(report.missing_audit_mismatch) == set(BASELINE_AUDIT_MISMATCH)
    assert set(report.missing_scheme_drift) == set(BASELINE_SCHEME_DRIFT)


# ---------------------------------------------------------------------------
# fetch_counts — projection round-trip via fake session
# ---------------------------------------------------------------------------
def test_fetch_counts_projects_cert_number_from_rows() -> None:
    session = _FakeSession(
        audit_rows=[
            {"cert_number": "CO222-00000026"},
            {"cert_number": "ES216-20254036"},
        ],
        scheme_rows=[
            {"cert_number": cn} for cn in BASELINE_SCHEME_DRIFT
        ],
    )
    out = asyncio.run(fetch_counts(session))  # type: ignore[arg-type]
    assert out.audit_mismatch_count == 2
    assert out.scheme_drift_count == 5
    assert "CO222-00000026" in out.audit_mismatch_certs
    assert "US201-120372025" in out.scheme_drift_certs


def test_fetch_counts_empty_db_returns_zero_counts() -> None:
    session = _FakeSession(audit_rows=[], scheme_rows=[])
    out = asyncio.run(fetch_counts(session))  # type: ignore[arg-type]
    assert out.audit_mismatch_count == 0
    assert out.scheme_drift_count == 0


# ---------------------------------------------------------------------------
# format_human_report
# ---------------------------------------------------------------------------
def test_format_human_report_ok_state() -> None:
    observed = FlagCounts(
        audit_mismatch_certs=BASELINE_AUDIT_MISMATCH,
        scheme_drift_certs=BASELINE_SCHEME_DRIFT,
    )
    report = check_drift(observed)
    text = format_human_report(report)
    assert "status=OK" in text
    assert "audit_mismatch: observed=2 expected=2" in text
    assert "scheme_drift:   observed=5 expected=5" in text
    # No diff section on OK.
    assert "NEW" not in text
    assert "MISSING" not in text


def test_format_human_report_drift_state_lists_diff() -> None:
    observed = FlagCounts(
        audit_mismatch_certs=BASELINE_AUDIT_MISMATCH + ("CO999-99999999",),
        scheme_drift_certs=BASELINE_SCHEME_DRIFT[:-1],  # last one missing
    )
    report = check_drift(observed)
    text = format_human_report(report)
    assert "status=DRIFT" in text
    assert "NEW AUDIT-MISMATCH certs (not in baseline): CO999-99999999" in text
    assert (
        "MISSING scheme drift (expected, not observed): US201-158772025"
        in text
    )


# ---------------------------------------------------------------------------
# DriftReport.to_json — CLI contract for --json output
# ---------------------------------------------------------------------------
def test_drift_report_to_json_round_trip_fields() -> None:
    observed = FlagCounts(
        audit_mismatch_certs=BASELINE_AUDIT_MISMATCH + ("CO999-99999999",),
        scheme_drift_certs=BASELINE_SCHEME_DRIFT,
    )
    report = check_drift(observed)
    data = json.loads(report.to_json())

    assert data["ok"] is False
    assert data["observed"]["audit_mismatch_count"] == 3
    assert data["observed"]["scheme_drift_count"] == 5
    assert "CO999-99999999" in data["observed"]["audit_mismatch_certs"]
    assert data["drift"]["new_audit_mismatch"] == ["CO999-99999999"]
    assert data["drift"]["missing_audit_mismatch"] == []
    assert data["drift"]["new_scheme_drift"] == []
    assert data["drift"]["missing_scheme_drift"] == []
    # Expected baseline echoed in JSON for audit-log clarity.
    assert set(data["expected"]["audit_mismatch_certs"]) == set(
        BASELINE_AUDIT_MISMATCH
    )


def test_drift_report_to_json_ok_state_has_no_diff_entries() -> None:
    observed = FlagCounts(
        audit_mismatch_certs=BASELINE_AUDIT_MISMATCH,
        scheme_drift_certs=BASELINE_SCHEME_DRIFT,
    )
    report = check_drift(observed)
    data = json.loads(report.to_json())
    assert data["ok"] is True
    assert data["drift"]["new_audit_mismatch"] == []
    assert data["drift"]["missing_audit_mismatch"] == []
    assert data["drift"]["new_scheme_drift"] == []
    assert data["drift"]["missing_scheme_drift"] == []
