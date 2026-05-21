"""Render the FINAL Annex A mass-balance PDF for the RTFO-310125 bundle.

Story: E1-S1.17 / DFTEN-111 — Day 6 bundle freeze. Produces
``02_mass_balance_january_2025_FINAL.pdf`` for UK DfT Track A submission.

Reads live materialized-view data (``mv_mass_balance_daily`` and
``mv_mass_balance_monthly``) and the supplier breakdown directly from
``daily_inputs`` joined to ``suppliers`` + ``certificates``. All values
post-migrations 0009/0010/0011 (ISCC certificate corrections).

Uses the deterministic Jinja + WeasyPrint pipeline from
``backend.app.services.pdf_renderer``: fixed pdf_identifier, no XMP
metadata, full-font embed, no creation date. ``generated_at`` is a
fixed bundle-freeze anchor string so the SHA-256 stays stable across
re-runs.

Usage::

    python3 scripts/render_annex_a_final.py [out_pdf]

Default output path::

    deliverables/RTFO-310125/01_annex_a_mass_balance/
        02_mass_balance_january_2025_FINAL.pdf

Data is read via ``docker exec dft-project_db_1 psql`` (read-only, no
FastAPI dependency). Determinism mirrors render_production_conversion_log.py
and render_stock_carryover.py.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from jinja2 import Environment

    from app.services.pdf_renderer import RenderResult  # type: ignore[import-not-found]

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
_BACKEND_DIR: Final[Path] = _REPO_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.services import pdf_renderer  # type: ignore[import-not-found]  # noqa: E402

_ORIGINAL_BUILD_ENV: Final = pdf_renderer._build_env

TEMPLATE_NAME: Final[str] = "mass_balance.html"

GENERATED_AT: Final[str] = "2026-05-21T00:00:00Z"

DB_CONTAINER: Final[str] = "dft-project_db_1"
DB_USER: Final[str] = "dft"
DB_NAME: Final[str] = "dft"

# Default period if --period not supplied (back-compat with RTFO-310125).
_DEFAULT_PERIOD: Final[str] = "2025-01"

_MONTH_NAMES: Final[dict[int, str]] = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


def _period_bounds(period: str) -> tuple[str, str, str, str, str]:
    """From 'YYYY-MM' return (period, label, start_iso, end_iso, submission_ref)."""
    year_s, month_s = period.split("-")
    year, month = int(year_s), int(month_s)
    last_day = calendar.monthrange(year, month)[1]
    start = date(year, month, 1).isoformat()
    end = date(year, month, last_day).isoformat()
    label = f"{_MONTH_NAMES[month]} {year}"
    # Submission ref: RTFO-DDMMYY anchored to month-end of LATEST month in bundle.
    # For per-month rendering we keep the bundle-wide ref RTFO-310825 (Aug 31 2025)
    # unless caller overrides via env.
    submission_ref = "RTFO-310825"
    return period, label, start, end, submission_ref


# ---------------------------------------------------------------------------
# Jinja numeric filters — match template expectations from reports.py.
# ---------------------------------------------------------------------------
def _format_thousands(value: float, decimals: int = 2) -> str:
    rounded = round(float(value), decimals)
    formatted = f"{rounded:,.{decimals}f}"
    return formatted.replace(",", " ").replace(".", ",")


def fmt_num(value: float | int | None) -> str:
    if value is None:
        return "—"
    return _format_thousands(float(value), decimals=2)


def fmt_num_signed(value: float | int | None) -> str:
    if value is None:
        return "—"
    rounded = round(float(value), 2)
    sign = "+" if rounded > 0 else ("−" if rounded < 0 else "±")  # noqa: RUF001
    return f"{sign}{_format_thousands(abs(rounded), decimals=2)}"


def fmt_kg(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{_format_thousands(float(value), decimals=2)} kg"


def fmt_kg_signed(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{fmt_num_signed(value)} kg"


def fmt_l(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{_format_thousands(float(value), decimals=2)} L"


def fmt_pct(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{_format_thousands(float(value), decimals=2)} %"


def fmt_pct_signed(value: float | int | None) -> str:
    if value is None:
        return "—"
    rounded = round(float(value), 2)
    sign = "+" if rounded > 0 else ("−" if rounded < 0 else "±")  # noqa: RUF001
    return f"{sign}{_format_thousands(abs(rounded), decimals=2)} %"


def fmt_density(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{float(value):.4f}".replace(".", ",")


# ---------------------------------------------------------------------------
# DB reads via docker exec psql, JSON output.
# ---------------------------------------------------------------------------
def _psql_json(query: str) -> Any:
    cmd = [
        "docker",
        "exec",
        DB_CONTAINER,
        "psql",
        "-U",
        DB_USER,
        "-d",
        DB_NAME,
        "-At",
        "-c",
        query,
    ]
    completed = subprocess.run(  # noqa: S603
        cmd,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = completed.stdout.strip()
    if not payload or payload == "\\N":
        return None
    return json.loads(payload)


def _daily_query(start: str, end: str) -> str:
    return f"""
