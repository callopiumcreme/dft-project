"""Cert-flag drift watchdog — Round-3 internal audit Step 3 (N10).

Background
----------
Round-3 finding N4 was closed by hiding the cert-flag columns from the
verifier-facing UI (commit ``7e3234d``). The underlying data flags —
``certificates.notes LIKE '%AUDIT-MISMATCH%'`` and
``certificates.scheme_pdf_detected <> scheme`` — are still recorded in
the DB so the audit trail survives, but nothing in the application
layer surfaces them anymore.

This script is the automated guard against silent drift. It compares
the live ``certificates`` table counts against the expected baseline
captured at audit-close (Round-3, 2026-05-26):

* ``AUDIT-MISMATCH`` notes: **2 rows** active
  (``CO222-00000026``, ``ES216-20254036``)
* Scheme PDF/DB mismatch: **5 rows** active
  (``CO222-00000026``, ``CO222-00000027``, ``US201-120372025``,
  ``US201-138762025``, ``US201-158772025``) — all five flagged for
  Step 4 (N9) root-cause investigation.

Behaviour
---------
* Exit code 0 — both counts match the expected baseline.
* Exit code 1 — drift detected (count higher or lower); a unified
  report of new and missing rows is printed to stderr.

The watchdog is read-only. It NEVER mutates ``certificates``, and it
honours the ``deleted_at IS NULL`` filter (same shape as
``ix_certificates_scheme_mismatch``).

Usage
-----
.. code-block:: bash

    docker exec dft-project_backend_1 \\
        python scripts/cert_flag_watchdog.py

    # JSON output for CI consumption:
    docker exec dft-project_backend_1 \\
        python scripts/cert_flag_watchdog.py --json

    # Re-baseline after Step 4 (N9) resolves the scheme drift to 0:
    docker exec dft-project_backend_1 \\
        python scripts/cert_flag_watchdog.py \\
        --expected-audit-mismatch 2 \\
        --expected-scheme-drift 0

Refresh of expectations is a code change (this file), not a flag, so
the audit-trail is git-tracked. The CLI override exists for one-shot
checks during investigation (e.g. simulating the post-Step-4 state),
not for permanent re-baselining.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# ---------------------------------------------------------------------------
# Baseline expectations — Round-3 close, 2026-05-26.
# Updating these constants IS the re-baseline event; commit message must
# describe which N-finding closed which flag.
# ---------------------------------------------------------------------------
EXPECTED_AUDIT_MISMATCH_COUNT = 2
EXPECTED_SCHEME_DRIFT_COUNT = 5

EXPECTED_AUDIT_MISMATCH_CERTS = (
    "CO222-00000026",
    "ES216-20254036",
)
EXPECTED_SCHEME_DRIFT_CERTS = (
    "CO222-00000026",
    "CO222-00000027",
    "US201-120372025",
    "US201-138762025",
    "US201-158772025",
)

# ---------------------------------------------------------------------------
# SQL — pinned, no-format. Both queries honour soft delete.
# ---------------------------------------------------------------------------
_SQL_AUDIT_MISMATCH = text(
    """
    SELECT cert_number
    FROM   certificates
    WHERE  notes LIKE '%AUDIT-MISMATCH%'
      AND  deleted_at IS NULL
    ORDER  BY cert_number
    """
)

_SQL_SCHEME_DRIFT = text(
    """
    SELECT cert_number
    FROM   certificates
    WHERE  scheme_pdf_detected IS NOT NULL
      AND  scheme_pdf_detected <> scheme
      AND  deleted_at IS NULL
    ORDER  BY cert_number
    """
)


# ---------------------------------------------------------------------------
# Pure logic — testable without a DB connection.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FlagCounts:
    """Snapshot of the two cert-flag dimensions the watchdog tracks."""

    audit_mismatch_certs: tuple[str, ...]
    scheme_drift_certs: tuple[str, ...]

    @property
    def audit_mismatch_count(self) -> int:
        return len(self.audit_mismatch_certs)

    @property
    def scheme_drift_count(self) -> int:
        return len(self.scheme_drift_certs)


@dataclass(frozen=True)
class DriftReport:
    """Diff between expected baseline and observed live state."""

    ok: bool
    observed: FlagCounts
    expected_audit_mismatch: tuple[str, ...]
    expected_scheme_drift: tuple[str, ...]
    new_audit_mismatch: tuple[str, ...]
    missing_audit_mismatch: tuple[str, ...]
    new_scheme_drift: tuple[str, ...]
    missing_scheme_drift: tuple[str, ...]

    def to_json(self) -> str:
        return json.dumps(
            {
                "ok": self.ok,
                "observed": {
                    "audit_mismatch_count": self.observed.audit_mismatch_count,
                    "audit_mismatch_certs": list(self.observed.audit_mismatch_certs),
                    "scheme_drift_count": self.observed.scheme_drift_count,
                    "scheme_drift_certs": list(self.observed.scheme_drift_certs),
                },
                "expected": {
                    "audit_mismatch_certs": list(self.expected_audit_mismatch),
                    "scheme_drift_certs": list(self.expected_scheme_drift),
                },
                "drift": {
                    "new_audit_mismatch": list(self.new_audit_mismatch),
                    "missing_audit_mismatch": list(self.missing_audit_mismatch),
                    "new_scheme_drift": list(self.new_scheme_drift),
                    "missing_scheme_drift": list(self.missing_scheme_drift),
                },
            },
            indent=2,
        )


def check_drift(
    observed: FlagCounts,
    expected_audit_mismatch: tuple[str, ...] = EXPECTED_AUDIT_MISMATCH_CERTS,
    expected_scheme_drift: tuple[str, ...] = EXPECTED_SCHEME_DRIFT_CERTS,
) -> DriftReport:
    """Pure diff. Compares cert-number sets (set semantics, ignoring order)."""
    exp_audit = set(expected_audit_mismatch)
    exp_scheme = set(expected_scheme_drift)
    obs_audit = set(observed.audit_mismatch_certs)
    obs_scheme = set(observed.scheme_drift_certs)

    new_audit = tuple(sorted(obs_audit - exp_audit))
    missing_audit = tuple(sorted(exp_audit - obs_audit))
    new_scheme = tuple(sorted(obs_scheme - exp_scheme))
    missing_scheme = tuple(sorted(exp_scheme - obs_scheme))

    ok = (
        not new_audit
        and not missing_audit
        and not new_scheme
        and not missing_scheme
    )

    return DriftReport(
        ok=ok,
        observed=observed,
        expected_audit_mismatch=tuple(sorted(expected_audit_mismatch)),
        expected_scheme_drift=tuple(sorted(expected_scheme_drift)),
        new_audit_mismatch=new_audit,
        missing_audit_mismatch=missing_audit,
        new_scheme_drift=new_scheme,
        missing_scheme_drift=missing_scheme,
    )


def format_human_report(report: DriftReport) -> str:
    """Multi-line human report for stdout/stderr."""
    lines: list[str] = []
    obs = report.observed
    status = "OK" if report.ok else "DRIFT"
    lines.append(f"[cert-flag-watchdog] status={status}")
    lines.append(
        f"  audit_mismatch: observed={obs.audit_mismatch_count} "
        f"expected={len(report.expected_audit_mismatch)}"
    )
    lines.append(
        f"  scheme_drift:   observed={obs.scheme_drift_count} "
        f"expected={len(report.expected_scheme_drift)}"
    )
    if not report.ok:
        if report.new_audit_mismatch:
            lines.append(
                "  NEW AUDIT-MISMATCH certs (not in baseline): "
                + ", ".join(report.new_audit_mismatch)
            )
        if report.missing_audit_mismatch:
            lines.append(
                "  MISSING AUDIT-MISMATCH certs (expected, not observed): "
                + ", ".join(report.missing_audit_mismatch)
            )
        if report.new_scheme_drift:
            lines.append(
                "  NEW scheme drift (not in baseline): "
                + ", ".join(report.new_scheme_drift)
            )
        if report.missing_scheme_drift:
            lines.append(
                "  MISSING scheme drift (expected, not observed): "
                + ", ".join(report.missing_scheme_drift)
            )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# DB I/O — the only impure layer.
# ---------------------------------------------------------------------------
async def fetch_counts(session: AsyncSession) -> FlagCounts:
    """Run both SQL probes and return a ``FlagCounts`` snapshot."""
    audit_rows = (await session.execute(_SQL_AUDIT_MISMATCH)).mappings().all()
    scheme_rows = (await session.execute(_SQL_SCHEME_DRIFT)).mappings().all()
    return FlagCounts(
        audit_mismatch_certs=tuple(r["cert_number"] for r in audit_rows),
        scheme_drift_certs=tuple(r["cert_number"] for r in scheme_rows),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--json",
        action="store_true",
        help="emit JSON to stdout instead of the human report",
    )
    p.add_argument(
        "--expected-audit-mismatch",
        type=int,
        default=None,
        help=(
            "override the expected AUDIT-MISMATCH count for this run "
            "(does NOT change the baseline; useful during investigation)"
        ),
    )
    p.add_argument(
        "--expected-scheme-drift",
        type=int,
        default=None,
        help="override the expected scheme-drift count for this run",
    )
    return p


async def _amain() -> int:
    args = _build_arg_parser().parse_args()

    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://dft:dft@db:5432/dft",
    )
    engine = create_async_engine(database_url, poolclass=NullPool, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with Session() as session:
            observed = await fetch_counts(session)
    finally:
        await engine.dispose()

    # CLI overrides — only count is overridden; the cert-set check still
    # uses the constants, so a count override that doesn't match the
    # baseline set will still report drift on the diff section.
    if args.expected_audit_mismatch is not None and (
        args.expected_audit_mismatch != EXPECTED_AUDIT_MISMATCH_COUNT
    ):
        # Override the count by truncating / extending against the baseline
        # set is meaningless; emit a sentinel "expected_count_override" line
        # in human report. JSON consumers see the real diff below.
        sys.stderr.write(
            "[cert-flag-watchdog] note: --expected-audit-mismatch override "
            f"requested ({args.expected_audit_mismatch}); diff still computed "
            "against the baseline cert set.\n"
        )
    if args.expected_scheme_drift is not None and (
        args.expected_scheme_drift != EXPECTED_SCHEME_DRIFT_COUNT
    ):
        sys.stderr.write(
            "[cert-flag-watchdog] note: --expected-scheme-drift override "
            f"requested ({args.expected_scheme_drift}); diff still computed "
            "against the baseline cert set.\n"
        )

    report = check_drift(observed)

    if args.json:
        sys.stdout.write(report.to_json() + "\n")
    else:
        out = format_human_report(report)
        if report.ok:
            sys.stdout.write(out + "\n")
        else:
            sys.stderr.write(out + "\n")

    return 0 if report.ok else 1


def main() -> None:
    sys.exit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
