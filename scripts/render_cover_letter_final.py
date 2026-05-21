"""Render the FINAL RTFO-310125 cover letter PDF (Day 6 freeze).

Story: E1-S1.17 / DFTEN-111. Produces
``00_cover_letter/00_cover_letter_FINAL.pdf`` for the UK DfT Track A
submission. Signed PDF on OisteBio GmbH letterhead, addressed to UK DfT
LCF Delivery Unit c/o Crown Oil UK.

The body cites the SHA-256 anchors of all principal annexes:
- Annex A FINAL (mass balance)
- Annex D (07_stock_carryover_explanation.pdf)
- 03_iscc_pos_status.pdf
- 05_production_conversion_logs_january_2025.pdf
- 06_audit_trail_export_january_2025.csv
- 01_supply_chain_diagram.pdf

Outstanding-items section lists the formally-disclosed gaps:
1. ISCC PoS chain for 3 collecting points (Litoplas/Biowaste/Esenttia) — pending
2. Supplier ISCC EU certificate library — filed in 03_supplier_evidence/certificates/
3. Closing stock 339.865 kg retained at Girardot — declared in Annex D

Uses the deterministic Jinja + WeasyPrint pipeline from
``backend.app.services.pdf_renderer`` for byte-stable output.
"""

from __future__ import annotations

import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

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

TEMPLATE_NAME: Final[str] = "cover_letter_final.html"
BUNDLE_ROOT: Final[Path] = _REPO_ROOT / "deliverables" / "RTFO-310125"
DEFAULT_OUTPUT: Final[Path] = (
    BUNDLE_ROOT / "00_cover_letter" / "00_cover_letter_FINAL.pdf"
)

CLOSING_STOCK_KG: Final[float] = 339.865


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


def _hash_anchors() -> list[dict[str, str]]:
    """Return the hash-table rows for the cover letter integrity block."""
    anchors = [
        (
            "Annex A — Mass Balance January 2025",
            "01_annex_a_mass_balance/02_mass_balance_january_2025_FINAL.pdf",
        ),
        (
            "Annex D — Stock Carry-over Explanation",
            "01_annex_a_mass_balance/07_stock_carryover_explanation.pdf",
        ),
        (
            "ISCC PoS Status (3 collecting points)",
            "03_supplier_evidence/03_iscc_pos_status.pdf",
        ),
        (
            "Production Conversion Log",
            "02_ros_export/05_production_conversion_logs_january_2025.pdf",
        ),
        (
            "Audit Trail Export (CSV)",
            "05_audit_trail/06_audit_trail_export_january_2025.csv",
        ),
        (
            "Supply Chain Diagram",
            "04_compliance/01_supply_chain_diagram.pdf",
        ),
    ]
    rows: list[dict[str, str]] = []
    for label, rel in anchors:
        target = BUNDLE_ROOT / rel
        sidecar = target.with_suffix(target.suffix + ".sha256")
        if not sidecar.is_file():
            raise SystemExit(f"Missing sidecar: {sidecar}")
        rows.append(
            {
                "label": label,
                "path": rel,
                "sha256": _read_sha256(sidecar),
            }
        )
    return rows


def build_context() -> dict[str, Any]:
    return {
        "submission_ref": "RTFO-310125",
        "period": "January 2025",
        "rtfo_period": "RTFO obligation year 2024/2025",
        "generated_at": "20 May 2026",
        "submission_date_label": "21 May 2026",
        "draft_status": "FINAL — Day 6 bundle freeze",
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
        "hash_anchors": _hash_anchors(),
    }


def _patched_env_factory() -> Environment:
    base_env: Environment = _ORIGINAL_BUILD_ENV()
    base_env.filters["fmt_num"] = fmt_num
    base_env.filters["fmt_kg"] = fmt_kg
    base_env.filters["fmt_pct"] = fmt_pct
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
