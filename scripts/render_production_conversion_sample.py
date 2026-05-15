"""Render a sample Production Conversion Log PDF for QA (DFTEN-104 / E1-S1.10).

Usage:
    python3 scripts/render_production_conversion_sample.py [out_pdf]

Produces ``production_conversion_sample.pdf`` at the repo root by default,
using deterministic synthetic data for the 31 days of January 2025.

The PDF documents per-day kg-to-litre conversion using product densities
EU 0.78 kg/L and PLUS 0.856 kg/L, mirroring the GENERATED ALWAYS columns
introduced by Alembic migration 0007_persist_production_litres.py on the
daily_production table.

WeasyPrint is invoked directly; no FastAPI or DB dependencies required.
"""

from __future__ import annotations

import hashlib
import random
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

if TYPE_CHECKING:
    from collections.abc import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = REPO_ROOT / "templates" / "reports"
TEMPLATE_NAME = "production_conversion.html"

# Product densities at 15 °C — see migration 0005_seed_product_densities.py
# and migration 0007_persist_production_litres.py.
DENSITY_EU = 0.78
DENSITY_PLUS = 0.856

# Deterministic seed so the sample PDF stays reproducible across reruns.
RNG_SEED = 20250131


# ---------------------------------------------------------------------------
# Jinja numeric filters (lifted from scripts/render_mass_balance_sample.py
# so this report keeps Worker F's thin-space-thousands convention).
# ---------------------------------------------------------------------------
def _format_thousands(value: float, decimals: int = 2) -> str:
    """Format a number with a thin-space thousands separator and comma decimal."""
    rounded = round(float(value), decimals)
    # Non-breaking thin space (U+202F) for thousands; comma for decimal.
    formatted = f"{rounded:,.{decimals}f}"
    return formatted.replace(",", " ").replace(".", ",")  # noqa: RUF001


def fmt_num(value: float | int | None) -> str:
    if value is None:
        return "—"
    return _format_thousands(float(value), decimals=2)


def fmt_kg(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{_format_thousands(float(value), decimals=2)} kg"


def fmt_l(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{_format_thousands(float(value), decimals=2)} L"


def fmt_density(value: float | int | None) -> str:
    """Render a density as ``0,780 kg/L`` (three decimals + unit)."""
    if value is None:
        return "—"
    return f"{_format_thousands(float(value), decimals=3)} kg/L"


def fmt_density_plain(value: float | int | None) -> str:
    """Render a density as ``0,780`` (three decimals, no unit) for table cells."""
    if value is None:
        return "—"
    return _format_thousands(float(value), decimals=3)


# ---------------------------------------------------------------------------
# Mock data builders
# ---------------------------------------------------------------------------
def _build_daily_rows(rng: random.Random) -> list[dict[str, Any]]:
    """Generate 31 plausible daily production rows for January 2025.

    Range mirrors the spec: EU 800-1200 kg, PLUS 600-900 kg per day.
    """
    rows: list[dict[str, Any]] = []
    day = date(2025, 1, 1)
    for _ in range(31):
        eu_kg = round(rng.uniform(800.0, 1200.0), 2)
        plus_kg = round(rng.uniform(600.0, 900.0), 2)
        eu_l = round(eu_kg / DENSITY_EU, 2)
        plus_l = round(plus_kg / DENSITY_PLUS, 2)
        rows.append(
            {
                "date": day.isoformat(),
                "eu_prod_kg": eu_kg,
                "plus_prod_kg": plus_kg,
                "eu_prod_litres": eu_l,
                "plus_prod_litres": plus_l,
                "notes": "",
            }
        )
        day += timedelta(days=1)
    return rows


def _build_totals(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows_list = list(rows)
    total_eu_kg = sum(float(r["eu_prod_kg"]) for r in rows_list)
    total_plus_kg = sum(float(r["plus_prod_kg"]) for r in rows_list)
    total_eu_l = sum(float(r["eu_prod_litres"]) for r in rows_list)
    total_plus_l = sum(float(r["plus_prod_litres"]) for r in rows_list)
    return {
        "eu_prod_kg": round(total_eu_kg, 2),
        "plus_prod_kg": round(total_plus_kg, 2),
        "eu_prod_litres": round(total_eu_l, 2),
        "plus_prod_litres": round(total_plus_l, 2),
        "grand_total_litres": round(total_eu_l + total_plus_l, 2),
    }


def build_context() -> dict[str, Any]:
    # S311: mock QA data, not cryptographic; deterministic seed is intentional.
    rng = random.Random(RNG_SEED)  # noqa: S311
    daily_rows = _build_daily_rows(rng)
    totals = _build_totals(daily_rows)
    return {
        "submission_ref": "RTFO-310125",
        "period": "2025-01",
        "period_label": "January 2025",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "submitter_company": "OisteBio GmbH",
        "submitter_address": "Oberneuhofstrasse 5, 6340 Baar, Switzerland",
        "plant_name": "Girardot, Colombia",
        "product": "DEV-P100 — refined pyrolysis oil",
        "product_eu_code": "DEV-P100-EU",
        "product_plus_code": "DEV-P100-PLUS",
        "off_taker": "Crown Oil UK",
        "regulator": "UK DfT — LCF Delivery Unit",
        "density_eu": DENSITY_EU,
        "density_plus": DENSITY_PLUS,
        "totals": totals,
        "daily_rows": daily_rows,
        # Stable placeholder hash (matches sibling report convention).
        "doc_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
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
    env.filters["fmt_kg"] = fmt_kg
    env.filters["fmt_l"] = fmt_l
    env.filters["fmt_density"] = fmt_density
    env.filters["fmt_density_plain"] = fmt_density_plain
    return env


def render(out_pdf: Path) -> Path:
    env = _build_env()
    template = env.get_template(TEMPLATE_NAME)
    html_str = template.render(**build_context())
    HTML(string=html_str, base_url=str(TEMPLATE_DIR)).write_pdf(str(out_pdf))
    return out_pdf


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str]) -> int:
    out_pdf = Path(argv[1]) if len(argv) > 1 else REPO_ROOT / "production_conversion_sample.pdf"
    out_pdf = out_pdf.resolve()
    rendered = render(out_pdf)
    size_kb = rendered.stat().st_size / 1024
    sha256_hex = _sha256_of(rendered)
    print(f"Rendered: {rendered}  ({size_kb:.1f} KB)")
    print(f"SHA-256:  {sha256_hex}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
