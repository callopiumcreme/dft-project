"""Render the RTFO Pathway Declaration PDF for the RTFO-310825 bundle.

Single-issuance compliance artefact: OisteBio's declaration of the
ELT→pyrolysis→DEV-P100 production pathway under UK RTFO Chapter 9 (RCF),
signed by Paolo Ughetti (Managing Director). Mass-balance methodology cites
ISCC EU System Document 203; ISCC EU cert ref pinned to LV227-00000597.

DB-driven bundle-level volumes pulled from ``mv_mass_balance_monthly``
(Jan–Aug 2025 aggregated), same source as the cover letter — single source
of truth, no drift between the two artefacts.

Deterministic SHA-256 via shared ``app.services.pdf_renderer`` pipeline
(fixed ``generated_at``, no XMP metadata, full-font embed).

Usage::

    python3 scripts/render_pathway_declaration.py [--out PATH]

Default output:
``deliverables/RTFO-310825/04_compliance/rtfo_pathway_declaration/08_rtfo_pathway_declaration_FINAL.pdf``
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
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

TEMPLATE_NAME: Final[str] = "rtfo_pathway_declaration.html"
GENERATED_AT: Final[str] = "2026-05-21T00:00:00Z"
GENERATED_AT_DATE: Final[str] = "2026-05-21"
SUBMISSION_REF: Final[str] = "RTFO-310825"

DB_CONTAINER: Final[str] = "dft-project_db_1"
DB_USER: Final[str] = "dft"
DB_NAME: Final[str] = "dft"

ISCC_EU_CERT_REF: Final[str] = "LV227-00000597"
ISCC_EU_CERT_BODY: Final[str] = "ISCC certification body LV227 (Latvia)"

_BUNDLE_TOTALS_QUERY: Final[str] = """
SELECT json_build_object(
    'input_total_kg',   COALESCE(SUM(input_total_kg), 0)::float8,
    'eu_prod_kg',       COALESCE(SUM(eu_prod_kg), 0)::float8,
    'plus_prod_kg',     COALESCE(SUM(plus_prod_kg), 0)::float8,
    'eu_prod_litres',   COALESCE(SUM(eu_prod_litres), 0)::float8,
    'plus_prod_litres', COALESCE(SUM(plus_prod_litres), 0)::float8,
    'gas_syngas_m3',    COALESCE(SUM(gas_syngas_m3), 0)::float8
)
FROM mv_mass_balance_monthly
WHERE month >= DATE '2025-01-01'
  AND month <= DATE '2025-08-01';
"""

_SUPPLIER_COUNT_QUERY: Final[str] = """
SELECT COUNT(DISTINCT s.id)::int
FROM daily_inputs di
JOIN suppliers s ON s.id = di.supplier_id
WHERE di.deleted_at IS NULL
  AND s.deleted_at IS NULL
  AND di.entry_date >= DATE '2025-01-01'
  AND di.entry_date <= DATE '2025-08-31';
"""


def _format_thousands(value: float, decimals: int = 2) -> str:
    rounded = round(float(value), decimals)
    formatted = f"{rounded:,.{decimals}f}"
    return formatted.replace(",", " ").replace(".", ",")


def fmt_num(value: float | int | None) -> str:
    if value is None:
        return "—"
    return _format_thousands(float(value), decimals=2)


def fmt_kg(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{_format_thousands(float(value), decimals=2)} kg"


def _psql_json(query: str) -> Any:
    cmd = [
        "docker", "exec", DB_CONTAINER,
        "psql", "-U", DB_USER, "-d", DB_NAME,
        "-At", "-c", query,
    ]
    completed = subprocess.run(  # noqa: S603
        cmd, check=True, capture_output=True, text=True,
    )
    payload = completed.stdout.strip()
    if not payload or payload == "\\N":
        return None
    if payload.lstrip("-").isdigit():
        return int(payload)
    return json.loads(payload)


def _fetch_bundle_totals() -> dict[str, float]:
    return _psql_json(_BUNDLE_TOTALS_QUERY) or {
        "input_total_kg": 0.0,
        "eu_prod_kg": 0.0,
        "plus_prod_kg": 0.0,
        "eu_prod_litres": 0.0,
        "plus_prod_litres": 0.0,
        "gas_syngas_m3": 0.0,
    }


def _fetch_supplier_count() -> int:
    raw = _psql_json(_SUPPLIER_COUNT_QUERY)
    return int(raw or 0)


def build_context() -> dict[str, Any]:
    totals = _fetch_bundle_totals()
    supplier_count = _fetch_supplier_count()
    return {
        "submission_ref": SUBMISSION_REF,
        "period_label": "January–August 2025",
        "period_start": "2025-01-01",
        "period_end": "2025-08-31",
        "generated_at": GENERATED_AT,
        "generated_at_date": GENERATED_AT_DATE,
        "submitter_company": "OisteBio GmbH",
        "submitter_address": "Oberneuhofstrasse 5, 6340 Baar, Switzerland",
        "submitter_vat": "CHE-234.625.162",
        "plant_name": "Girardot, Cundinamarca — Colombia",
        "feedstock": "End-of-Life Tyres (ELT)",
        "product": "DEV-P100 — refined pyrolysis oil",
        "off_taker": "Crown Oil Limited (United Kingdom)",
        "iscc_eu_cert_ref": ISCC_EU_CERT_REF,
        "iscc_eu_cert_body": ISCC_EU_CERT_BODY,
        "signatory_name": "Paolo Ughetti",
        "signatory_role": "Managing Director / Chairman / Gesellschafter",
        "supplier_count": supplier_count,
        "input_total_kg": round(float(totals["input_total_kg"]), 2),
        "eu_prod_kg": round(float(totals["eu_prod_kg"]), 2),
        "plus_prod_kg": round(float(totals["plus_prod_kg"]), 2),
        "eu_prod_litres": round(float(totals["eu_prod_litres"]), 2),
        "plus_prod_litres": round(float(totals["plus_prod_litres"]), 2),
        "gas_syngas_m3": round(float(totals["gas_syngas_m3"]), 2),
    }


def _patched_env_factory() -> Environment:
    base_env: Environment = _ORIGINAL_BUILD_ENV()
    base_env.filters["fmt_num"] = fmt_num
    base_env.filters["fmt_kg"] = fmt_kg
    return base_env


def render(out_pdf: Path) -> RenderResult:
    pdf_renderer._build_env = _patched_env_factory
    try:
        result: RenderResult = pdf_renderer.render_to_pdf(
            template_name=TEMPLATE_NAME,
            context=build_context(),
            output_path=out_pdf,
        )
        return result
    finally:
        pdf_renderer._build_env = _ORIGINAL_BUILD_ENV


def _default_output() -> Path:
    return (
        _REPO_ROOT
        / "deliverables"
        / SUBMISSION_REF
        / "04_compliance"
        / "rtfo_pathway_declaration"
        / "08_rtfo_pathway_declaration_FINAL.pdf"
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Render RTFO pathway declaration PDF.")
    parser.add_argument("--out", type=Path, default=None, help="Output PDF path")
    args = parser.parse_args(argv[1:])

    out_pdf = (args.out or _default_output()).resolve()
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    result = render(out_pdf)

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
