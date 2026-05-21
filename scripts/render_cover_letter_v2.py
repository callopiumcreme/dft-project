"""Render the FINAL RTFO-310825 cover letter PDF (8-month bundle, Jan–Aug 2025).

Story: DFTEN-RTFO-310825. Produces
``00_cover_letter/00_cover_letter_FINAL.pdf`` for the UK DfT Track A
submission (8-month bundle). Signed PDF on OisteBio GmbH letterhead,
addressed to UK DfT LCF Delivery Unit c/o Crown Oil UK.

Bundle-level totals are read directly from ``mv_mass_balance_monthly``
(Jan–Aug 2025 aggregated), so this script has NO dependency on sibling
Annex A agents — it can render independently.

The body cites the SHA-256 anchors of the 8 monthly Annex A PDFs plus
Annex D stock carry-over, ISCC PoS status, supply-chain diagram.

Outstanding-items section:
1. Retrospective ISCC PoS for 3 collecting points (pending)
2. Supplier ISCC EU certificate library — filed in 03_supplier_evidence/certificates/
3. ELT RCF eligibility — audit-gated (NOT a blocking gap; evidence in bundle)
4. Closing stock 339.865 kg Jan→Feb carry-over — declared in Annex D

Usage:
    python scripts/render_cover_letter_v2.py [OUTPUT_PDF]
    # default: deliverables/RTFO-310825/00_cover_letter/00_cover_letter_FINAL.pdf

Uses the deterministic Jinja + WeasyPrint pipeline from
``backend.app.services.pdf_renderer`` for byte-stable output.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

DB_CONTAINER: Final[str] = "dft-project_db_1"
DB_USER: Final[str] = "dft"
DB_NAME: Final[str] = "dft"

if TYPE_CHECKING:
    from collections.abc import Callable

    from jinja2 import Environment

    from app.services.pdf_renderer import RenderResult  # type: ignore[import-not-found]

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
_BACKEND_DIR: Final[Path] = _REPO_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.services import pdf_renderer  # type: ignore[import-not-found]  # noqa: E402

_ORIGINAL_BUILD_ENV: Final = pdf_renderer._build_env

TEMPLATE_NAME: Final[str] = "cover_letter_v2.html"
BUNDLE_ROOT: Final[Path] = _REPO_ROOT / "deliverables" / "RTFO-310825"
DEFAULT_OUTPUT: Final[Path] = (
    BUNDLE_ROOT / "00_cover_letter" / "00_cover_letter_FINAL.pdf"
)

# Jan→Feb carry-over — documented in Annex D; symmetric 339.865 kg carry-over.
CLOSING_STOCK_KG: Final[float] = 339.865

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

# Ordered list of the 8 monthly Annex A FINAL PDFs (for hash anchors + attachments).
MONTHS_ORDERED: Final[list[dict[str, str]]] = [
    {"month": "January 2025",  "file": "01_annex_a_mass_balance/02_mass_balance_january_2025_FINAL.pdf"},
    {"month": "February 2025", "file": "01_annex_a_mass_balance/02_mass_balance_february_2025_FINAL.pdf"},
    {"month": "March 2025",    "file": "01_annex_a_mass_balance/02_mass_balance_march_2025_FINAL.pdf"},
    {"month": "April 2025",    "file": "01_annex_a_mass_balance/02_mass_balance_april_2025_FINAL.pdf"},
    {"month": "May 2025",      "file": "01_annex_a_mass_balance/02_mass_balance_may_2025_FINAL.pdf"},
    {"month": "June 2025",     "file": "01_annex_a_mass_balance/02_mass_balance_june_2025_FINAL.pdf"},
    {"month": "July 2025",     "file": "01_annex_a_mass_balance/02_mass_balance_july_2025_FINAL.pdf"},
    {"month": "August 2025",   "file": "01_annex_a_mass_balance/02_mass_balance_august_2025_FINAL.pdf"},
]

# Conversion log PDFs (8 months).
CONV_LOGS: Final[list[dict[str, str]]] = [
    {"month": "January 2025",  "file": "02_ros_export/05_production_conversion_logs_january_2025.pdf"},
    {"month": "February 2025", "file": "02_ros_export/05_production_conversion_logs_february_2025.pdf"},
    {"month": "March 2025",    "file": "02_ros_export/05_production_conversion_logs_march_2025.pdf"},
    {"month": "April 2025",    "file": "02_ros_export/05_production_conversion_logs_april_2025.pdf"},
    {"month": "May 2025",      "file": "02_ros_export/05_production_conversion_logs_may_2025.pdf"},
    {"month": "June 2025",     "file": "02_ros_export/05_production_conversion_logs_june_2025.pdf"},
    {"month": "July 2025",     "file": "02_ros_export/05_production_conversion_logs_july_2025.pdf"},
    {"month": "August 2025",   "file": "02_ros_export/05_production_conversion_logs_august_2025.pdf"},
]

# Static reference artifacts (shared across all 8 months).
STATIC_ANCHORS: Final[list[tuple[str, str]]] = [
    (
        "ISCC PoS Status (3 collecting points)",
        "03_supplier_evidence/03_iscc_pos_status.pdf",
    ),
    (
        "Supply Chain Diagram",
        "04_compliance/01_supply_chain_diagram.pdf",
    ),
    (
        "Annex D — Stock Carry-over Jan→Feb 2025",
        "06_annex_d_stock_carryover/07_stock_carryover_jan_feb_2025.pdf",
    ),
]


# ---------------------------------------------------------------------------
# Jinja numeric filters — match Annex A FINAL / Annex D conventions.
# ---------------------------------------------------------------------------
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
    return f"{_format_thousands(float(value), decimals=3)} kg"


def fmt_pct(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{_format_thousands(float(value), decimals=2)} %"


# ---------------------------------------------------------------------------
# Read side-car digests directly from bundle.
# ---------------------------------------------------------------------------
def _read_sha256(sidecar: Path) -> str:
    """Parse the first hex token from a ``sha256sum -c`` sidecar."""
    text = sidecar.read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit(f"Empty sidecar: {sidecar}")
    return text.split()[0]


def _sha256_or_missing(target: Path) -> str:
    """Return SHA-256 from sidecar if available, else '(file not yet rendered)'."""
    sidecar = target.with_suffix(target.suffix + ".sha256")
    if sidecar.is_file():
        return _read_sha256(sidecar)
    if target.is_file():
        import hashlib as _hl
        h = _hl.sha256()
        with target.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    return "(not yet rendered)"


def _hash_anchors() -> list[dict[str, str]]:
    """Return the hash-table rows for the cover letter integrity block."""
    rows: list[dict[str, str]] = []

    # 8 Annex A monthly PDFs.
    for m in MONTHS_ORDERED:
        target = BUNDLE_ROOT / m["file"]
        rows.append({
            "label": f"Annex A — Mass Balance {m['month']}",
            "path": m["file"],
            "sha256": _sha256_or_missing(target),
        })

    # Static reference anchors.
    for label, rel in STATIC_ANCHORS:
        target = BUNDLE_ROOT / rel
        rows.append({
            "label": label,
            "path": rel,
            "sha256": _sha256_or_missing(target),
        })

    return rows


def build_context() -> dict[str, Any]:
    bundle_totals = _fetch_bundle_totals()
    return {
        "submission_ref": "RTFO-310825",
        "period": "January–August 2025",
        "rtfo_period": "RTFO obligation year 2024/2025",
        "calendar_days": "243",
        "production_months": "8",
        "months_list": "January, February, March, April, May, June, July, August 2025",
        "generated_at": "21 May 2026",
        "submission_date_label": "21 May 2026",
        "draft_status": "FINAL — 8-month bundle freeze",
        "submitter_company": "OisteBio GmbH",
        "submitter_address": "Oberneuhofstrasse 5, 6340 Baar, Switzerland",
        "submitter_vat": "CHE-234.625.162",
        "submitter_contact": "compliance@oistebio.com",
        "intermediary_label": (
            "Crown Oil Ltd — RTFO obligated supplier (intermediary)"
        ),
        "off_taker": "Crown Oil Ltd (United Kingdom)",
        "feedstock": "End-of-Life Tyres (ELT)",
        "product": "DEV-P100 refined pyrolysis oil",
        "stock_carryover_kg": CLOSING_STOCK_KG,
        "manifest_hash_short": "see MANIFEST.sha256",
        # Bundle-level production totals (Jan–Aug 2025 aggregate from MV).
        "input_total_kg": bundle_totals["input_total_kg"],
        "eu_prod_kg": bundle_totals["eu_prod_kg"],
        "plus_prod_kg": bundle_totals["plus_prod_kg"],
        "eu_prod_litres": bundle_totals["eu_prod_litres"],
        "plus_prod_litres": bundle_totals["plus_prod_litres"],
        "gas_syngas_m3": bundle_totals["gas_syngas_m3"],
        # Hash anchors table.
        "hash_anchors": _hash_anchors(),
        # Annex A file list for attachments section.
        "annex_a_files": MONTHS_ORDERED,
    }


def _patched_env_factory() -> "Environment":
    base_env: "Environment" = _ORIGINAL_BUILD_ENV()
    base_env.filters["fmt_num"] = fmt_num
    base_env.filters["fmt_kg"] = fmt_kg
    base_env.filters["fmt_pct"] = fmt_pct
    return base_env


def render(out_pdf: Path) -> "RenderResult":
    pdf_renderer._build_env = _patched_env_factory
    try:
        result: "RenderResult" = pdf_renderer.render_to_pdf(
            template_name=TEMPLATE_NAME,
            context=build_context(),
            output_path=out_pdf,
        )
        return result
    finally:
        pdf_renderer._build_env = _ORIGINAL_BUILD_ENV


def main(argv: list[str]) -> int:
    out_pdf = Path(argv[1]) if len(argv) > 1 else DEFAULT_OUTPUT
    out_pdf = out_pdf.resolve()
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
    print(f"Sanity (UTC now): {datetime.now(UTC).isoformat()}")

    if on_disk_sha != result.pdf_sha256:
        print(
            "ERROR: on-disk SHA-256 differs from renderer-reported digest",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
