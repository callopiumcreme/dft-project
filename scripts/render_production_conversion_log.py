"""Render the production conversion log PDF for the RTFO-310825 bundle.

Story: E1-S1.10 / DFTEN-110 — produces monthly production conversion log PDFs
for the UK DfT Track A submission bundle covering Jan–Aug 2025 production at
the OisteBio / DFT Energy Girardot pyrolysis facility.

The PDF reports per-day kg-to-litre conversion for each production day
recorded in the ``daily_production`` table, columns:

- prod_date
- kg_to_production       (feedstock to reactor — "input kg")
- eu_prod_kg             (EU-spec product mass)
- plus_prod_kg           (PLUS-spec product mass)
- litres_eu              (eu_prod_kg / density_eu — plain numeric post-0014)
- litres_plus            (plus_prod_kg / density_plus — plain numeric post-0014)
- liquid yield %         ((eu_prod_kg + plus_prod_kg) / kg_to_production)

Non-production days (weekends + Colombian public holidays) are listed
explicitly as a gap line below the table; they have no row in
``daily_production`` and are reported honestly as omitted rather than
back-filled.

Usage::

    python3 scripts/render_production_conversion_log.py [--period YYYY-MM] [--out PATH]

Default output path follows the RTFO-310825 bundle layout::

    deliverables/RTFO-310825/02_ros_export/
        05_production_conversion_logs_<month>_<year>.pdf

Uses the deterministic Jinja + WeasyPrint pipeline from
``backend.app.services.pdf_renderer`` so the same input always produces a
byte-identical PDF (fixed pdf_identifier, no XMP metadata, full-font
embed, no creation date).

Data source: reads via direct psql through ``dft-project_db_1`` — no
FastAPI dependency. Monthly densities are resolved from ``product_densities``
for the reporting month (effective_from = first of that month) per the
post-migration-0014 schema.

Constraints (per project memory):
- DO NOT commit, push, or deploy.
- DO NOT alter the database — read-only operations only.
- DO NOT silently rewrite historical compliance data (ISCC EU audit
  safety rule). Honest gaps are marked ``N/A`` or listed as a "no row"
  line; null values surface as ``—``.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from jinja2 import Environment

    from app.services.pdf_renderer import RenderResult  # type: ignore[import-not-found]

# Make the repository's ``backend/`` importable so the production renderer
# module can be reused as-is.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
_BACKEND_DIR: Final[Path] = _REPO_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.services import pdf_renderer  # type: ignore[import-not-found]  # noqa: E402

# Stash the production env factory so the patched one does not recurse.
_ORIGINAL_BUILD_ENV: Final = pdf_renderer._build_env

TEMPLATE_NAME: Final[str] = "production_conversion_log.html"

# Fixed generated-at label so the PDF stays byte-stable across re-runs.
# Bundle-freeze anchor for the 8-month RTFO-310825 package.
GENERATED_AT: Final[str] = "2026-05-21T00:00:00Z"

# Docker container hosting Postgres. Read-only psql access.
DB_CONTAINER: Final[str] = "dft-project_db_1"
DB_USER: Final[str] = "dft"
DB_NAME: Final[str] = "dft"

# Default period — 2025-01 retained for back-compat invocation without args.
_DEFAULT_PERIOD: Final[str] = "2025-01"

_MONTH_NAMES: Final[dict[int, str]] = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------
def _period_bounds(period: str) -> tuple[str, str, date, date, str]:
    """From 'YYYY-MM' return (period, label, start_date, end_date, submission_ref)."""
    year_s, month_s = period.split("-")
    year, month = int(year_s), int(month_s)
    last_day = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last_day)
    label = f"{_MONTH_NAMES[month]} {year}"
    # All months in the 8-month bundle use the bundle-wide ref RTFO-310825.
    submission_ref = "RTFO-310825"
    return period, label, start, end, submission_ref


def _default_output(period: str) -> Path:
    """Derive default output path for the RTFO-310825 bundle."""
    period, label, _, _, submission_ref = _period_bounds(period)
    # Always route to RTFO-310825 for all months in the 8-month bundle.
    bundle_dir = submission_ref
    month_lower = label.lower().replace(" ", "_")
    fname = f"05_production_conversion_logs_{month_lower}.pdf"
    return (
        _REPO_ROOT
        / "deliverables"
        / bundle_dir
        / "02_ros_export"
        / fname
    )


# ---------------------------------------------------------------------------
# Jinja numeric filters — locked with Annex A / ISCC PoS status across bundle.
# ---------------------------------------------------------------------------
def _format_thousands(value: float, decimals: int = 2) -> str:
    """Format with thin-space thousands separator and comma decimal mark."""
    rounded = round(float(value), decimals)
    formatted = f"{rounded:,.{decimals}f}"
    return formatted.replace(",", " ").replace(".", ",")


def fmt_num(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return _format_thousands(float(value), decimals=3)


def fmt_kg(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{_format_thousands(float(value), decimals=3)} kg"


def fmt_l(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{_format_thousands(float(value), decimals=3)} L"


def fmt_pct(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{_format_thousands(float(value), decimals=2)} %"


def fmt_density(value: float | int | None) -> str:
    """Render a density as ``0,780 kg/L`` (three decimals + unit)."""
    if value is None:
        return "N/A"
    return f"{_format_thousands(float(value), decimals=3)} kg/L"


def fmt_density_plain(value: float | int | None) -> str:
    """Render a density as ``0,780`` (three decimals, no unit) for table cells."""
    if value is None:
        return "N/A"
    return _format_thousands(float(value), decimals=3)


# ---------------------------------------------------------------------------
# Database reads — psql via docker exec, JSON output for safe parsing.
# ---------------------------------------------------------------------------
def _psql(query: str) -> str:
    cmd = [
        "docker", "exec", DB_CONTAINER,
        "psql", "-U", DB_USER, "-d", DB_NAME,
        "-At", "-c", query,
    ]
    completed = subprocess.run(  # noqa: S603
        cmd, check=True, capture_output=True, text=True,
    )
    return completed.stdout.strip()


def _psql_json(query: str) -> Any:
    payload = _psql(query)
    if not payload or payload == "\\N":
        return None
    return json.loads(payload)


# ---------------------------------------------------------------------------
# Query builders — parameterised on (start, end) strings
# ---------------------------------------------------------------------------
def _density_query(start_iso: str) -> str:
    """Look up EU and PLUS densities for the given month (effective_from = first of month)."""
    return f"""
