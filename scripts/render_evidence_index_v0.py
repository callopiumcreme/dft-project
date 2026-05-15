"""Render the Day-1 v0 Evidence Index PDF for bundle RTFO-310125.

Story: E1-S1.12 / DFTEN-106 — produces a single cross-reference index that
maps every planned bundle artifact to the DfT rejection point it addresses,
its SHA-256 digest (placeholder ``TBD`` for files not yet generated), and
its current revision status. The three formally-disclosed outstanding gaps
(per the 5-working-day activity plan, §5) are highlighted in-row.

Usage:
    python3 scripts/render_evidence_index_v0.py [out_pdf]

Default output path follows the bundle layout:
    deliverables/RTFO-310125/09_evidence_index_v0.pdf

Uses the deterministic Jinja + WeasyPrint pipeline from
``backend.app.services.pdf_renderer``.
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from app.services.pdf_renderer import RenderResult  # type: ignore[import-not-found]

# Make the repository's ``backend/`` importable so the production renderer
# module can be reused as-is.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
_BACKEND_DIR: Final[Path] = _REPO_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.services import pdf_renderer  # type: ignore[import-not-found]  # noqa: E402

TEMPLATE_NAME: Final[str] = "evidence_index.html"
DEFAULT_OUTPUT: Final[Path] = (
    _REPO_ROOT
    / "deliverables"
    / "RTFO-310125"
    / "09_evidence_index_v0.pdf"
)


# ---------------------------------------------------------------------------
# Row model — one entry per planned bundle artifact.
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class IndexRow:
    """One cross-reference row mapping a bundle artifact to a DfT point."""

    path: str
    annex: str
    point: str
    hash_short: str
    status: str
    status_class: str
    row_class: str = ""

    def as_context(self) -> dict[str, str]:
        """Render-friendly mapping used by the Jinja template."""
        return {
            "path": self.path,
            "annex": self.annex,
            "point": self.point,
            "hash_short": self.hash_short,
            "status": self.status,
            "status_class": self.status_class,
            "row_class": self.row_class,
        }


# Status sentinels — must match CSS class suffixes in evidence_index.css.
STATUS_DRAFT: Final[str] = "DRAFT"
STATUS_V0: Final[str] = "v0"
STATUS_TBD: Final[str] = "TBD"
STATUS_OUTSTANDING: Final[str] = "OUTSTANDING"


def _build_rows() -> list[IndexRow]:
    """Build the v0 cross-reference rows (one per planned deliverable).

    Hashes are placeholders (``TBD``) for artifacts that have not yet been
    produced. The bundle-freeze stage (Day 7) replaces these with the
    actual SHA-256 digests and re-issues this index as FINAL.
    """
    return [
        IndexRow(
            path="00_cover_letter/00_cover_letter_v0.pdf",
            annex="Cover letter",
            point="Submission framing + outstanding-items disclosure",
            hash_short="see side-car",
            status=STATUS_DRAFT,
            status_class="draft",
        ),
        IndexRow(
            path="01_annex_a_mass_balance/02_mass_balance_january_2025_v1.pdf",
            annex="Annex A",
            point="Mass balance closure (in/out kg, daily detail, supplier mix)",
            hash_short="TBD",
            status=STATUS_TBD,
            status_class="tbd",
        ),
        IndexRow(
            path="02_ros_export/",
            annex="ROS export",
            point="RTFC ledger / Renewable Obligation Sustainability return",
            hash_short="TBD",
            status=STATUS_TBD,
            status_class="tbd",
        ),
        IndexRow(
            path="03_supplier_evidence/certificates/",
            annex="Supplier ISCC certs",
            point="Supplier compliance — chain-of-custody traceability",
            hash_short="TBD",
            status=STATUS_TBD,
            status_class="tbd",
        ),
        IndexRow(
            path="03_supplier_evidence/contracts/",
            annex="Supplier contracts",
            point="Supplier compliance — contractual basis",
            hash_short="TBD",
            status=STATUS_TBD,
            status_class="tbd",
        ),
        IndexRow(
            path="03_supplier_evidence/ersv/",
            annex="eRSV registry",
            point="Supplier traceability — registry of self-declarations ≤5 t",
            hash_short="TBD",
            status=STATUS_TBD,
            status_class="tbd",
        ),
        IndexRow(
            path="04_compliance/iscc_eu_certificate/",
            annex="ISCC EU PoS",
            point="Pathway certification (RCF, ISCC EU System Document 203)",
            hash_short="OUTSTANDING",
            status=STATUS_OUTSTANDING,
            status_class="outstanding",
            row_class="row-outstanding",
        ),
        IndexRow(
            path="04_compliance/rtfo_pathway_declaration/",
            annex="RTFO pathway decl.",
            point="Pathway certification (UK RTFO RCF eligibility)",
            hash_short="TBD",
            status=STATUS_TBD,
            status_class="tbd",
        ),
        IndexRow(
            path="04_compliance/01_supply_chain_diagram.pdf",
            annex="Supply chain diagram",
            point="Traceability — ELT collection → pyrolysis → DEV-P100",
            hash_short="TBD (Worker L)",
            status=STATUS_TBD,
            status_class="tbd",
        ),
        IndexRow(
            path="05_audit_trail/",
            annex="DB snapshots + audit CSV",
            point="Audit trail (DB snapshots Day 5/6 + audit-log CSV)",
            hash_short="TBD",
            status=STATUS_TBD,
            status_class="tbd",
        ),
        IndexRow(
            path="07_stock_carryover_explanation.pdf",
            annex="Annex D",
            point="Closing-stock declaration (339.865 kg retained at Girardot)",
            hash_short="TBD",
            status=STATUS_TBD,
            status_class="tbd",
        ),
        IndexRow(
            path="09_evidence_index_v0.pdf",
            annex="Evidence index",
            point="Cross-reference of all bundle artifacts (this document)",
            hash_short="see side-car",
            status=STATUS_V0,
            status_class="v0",
        ),
    ]


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------
def build_context() -> dict[str, Any]:
    """Return the Jinja context for the v0 evidence index.

    ``generated_at`` is a fixed date string so the rendered PDF stays
    byte-identical across re-runs.
    """
    rows = [r.as_context() for r in _build_rows()]
    return {
        # Submission identifiers.
        "submission_ref": "RTFO-310125",
        "period": "January 2025",
        "generated_at": "15 May 2026",
        "submission_date_label": "22 May 2026 (Day 7 EOD)",
        # Submitter — OisteBio Swiss GmbH (NOT German; per project memory).
        "submitter_company": "OisteBio GmbH",
        "submitter_address": "Oberneuhofstrasse 5, 6340 Baar, Switzerland",
        "submitter_vat": "CHE-234.625.162",
        # Recipient + intermediary.
        "intermediary_label": "Crown Oil Ltd (UK RTFO obligated supplier)",
        "off_taker": "Crown Oil Ltd (United Kingdom)",
        # Product / feedstock.
        "feedstock": "End-of-Life Tyres (ELT)",
        "product": "DEV-P100 refined pyrolysis oil",
        # Row data.
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Renderer — production pdf_renderer for byte-stable output.
# ---------------------------------------------------------------------------
def render(out_pdf: Path) -> RenderResult:
    """Render the v0 evidence index PDF and return the structured result."""
    result: RenderResult = pdf_renderer.render_to_pdf(
        template_name=TEMPLATE_NAME,
        context=build_context(),
        output_path=out_pdf,
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