SELECT json_agg(t ORDER BY t.day) FROM (
    SELECT
        to_char(day, 'YYYY-MM-DD')              AS day,
        input_total_kg::float8                  AS input_kg,
        eu_prod_kg::float8                      AS eu_prod_kg,
        plus_prod_kg::float8                    AS plus_prod_kg,
        eu_prod_litres::float8                  AS eu_prod_litres,
        plus_prod_litres::float8                AS plus_prod_litres,
        output_total_kg::float8                 AS output_total_kg,
        closure_diff_pct::float8                AS closure_diff_pct
    FROM mv_mass_balance_daily
    WHERE day >= DATE '{start}' AND day <= DATE '{end}'
) AS t;
"""


def _monthly_query(start: str) -> str:
    return f"""
SELECT row_to_json(t) FROM (
    SELECT
        input_total_kg::float8                  AS input_kg,
        eu_prod_kg::float8                      AS eu_prod_kg,
        plus_prod_kg::float8                    AS plus_prod_kg,
        eu_prod_litres::float8                  AS eu_prod_litres,
        plus_prod_litres::float8                AS plus_prod_litres,
        output_total_kg::float8                 AS output_total_kg,
        closure_diff_pct::float8                AS closure_diff_pct
    FROM mv_mass_balance_monthly
    WHERE month = DATE '{start}'
) AS t;
"""


def _density_query(start: str, product: str) -> str:
    return f"""
SELECT density_kg_per_l::float8
FROM product_densities
WHERE product = '{product}'
  AND effective_from <= DATE '{start}'
ORDER BY effective_from DESC
LIMIT 1;
"""


def _byproducts_query(start: str, end: str) -> str:
    return f"""
SELECT row_to_json(t) FROM (
    SELECT
        COALESCE(SUM(carbon_black_kg), 0)::float8   AS carbon_black_kg,
        COALESCE(SUM(metal_scrap_kg), 0)::float8    AS metal_scrap_kg,
        COALESCE(SUM(gas_syngas_kg), 0)::float8     AS gas_syngas_kg,
        COALESCE(SUM(h2o_kg), 0)::float8            AS h2o_kg,
        COALESCE(SUM(losses_kg), 0)::float8         AS losses_kg
    FROM daily_production
    WHERE deleted_at IS NULL
      AND prod_date >= DATE '{start}'
      AND prod_date <= DATE '{end}'
) AS t;
"""


def _suppliers_query(start: str, end: str) -> str:
    return f"""
