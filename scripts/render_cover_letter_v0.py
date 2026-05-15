"""Render the Day-1 v0 RTFO cover letter PDF for bundle RTFO-310125.

Story: E1-S1.12 / DFTEN-106 — produces the Day 1 draft cover letter that
declares the three formally-disclosed gaps (PoS retroactive issuance, ANLA
authorisations consular legalisation, closing stock 339.865 kg) per the
5-working-day activity plan, §5.

Usage:
    python3 scripts/render_cover_letter_v0.py [out_pdf]

The default output path follows the bundle layout:
    deliverables/RTFO-310125/00_cover_letter/00_cover_letter_v0.pdf

Uses the deterministic Jinja + WeasyPrint pipeline from
``backend.app.services.pdf_renderer`` (Worker H added ``filters=`` support) so
the SHA-256 side-car is reproducible across re-runs.

This script intentionally does NOT overwrite Worker B's
``render_cover_letter_sample.py`` — it is a sibling Day-1 artifact for the
real bundle, while the sample remains the QA fixture.
"""

from __future__ import annotations

import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.services.pdf_renderer import RenderResult  # type: ignore[import-not-found]

# Make the repository's ``backend/`` importable so the production renderer
# module can be reused as-is.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
_BACKEND_DIR: Final[Path] = _REPO_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.services import pdf_renderer  # type: ignore[import-not-found]  # noqa: E402

TEMPLATE_NAME: Final[str] = "cover_letter_v0.html"
DEFAULT_OUTPUT: Final[Path] = (
    _REPO_ROOT
    / "deliverables"
    / "RTFO-310125"
    / "00_cover_letter"
    / "00_cover_letter_v0.pdf"
)

# Headline closing-stock figure for January 2025 — Annex D back-reference.
CLOSING_STOCK_KG: Final[float] = 339.865


# ---------------------------------------------------------------------------
# Jinja numeric filters — kept in lock-step with Annex A / Annex D conventions.
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


def _filters() -> dict[str, Callable[..., Any]]:
    return {"fmt_num": fmt_num, "fmt_kg": fmt_kg, "fmt_pct": fmt_pct}


# ---------------------------------------------------------------------------
# Context assembly — Day-1 v0 real bundle metadata.
# ---------------------------------------------------------------------------
def build_context() -> dict[str, Any]:
    """Return the Jinja context for the v0 cover letter.

    ``generated_at`` is a fixed date string so the rendered PDF stays
    byte-identical across re-runs (matching the determinism contract of
    ``pdf_renderer.render_to_pdf``). The manifest hash slug is the public
    placeholder for the bundle-level ``MANIFEST.sha256``, which is populated
    by the bundle-freeze stage on Day 7.
    """
    # Note: ``stock_carryover_kg`` is rendered through the ``fmt_kg`` filter
    # in the template (Spanish/European thousands convention) so we pass the
    # raw float here, not a pre-formatted string.
    return {
        # Submission identifiers.
        "submission_ref": "RTFO-310125",
        "period": "January 2025",
        "rtfo_period": "RTFO obligation year 2024/2025",
        "generated_at": "15 May 2026",
        "submission_date_label": "22 May 2026 (Day 7 EOD)",
        "draft_status": "DRAFT — pending Crown Oil review",
        # Submitter — OisteBio Swiss GmbH (NOT German; per project memory).
        "submitter_company": "OisteBio GmbH",
        "submitter_address": "Oberneuhofstrasse 5, 6340 Baar, Switzerland",
        "submitter_vat": "CHE-234.625.162",
        "submitter_contact": "compliance@oistebio.com",
        # Recipient + intermediary.
        "intermediary_label": (
            "Crown Oil Ltd — RTFO obligated supplier (intermediary)"
        ),
        "off_taker": "Crown Oil Ltd (United Kingdom)",
        # Product / feedstock.
        "feedstock": "End-of-Life Tyres (ELT)",
        "product": "DEV-P100 refined pyrolysis oil",
        # Outstanding items §3 — closing stock back-reference.
        "stock_carryover_kg": CLOSING_STOCK_KG,
        # Manifest hash — populated by bundle freeze (Day 7). v0 placeholder.
        "manifest_hash_short": "TBD-bundle-freeze",
    }


# ---------------------------------------------------------------------------
# Renderer — reuses backend pdf_renderer.render_to_pdf, passing filters via
# the ``filters=`` kwarg (Worker H, S1.10). No monkey-patching needed.
# ---------------------------------------------------------------------------
def render(out_pdf: Path) -> RenderResult:
    """Render the v0 cover letter PDF and return the structured result."""
    result: RenderResult = pdf_renderer.render_to_pdf(
        template_name=TEMPLATE_NAME,
        context=build_context(),
        output_path=out_pdf,
        filters=_filters(),
    )
    return result


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
    print(f"UTC now:     {datetime.now(UTC).isoformat()}")

    if on_disk_sha != result.pdf_sha256:
        print(
            "ERROR: on-disk SHA-256 differs from renderer-reported digest",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
