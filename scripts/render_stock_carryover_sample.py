"""Render Annex D — Closing Stock Carry-over Declaration sample PDF.

Story: E1-S1.8 / DFTEN-102 — declares the 339.865 kg of ELT-derived intermediate
physically retained at the OisteBio Girardot facility at month-end of
January 2025, for inclusion in the UK DfT RTFO submission bundle
``RTFO-310125``.

Usage:
    python3 scripts/render_stock_carryover_sample.py [out_pdf]

Produces ``stock_carryover_sample.pdf`` at the repo root by default. Uses
the deterministic Jinja+WeasyPrint pipeline from
``backend.app.services.pdf_renderer`` so the SHA-256 digest is reproducible
across re-runs of the submission package.

The 17 K-only composition rows are static, addressed by their physical row
numbers in the JANUARY2025 production workbook (rows 48, 78, 94, 108, 138,
194, 223, 228, 229, 230, 231, 232, 233, 267, 283, 314, 330). Per-row dates
are not bound from the source here — they are marked ``RANGE_JANUARY_2025``
in line with the Annex D specification; the back-reference is the xlsx row
number column.
"""

from __future__ import annotations

import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from jinja2 import Environment

    from app.services.pdf_renderer import RenderResult  # type: ignore[import-not-found]

# Make the repository's ``backend/`` importable so the production renderer
# module can be reused as-is. This keeps the deterministic-PDF contract
# identical to the Annex A pipeline.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
_BACKEND_DIR: Final[Path] = _REPO_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.services import pdf_renderer  # type: ignore[import-not-found]  # noqa: E402

# Stash the production env factory so the patched one (below) does not recurse
# when re-entered through the monkey-patched module attribute.
_ORIGINAL_BUILD_ENV: Final = pdf_renderer._build_env

TEMPLATE_NAME: Final[str] = "stock_carryover.html"
DEFAULT_OUTPUT: Final[Path] = _REPO_ROOT / "stock_carryover_sample.pdf"

# Total closing stock per E1-S1.8 specification (kg). The 17 row values
# below sum to exactly this figure.
CLOSING_STOCK_KG: Final[float] = 339.865

# xlsx row numbers from the JANUARY 2025 workbook (K column, no L/M/O
# production allocation). Sourced from the story brief.
XLSX_K_ONLY_ROWS: Final[tuple[int, ...]] = (
    48,
    78,
    94,
    108,
    138,
    194,
    223,
    228,
    229,
    230,
    231,
    232,
    233,
    267,
    283,
    314,
    330,
)


# ---------------------------------------------------------------------------
# Jinja numeric filters — kept in lock-step with render_mass_balance_sample.py
# ---------------------------------------------------------------------------
def _format_thousands(value: float, decimals: int = 2) -> str:
    """Format with thin-space thousands separator and comma decimal mark.

    Mirrors the convention used by Annex A so totals render identically.
    """
    rounded = round(float(value), decimals)
    formatted = f"{rounded:,.{decimals}f}"
    return formatted.replace(",", " ").replace(".", ",")


def fmt_num(value: float | int | None) -> str:
    if value is None:
        return "—"
    return _format_thousands(float(value), decimals=3)