SELECT json_agg(t) FROM (
    SELECT
        s.name AS name,
        COALESCE(
            (SELECT c2.cert_number
             FROM daily_inputs di2
             JOIN certificates c2 ON c2.id = di2.certificate_id
             WHERE di2.deleted_at IS NULL
               AND di2.supplier_id = s.id
               AND di2.entry_date >= DATE '{start}'
               AND di2.entry_date <= DATE '{end}'
             GROUP BY c2.id, c2.cert_number
             ORDER BY SUM(di2.total_input_kg) DESC NULLS LAST, c2.cert_number ASC
             LIMIT 1),
            '—'
        ) AS cert_iscc_ref,
        SUM(di.total_input_kg)::float8 AS total_kg
    FROM daily_inputs di
    JOIN suppliers s ON s.id = di.supplier_id
    WHERE di.deleted_at IS NULL
      AND s.deleted_at IS NULL
      AND di.entry_date >= DATE '{start}'
      AND di.entry_date <= DATE '{end}'
    GROUP BY s.id, s.name
    ORDER BY total_kg DESC
) AS t;
"""


def _fetch_daily(start: str, end: str) -> list[dict[str, Any]]:
    raw = _psql_json(_daily_query(start, end)) or []
    rows: list[dict[str, Any]] = []
    for r in raw:
        input_kg = float(r["input_kg"]) if r.get("input_kg") is not None else 0.0
        closure_pct = (
            float(r["closure_diff_pct"]) if r.get("closure_diff_pct") is not None else None
        )
        closure_kg = (closure_pct / 100.0) * input_kg if closure_pct is not None else None
        rows.append(
            {
                "date": r["day"],
                "input_kg": input_kg if r.get("input_kg") is not None else None,
                "eu_prod_kg": r.get("eu_prod_kg"),
                "plus_prod_kg": r.get("plus_prod_kg"),
                "eu_prod_litres": r.get("eu_prod_litres"),
                "plus_prod_litres": r.get("plus_prod_litres"),
                "c14_pct": None,
                "closure_diff_kg": closure_kg,
            }
        )
    return rows


def _fetch_density(start: str, product: str) -> float | None:
    raw = _psql_json(_density_query(start, product))
    if raw is None:
        return None
    return float(raw)


def _fetch_byproducts(
    start: str, end: str, input_kg: float
) -> dict[str, Any] | None:
    raw = _psql_json(_byproducts_query(start, end))
    if raw is None:
        return None
    carbon_black = float(raw.get("carbon_black_kg") or 0.0)
    metal_scrap = float(raw.get("metal_scrap_kg") or 0.0)
    gas_syngas = float(raw.get("gas_syngas_kg") or 0.0)
    h2o = float(raw.get("h2o_kg") or 0.0)
    losses = float(raw.get("losses_kg") or 0.0)
    total = carbon_black + metal_scrap + gas_syngas + h2o + losses
    if total == 0:
        return None

    def _pct(v: float) -> float | None:
        return (v / input_kg * 100.0) if input_kg > 0 else None

    return {
        "carbon_black_kg": carbon_black,
        "metal_scrap_kg": metal_scrap,
        "gas_syngas_kg": gas_syngas,
        "h2o_kg": h2o,
        "losses_kg": losses,
        "total_kg": total,
        "carbon_black_pct": _pct(carbon_black),
        "metal_scrap_pct": _pct(metal_scrap),
        "gas_syngas_pct": _pct(gas_syngas),
        "h2o_pct": _pct(h2o),
        "losses_pct": _pct(losses),
        "total_pct": _pct(total),
    }


def _fetch_monthly(start: str, period: str) -> dict[str, Any]:
    raw = _psql_json(_monthly_query(start))
    if raw is None:
        raise SystemExit(f"No mv_mass_balance_monthly row for {period}.")
    input_kg = float(raw["input_kg"]) if raw.get("input_kg") is not None else 0.0
    closure_pct = (
        float(raw["closure_diff_pct"]) if raw.get("closure_diff_pct") is not None else 0.0
    )
    closure_kg = (closure_pct / 100.0) * input_kg
    eu_density = _fetch_density(start, "EU")
    plus_density = _fetch_density(start, "PLUS")
    return {
        "input_kg": input_kg,
        "eu_prod_kg": float(raw["eu_prod_kg"]) if raw.get("eu_prod_kg") is not None else 0.0,
        "plus_prod_kg": (
            float(raw["plus_prod_kg"]) if raw.get("plus_prod_kg") is not None else 0.0
        ),
        "eu_prod_litres": (
            float(raw["eu_prod_litres"]) if raw.get("eu_prod_litres") is not None else 0.0
        ),
        "plus_prod_litres": (
            float(raw["plus_prod_litres"]) if raw.get("plus_prod_litres") is not None else 0.0
        ),
        "c14_pct": None,
        "closure_diff_kg": closure_kg,
        "closure_diff_pct": closure_pct,
        "eu_density_kgl": eu_density,
        "plus_density_kgl": plus_density,
    }


def _fetch_suppliers(start: str, end: str) -> list[dict[str, Any]]:
    raw = _psql_json(_suppliers_query(start, end)) or []
    grand_total = sum(
        float(r["total_kg"]) for r in raw if r.get("total_kg") is not None
    ) or 0.0
    out: list[dict[str, Any]] = []
    for r in raw:
        kg = float(r["total_kg"]) if r.get("total_kg") is not None else 0.0
        share = (kg / grand_total * 100.0) if grand_total > 0 else 0.0
        out.append(
            {
                "name": r["name"],
                "cert_iscc_ref": r.get("cert_iscc_ref") or "—",
                "total_kg": round(kg, 2),
                "share_pct": round(share, 2),
            }
        )
    return out


def build_context(period: str) -> dict[str, Any]:
    period, label, start, end, submission_ref = _period_bounds(period)
    daily_rows = _fetch_daily(start, end)
    totals = _fetch_monthly(start, period)
    suppliers = _fetch_suppliers(start, end)
    byproducts = _fetch_byproducts(start, end, totals["input_kg"])
    short_year = period.split("-")[0][2:]
    short_month = _MONTH_NAMES[int(period.split("-")[1])][:3]
    period_short = f"{short_month} {short_year}"
    return {
        "submission_ref": submission_ref,
        "period": period,
        "period_label": label,
        "period_short": period_short,
        "generated_at": GENERATED_AT,
        "submitter_company": "OisteBio GmbH",
        "submitter_address": "Oberneuhofstrasse 5, 6340 Baar, Switzerland",
        "plant_name": "Girardot, Colombia",
        "feedstock": "ELT — End-of-Life Tyres",
        "product": "DEV-P100 — refined pyrolysis oil",
        "off_taker": "Crown Oil UK",
        "regulator": "UK DfT — LCF Delivery Unit",
        "totals": totals,
        "daily_rows": daily_rows,
        "suppliers": suppliers,
        "byproducts": byproducts,
        "annex_a_hash": None,
    }


def _patched_env_factory() -> Environment:
    base_env: Environment = _ORIGINAL_BUILD_ENV()
    base_env.filters["fmt_num"] = fmt_num
    base_env.filters["fmt_num_signed"] = fmt_num_signed
    base_env.filters["fmt_kg"] = fmt_kg
    base_env.filters["fmt_kg_signed"] = fmt_kg_signed
    base_env.filters["fmt_l"] = fmt_l
    base_env.filters["fmt_pct"] = fmt_pct
    base_env.filters["fmt_pct_signed"] = fmt_pct_signed
    base_env.filters["fmt_density"] = fmt_density
    return base_env


def render(out_pdf: Path, period: str) -> RenderResult:
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


def _default_output(period: str) -> Path:
    period, label, _, _, submission_ref = _period_bounds(period)
    month_lower = label.lower().replace(" ", "_")
    fname = f"02_mass_balance_{month_lower}_FINAL.pdf"
    return (
        _REPO_ROOT
        / "deliverables"
        / submission_ref
        / "01_annex_a_mass_balance"
        / fname
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Render Annex A monthly mass-balance PDF.")
    parser.add_argument("--period", default=_DEFAULT_PERIOD, help="YYYY-MM (default 2025-01)")
    parser.add_argument("--out", type=Path, default=None, help="Output PDF path")
    parser.add_argument("positional_out", nargs="?", type=Path, default=None,
                        help="Back-compat positional out path")
    args = parser.parse_args(argv[1:])
    out_pdf = args.out or args.positional_out or _default_output(args.period)
    out_pdf = out_pdf.resolve()
    result = render(out_pdf, args.period)

    size_kb = result.pdf_size_bytes / 1024
    on_disk_sha = hashlib.sha256(result.pdf_path.read_bytes()).hexdigest()

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