SELECT json_object_agg(product, density_kg_per_l::float8)
FROM product_densities
WHERE effective_from = DATE '{start_iso}'
  AND product IN ('EU', 'PLUS');
"""


def _daily_query(start_iso: str, end_iso: str) -> str:
    return f"""
SELECT json_agg(t ORDER BY t.prod_date)
FROM (
    SELECT
        to_char(prod_date, 'YYYY-MM-DD')        AS prod_date,
        kg_to_production::float8                AS input_kg,
        eu_prod_kg::float8                      AS eu_prod_kg,
        plus_prod_kg::float8                    AS plus_prod_kg,
        litres_eu::float8                       AS litres_eu,
        litres_plus::float8                     AS litres_plus,
        carbon_black_kg::float8                 AS carbon_black_kg,
        metal_scrap_kg::float8                  AS metal_scrap_kg,
        h2o_kg::float8                          AS h2o_kg,
        gas_syngas_kg::float8                   AS gas_syngas_kg,
        losses_kg::float8                       AS losses_kg,
        notes
    FROM daily_production
    WHERE prod_date >= DATE '{start_iso}'
      AND prod_date <= DATE '{end_iso}'
      AND deleted_at IS NULL
) AS t;
"""


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------
def _fetch_densities(start_iso: str) -> tuple[float, float]:
    """Return (density_eu, density_plus) for the given month from product_densities."""
    raw = _psql_json(_density_query(start_iso))
    if raw is None or "EU" not in raw or "PLUS" not in raw:
        raise SystemExit(
            f"No EU/PLUS density rows found in product_densities for effective_from={start_iso}"
        )
    return float(raw["EU"]), float(raw["PLUS"])


def _fetch_daily_rows(start_iso: str, end_iso: str) -> list[dict[str, Any]]:
    """Fetch raw daily_production rows for the period."""
    payload = _psql_json(_daily_query(start_iso, end_iso))
    return payload or []


# ---------------------------------------------------------------------------
# Row + totals builders
# ---------------------------------------------------------------------------
def _enrich_row(raw: dict[str, Any]) -> dict[str, Any]:
    """Compute per-row liquid-yield percentage; preserve nulls honestly."""
    eu = raw.get("eu_prod_kg")
    plus = raw.get("plus_prod_kg")
    inp = raw.get("input_kg")
    yield_pct: float | None
    if eu is None or plus is None or inp is None or inp == 0:
        yield_pct = None
    else:
        yield_pct = (float(eu) + float(plus)) / float(inp) * 100.0
    return {
        "date": raw["prod_date"],
        "input_kg": raw.get("input_kg"),
        "eu_prod_kg": raw.get("eu_prod_kg"),
        "plus_prod_kg": raw.get("plus_prod_kg"),
        "eu_prod_litres": raw.get("litres_eu"),
        "plus_prod_litres": raw.get("litres_plus"),
        "liquid_yield_pct": yield_pct,
        "notes": raw.get("notes") or "",
    }


def _build_totals(
    rows: list[dict[str, Any]],
    raw_rows: list[dict[str, Any]],
    period_start: date,
    period_end: date,
) -> dict[str, Any]:
    def _sum(field: str, source: list[dict[str, Any]]) -> float:
        return sum(float(r[field]) for r in source if r.get(field) is not None)

    total_input = _sum("input_kg", rows)
    total_eu_kg = _sum("eu_prod_kg", rows)
    total_plus_kg = _sum("plus_prod_kg", rows)
    total_eu_l = _sum("eu_prod_litres", rows)
    total_plus_l = _sum("plus_prod_litres", rows)
    yield_pct = (total_eu_kg + total_plus_kg) / total_input * 100.0 if total_input else None

    total_cb = _sum("carbon_black_kg", raw_rows)
    total_steel = _sum("metal_scrap_kg", raw_rows)
    total_h2o = _sum("h2o_kg", raw_rows)
    total_gas = _sum("gas_syngas_kg", raw_rows)
    total_losses = _sum("losses_kg", raw_rows)

    calendar_days = (period_end - period_start).days + 1
    day_count = len(rows)
    non_prod_count = calendar_days - day_count

    return {
        "input_kg": round(total_input, 3),
        "eu_prod_kg": round(total_eu_kg, 3),
        "plus_prod_kg": round(total_plus_kg, 3),
        "eu_prod_litres": round(total_eu_l, 3),
        "plus_prod_litres": round(total_plus_l, 3),
        "grand_total_litres": round(total_eu_l + total_plus_l, 3),
        "liquid_yield_pct": round(yield_pct, 2) if yield_pct is not None else None,
        "carbon_black_kg": round(total_cb, 3),
        "metal_scrap_kg": round(total_steel, 3),
        "h2o_kg": round(total_h2o, 3),
        "gas_syngas_kg": round(total_gas, 3),
        "losses_kg": round(total_losses, 3),
        "day_count": day_count,
        "non_production_day_count": non_prod_count,
    }


def _non_production_dates(
    daily_rows: list[dict[str, Any]], period_start: date, period_end: date
) -> list[str]:
    """All calendar dates in the reporting window with no production row."""
    seen = {r["date"] for r in daily_rows}
    out: list[str] = []
    current = period_start
    while current <= period_end:
        iso = current.isoformat()
        if iso not in seen:
            out.append(iso)
        current += timedelta(days=1)
    return out


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------
def build_context(period: str) -> dict[str, Any]:
    """Return the Jinja context for the production conversion log template."""
    period, label, period_start, period_end, submission_ref = _period_bounds(period)
    start_iso = period_start.isoformat()
    end_iso = period_end.isoformat()

    # Resolve monthly densities from product_densities table (post-migration-0014).
    density_eu, density_plus = _fetch_densities(start_iso)

    raw_rows = _fetch_daily_rows(start_iso, end_iso)
    daily_rows = [_enrich_row(r) for r in raw_rows]
    totals = _build_totals(daily_rows, raw_rows, period_start, period_end)
    non_production_days = _non_production_dates(daily_rows, period_start, period_end)
    calendar_day_count = (period_end - period_start).days + 1

    return {
        # Submission metadata.
        "submission_ref": submission_ref,
        "period": period,
        "period_label": label,
        "generated_at": GENERATED_AT,
        "calendar_day_count": calendar_day_count,
        # Submitter — Swiss GmbH per project memory.
        "submitter_company": "OisteBio GmbH",
        "submitter_address": "Oberneuhofstrasse 5, 6340 Baar, Switzerland",
        "plant_name": "Girardot, Colombia",
        "product": "DEV-P100 — refined pyrolysis oil",
        "product_eu_code": "DEV-P100-EU",
        "product_plus_code": "DEV-P100-PLUS",
        "off_taker": "Crown Oil Limited (UK)",
        "regulator": "UK DfT — LCF Delivery Unit",
        # Monthly densities resolved from product_densities table.
        "density_eu": density_eu,
        "density_plus": density_plus,
        # Data.
        "totals": totals,
        "daily_rows": daily_rows,
        "non_production_days": non_production_days,
        # SHA-256 placeholder — authoritative digest written to .sha256 side-car.
        "doc_hash": "0" * 64,
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
def _patched_env_factory() -> Environment:
    """Wrap the captured original env factory and register numeric filters."""
    base_env: Environment = _ORIGINAL_BUILD_ENV()
    base_env.filters["fmt_num"] = fmt_num
    base_env.filters["fmt_kg"] = fmt_kg
    base_env.filters["fmt_l"] = fmt_l
    base_env.filters["fmt_pct"] = fmt_pct
    base_env.filters["fmt_density"] = fmt_density
    base_env.filters["fmt_density_plain"] = fmt_density_plain
    return base_env


def render(out_pdf: Path, period: str) -> RenderResult:
    """Render the Production Conversion Log PDF and return the renderer's result."""
    pdf_renderer._build_env = _patched_env_factory
    try:
        result: RenderResult = pdf_renderer.render_to_pdf(
            template_name=TEMPLATE_NAME,
            context=build_context(period),
            output_path=out_pdf,
        )
        return result
    finally:
        pdf_renderer._build_env = _ORIGINAL_BUILD_ENV


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Render Production Conversion Log PDF for a given month."
    )
    parser.add_argument(
        "--period", default=_DEFAULT_PERIOD,
        help="Reporting month YYYY-MM (default: 2025-01)",
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="Output PDF path (default: deliverables/RTFO-310825/02_ros_export/...)",
    )
    # Back-compat: positional out path (legacy callers using argv[1]).
    parser.add_argument(
        "positional_out", nargs="?", type=Path, default=None,
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv[1:])

    out_pdf = args.out or args.positional_out or _default_output(args.period)
    out_pdf = out_pdf.resolve()
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    result = render(out_pdf, args.period)

    size_kb = result.pdf_size_bytes / 1024
    on_disk_sha = hashlib.sha256(result.pdf_path.read_bytes()).hexdigest()

    print(f"Period:      {args.period}")
    print(f"Rendered:    {result.pdf_path}")
    print(f"Size:        {size_kb:.1f} KB ({result.pdf_size_bytes} bytes)")
    print(f"Pages:       {result.page_count}")
    print(f"Template:    {result.template_name}")
    print(f"SHA-256:     {result.pdf_sha256}")
    print(f"On-disk:     {on_disk_sha}")
    print(f"Side-car:    {result.pdf_sha256_path}")
    print(f"Rendered at: {result.rendered_at.isoformat()}")
    print(f"Generated at (context, fixed for determinism): {GENERATED_AT}")
    print(f"Sanity (UTC now): {datetime.now(UTC).isoformat()}")

    if on_disk_sha != result.pdf_sha256:
        print("ERROR: on-disk SHA-256 differs from renderer-reported digest", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