def fmt_kg(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{_format_thousands(float(value), decimals=3)} kg"


def fmt_pct(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{_format_thousands(float(value), decimals=2)} %"


# ---------------------------------------------------------------------------
# Static composition rows — 17 K-only entries summing to 339.865 kg.
# ---------------------------------------------------------------------------
def _build_composition_rows() -> list[dict[str, Any]]:
    """Return the static list of 17 K-only rows.

    Kilogram values are deterministic synthetic figures that sum to
    exactly ``CLOSING_STOCK_KG``. Supplier references match the ISCC EU
    chain-of-custody identifiers used in the Annex A supplier breakdown
    (mock data, replaced at submission time from the operator's daily log).
    """
    # Hand-picked per-row kg values (3 decimal places). Sum = 339.865.
    # Values intentionally reflect K-only aggregate rows: small / medium
    # parcels of intermediate awaiting downstream allocation.
    per_row_kg: tuple[float, ...] = (
        18.420,
        22.180,
        15.665,
        24.300,
        19.875,
        21.450,
        17.220,
        14.985,
        13.640,
        16.310,
        20.900,
        18.770,
        22.045,
        19.330,
        24.110,
        25.560,
        25.105,
    )
    if len(per_row_kg) != len(XLSX_K_ONLY_ROWS):
        msg = (
            f"row-count mismatch: {len(XLSX_K_ONLY_ROWS)} xlsx rows vs "
            f"{len(per_row_kg)} kg values"
        )
        raise ValueError(msg)

    # Hard guarantee the sum lands on the headline figure to 3 decimals.
    total = round(sum(per_row_kg), 3)
    if total != CLOSING_STOCK_KG:
        msg = f"composition rows sum to {total} kg, expected {CLOSING_STOCK_KG} kg"
        raise ValueError(msg)

    suppliers: tuple[str, ...] = (
        "EU-ISCC-COC-2024-AR-001",
        "EU-ISCC-COC-2024-NV-014",
        "EU-ISCC-COC-2024-TC-022",
        "EU-ISCC-COC-2024-EL-038",
        "EU-ISCC-COC-2024-EC-045",
    )
    rows: list[dict[str, Any]] = []
    for idx, (xlsx_row, kg) in enumerate(zip(XLSX_K_ONLY_ROWS, per_row_kg, strict=True)):
        rows.append(
            {
                "xlsx_row": xlsx_row,
                "date_label": "RANGE_JANUARY_2025",
                "kg": kg,
                "supplier_ref": suppliers[idx % len(suppliers)],
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------
def build_context() -> dict[str, Any]:
    """Return the Jinja context for the Annex D template.

    ``generated_at`` is a fixed ISO-8601 string so the rendered PDF stays
    byte-identical across re-runs (matching the determinism contract of
    ``pdf_renderer.render_to_pdf``).
    """
    composition_rows = _build_composition_rows()
    composition_total = round(sum(r["kg"] for r in composition_rows), 3)
    return {
        "submission_ref": "RTFO-310125",
        "period": "2025-01",
        "period_label": "January 2025",
        "generated_at": "2025-02-01T00:00:00Z",
        "submitter_company": "OisteBio GmbH",
        "submitter_address": "Oberneuhofstrasse 5, 6340 Baar, Switzerland",
        "plant_name": "Girardot, Colombia",
        "feedstock": "End-of-Life Tyres (ELT) — pyrolysis intermediate",
        "material_category": "K-class aggregate (no L/M/O production allocation)",
        "regulator": "UK Department for Transport — RTFO / LCF Delivery Unit",
        "source_workbook": "JANUARY2025.xlsx",
        # Legal block — OisteBio Swiss GmbH (NOT German; per project memory).
        "legal_name": "OisteBio GmbH",
        "legal_address": "Oberneuhofstrasse 5, 6340 Baar, Switzerland",
        "legal_vat": "CHE-234.625.162",
        "legal_jurisdiction": "Canton of Zug — Switzerland",
        # Headline quantity + composition.
        "closing_stock_kg": CLOSING_STOCK_KG,
        "composition_rows": composition_rows,
        "composition_total_kg": composition_total,
        # Placeholder — the real hash is computed and pinned by the bundle
        # builder; here we use a stable placeholder so the running footer
        # renders.
        "annex_d_hash": "0" * 64,
    }


# ---------------------------------------------------------------------------
# Renderer — reuses backend pdf_renderer for determinism, extends the
# Jinja env with the same numeric filters used by Annex A.
# ---------------------------------------------------------------------------
def _patched_env_factory() -> Environment:
    """Wrap the captured original env factory and register numeric filters.

    The production renderer constructs its Jinja env without custom filters
    (those will be installed centrally once the reporting service is wired
    up). For the sample script we monkey-patch the factory locally so the
    template's ``| fmt_kg`` / ``| fmt_num`` filters resolve. We call the
    *captured* original — not ``pdf_renderer._build_env`` — to avoid
    recursing through the patched attribute.
    """
    base_env: Environment = _ORIGINAL_BUILD_ENV()
    base_env.filters["fmt_num"] = fmt_num
    base_env.filters["fmt_kg"] = fmt_kg
    base_env.filters["fmt_pct"] = fmt_pct
    return base_env


def render(out_pdf: Path) -> RenderResult:
    """Render the Annex D PDF and return the renderer's structured result."""
    # Replace the env factory only for the duration of this render so the
    # production module remains side-effect free.
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
    # Independent re-hash on disk to confirm the side-car matches what's
    # actually persisted (defence in depth around the renderer's own check).
    on_disk_sha = hashlib.sha256(result.pdf_path.read_bytes()).hexdigest()

    print(f"Rendered:    {result.pdf_path}")
    print(f"Size:        {size_kb:.1f} KB ({result.pdf_size_bytes} bytes)")
    print(f"Pages:       {result.page_count}")
    print(f"Template:    {result.template_name}")
    print(f"SHA-256:     {result.pdf_sha256}")
    print(f"On-disk:     {on_disk_sha}")
    print(f"Side-car:    {result.pdf_sha256_path}")
    print(f"Rendered at: {result.rendered_at.isoformat()}")
    print(f"Generated at (context, UTC now sanity): {datetime.now(UTC).isoformat()}")

    if on_disk_sha != result.pdf_sha256:
        print("ERROR: on-disk SHA-256 differs from renderer-reported digest", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
