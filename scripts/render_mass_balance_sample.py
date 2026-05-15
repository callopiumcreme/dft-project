"""Render a sample Annex A mass-balance PDF for QA (DFTEN-98 / E1-S1.4).

Usage:
    python3 scripts/render_mass_balance_sample.py [out_pdf]

Produces ``mass_balance_sample.pdf`` at the repo root by default, using
deterministic synthetic data for the 31 days of January 2025 plus five
mock ELT suppliers. WeasyPrint is invoked directly; no FastAPI or DB
dependencies are required.
"""

from __future__ import annotations

import random
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = REPO_ROOT / "templates" / "reports"
TEMPLATE_NAME = "mass_balance.html"

# Product densities at 15 °C — see methodology section of the template.
DENSITY_EU = 0.78
DENSITY_PLUS = 0.856

# Deterministic seed so the sample PDF stays reproducible across reruns.
RNG_SEED = 20250131


# ---------------------------------------------------------------------------
# Jinja numeric filters
# ---------------------------------------------------------------------------
def _format_thousands(value: float, decimals: int = 2) -> str:
    """Format a number with a thin-space thousands separator and ``decimals`` places."""
    rounded = round(float(value), decimals)
    # Use a non-breaking thin space (U+202F) for the thousands separator, comma for decimal.
    formatted = f"{rounded:,.{decimals}f}"
    return formatted.replace(",", " ").replace(".", ",")  # noqa: RUF001


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


# ---------------------------------------------------------------------------
# Mock data builders
# ---------------------------------------------------------------------------
def _build_daily_rows(rng: random.Random) -> list[dict[str, Any]]:
    """Generate 31 plausible daily rows for January 2025."""
    rows: list[dict[str, Any]] = []
    day = date(2025, 1, 1)
    for _ in range(31):
        # Plant nominal throughput: ~10-14 t/day of ELT input.
        input_kg = round(rng.uniform(10_000, 14_000), 2)
        # Pyrolysis oil yield ~40-48 % of input mass.
        total_out_kg = round(input_kg * rng.uniform(0.40, 0.48), 2)
        # Split EU / PLUS roughly 70 / 30 with a bit of jitter.
        eu_kg = round(total_out_kg * rng.uniform(0.65, 0.75), 2)
        plus_kg = round(total_out_kg - eu_kg, 2)
        eu_l = round(eu_kg / DENSITY_EU, 2)
        plus_l = round(plus_kg / DENSITY_PLUS, 2)
        # C14 biogenic fraction — should be very low for ELT (fossil feedstock).
        c14_pct = round(rng.uniform(0.4, 1.2), 2)
        # Closure: tiny mass-balance drift around zero, ±0.5 % of input.
        closure_kg = round(rng.uniform(-0.005, 0.005) * input_kg, 2)
        rows.append(
            {
                "date": day.isoformat(),
                "input_kg": input_kg,
                "eu_prod_kg": eu_kg,
                "plus_prod_kg": plus_kg,
                "eu_prod_litres": eu_l,
                "plus_prod_litres": plus_l,
                "c14_pct": c14_pct,
                "closure_diff_kg": closure_kg,
            }
        )
        day += timedelta(days=1)
    return rows


def _build_totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_input = sum(r["input_kg"] for r in rows)
    total_eu_kg = sum(r["eu_prod_kg"] for r in rows)
    total_plus_kg = sum(r["plus_prod_kg"] for r in rows)
    total_eu_l = sum(r["eu_prod_litres"] for r in rows)
    total_plus_l = sum(r["plus_prod_litres"] for r in rows)
    # Weighted-average C14 by input mass.
    weighted_c14 = (
        sum(r["c14_pct"] * r["input_kg"] for r in rows) / total_input if total_input else 0.0
    )
    closure_kg = sum(r["closure_diff_kg"] for r in rows)
    closure_pct = (closure_kg / total_input * 100) if total_input else 0.0
    return {
        "input_kg": round(total_input, 2),
        "eu_prod_kg": round(total_eu_kg, 2),
        "plus_prod_kg": round(total_plus_kg, 2),
        "eu_prod_litres": round(total_eu_l, 2),
        "plus_prod_litres": round(total_plus_l, 2),
        "c14_pct": round(weighted_c14, 2),
        "closure_diff_kg": round(closure_kg, 2),
        "closure_diff_pct": round(closure_pct, 4),
    }


def _build_suppliers(rng: random.Random, total_input_kg: float) -> list[dict[str, Any]]:
    """Five mock ELT suppliers with ISCC EU references, shares summing to 100 %."""
    names = [
        "Reciclajes Andinos S.A.S.",
        "NeumáticosVerde Bogotá Ltda.",
        "TyreCycle Caribe S.A.",
        "EcoLLantas Medellín S.A.S.",
        "ELT Colectiva Cali Coop.",
    ]
    iscc_refs = [
        "EU-ISCC-COC-2024-AR-001",
        "EU-ISCC-COC-2024-NV-014",
        "EU-ISCC-COC-2024-TC-022",
        "EU-ISCC-COC-2024-EL-038",
        "EU-ISCC-COC-2024-EC-045",
    ]
    # Dirichlet-like shares: random weights, then normalise.
    weights = [rng.uniform(0.5, 2.0) for _ in names]
    weight_sum = sum(weights)
    shares = [w / weight_sum for w in weights]
    suppliers: list[dict[str, Any]] = []
    for name, iscc, share in zip(names, iscc_refs, shares, strict=True):
        kg = round(total_input_kg * share, 2)
        suppliers.append(
            {
                "name": name,
                "cert_iscc_ref": iscc,
                "total_kg": kg,
                "share_pct": round(share * 100, 2),
            }
        )
    # Reconcile last supplier kg to exact total to avoid rounding drift.
    delta = round(total_input_kg - sum(s["total_kg"] for s in suppliers), 2)
    suppliers[-1]["total_kg"] = round(suppliers[-1]["total_kg"] + delta, 2)
    return suppliers


def build_context() -> dict[str, Any]:
    # S311: mock QA data, not cryptographic; deterministic seed is intentional.
    rng = random.Random(RNG_SEED)  # noqa: S311
    daily_rows = _build_daily_rows(rng)
    totals = _build_totals(daily_rows)
    suppliers = _build_suppliers(rng, totals["input_kg"])
    return {
        "submission_ref": "RTFO-310125",
        "period": "2025-01",
        "period_label": "Gennaio 2025",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
        "annex_a_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
def _build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["fmt_num"] = fmt_num
    env.filters["fmt_num_signed"] = fmt_num_signed
    env.filters["fmt_kg"] = fmt_kg
    env.filters["fmt_kg_signed"] = fmt_kg_signed
    env.filters["fmt_l"] = fmt_l
    env.filters["fmt_pct"] = fmt_pct
    env.filters["fmt_pct_signed"] = fmt_pct_signed
    return env


def render(out_pdf: Path) -> Path:
    env = _build_env()
    template = env.get_template(TEMPLATE_NAME)
    html_str = template.render(**build_context())
    HTML(string=html_str, base_url=str(TEMPLATE_DIR)).write_pdf(str(out_pdf))
    return out_pdf


def main(argv: list[str]) -> int:
    out_pdf = Path(argv[1]) if len(argv) > 1 else REPO_ROOT / "mass_balance_sample.pdf"
    out_pdf = out_pdf.resolve()
    rendered = render(out_pdf)
    size_kb = rendered.stat().st_size / 1024
    print(f"Rendered: {rendered}  ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
