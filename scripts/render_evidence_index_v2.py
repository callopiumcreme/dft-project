"""Render the FINAL Evidence Index PDF for the RTFO-310825 bundle (8 months).

Story: DFTEN-RTFO-310825. Produces ``09_evidence_index_FINAL.pdf`` at the
bundle root. Enumerates every file in the bundle (excluding ``.sha256``
sidecars and ``.gitkeep`` markers), reads each adjacent ``.sha256`` sidecar
(or computes the digest inline if absent), and maps each file to:
- bundle-relative path
- SHA-256 digest
- producing story (S1.x)
- DfT rejection point addressed (if any)
- status (FINAL / PENDING / META)

Coordination: sibling agents render Annex A ×8, conversion log ×8, audit CSV
×8, and Annex D in parallel. This script polls up to MAX_POLL_ATTEMPTS ×
POLL_INTERVAL_S seconds for the expected files to appear before rendering.
If files are still missing after timeout, it renders with what is present and
notes the gaps.

Usage:
    python scripts/render_evidence_index_v2.py [OUTPUT_PDF]
    # default: deliverables/RTFO-310825/09_evidence_index_FINAL.pdf

Uses the deterministic Jinja + WeasyPrint pipeline from
``backend.app.services.pdf_renderer``.
"""

from __future__ import annotations

import hashlib
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from app.services.pdf_renderer import RenderResult  # type: ignore[import-not-found]

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
_BACKEND_DIR: Final[Path] = _REPO_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.services import pdf_renderer  # type: ignore[import-not-found]  # noqa: E402

TEMPLATE_NAME: Final[str] = "evidence_index_final.html"
BUNDLE_ROOT: Final[Path] = _REPO_ROOT / "deliverables" / "RTFO-310825"
DEFAULT_OUTPUT: Final[Path] = BUNDLE_ROOT / "09_evidence_index_FINAL.pdf"

# Polling config — wait for sibling agents to finish rendering their artifacts.
POLL_INTERVAL_S: Final[int] = 30
MAX_POLL_ATTEMPTS: Final[int] = 10

# Files to skip when enumerating (will not appear in the index).
SKIP_SUFFIXES: Final[frozenset[str]] = frozenset({".sha256"})
SKIP_NAMES: Final[frozenset[str]] = frozenset(
    {
        ".gitkeep",
        "MANIFEST.sha256",
        "MANIFEST.sha256.sig",
        "09_evidence_index_FINAL.pdf",
    }
)

# Expected artifacts from sibling agents — used to gate polling.
EXPECTED_SIBLING_FILES: Final[list[str]] = [
    # Annex A ×8 (sibling mass-balance agent)
    "01_annex_a_mass_balance/02_mass_balance_january_2025_FINAL.pdf",
    "01_annex_a_mass_balance/02_mass_balance_february_2025_FINAL.pdf",
    "01_annex_a_mass_balance/02_mass_balance_march_2025_FINAL.pdf",
    "01_annex_a_mass_balance/02_mass_balance_april_2025_FINAL.pdf",
    "01_annex_a_mass_balance/02_mass_balance_may_2025_FINAL.pdf",
    "01_annex_a_mass_balance/02_mass_balance_june_2025_FINAL.pdf",
    "01_annex_a_mass_balance/02_mass_balance_july_2025_FINAL.pdf",
    "01_annex_a_mass_balance/02_mass_balance_august_2025_FINAL.pdf",
    # Conversion logs ×8 (sibling conversion log agent)
    "02_ros_export/05_production_conversion_logs_january_2025.pdf",
    "02_ros_export/05_production_conversion_logs_february_2025.pdf",
    "02_ros_export/05_production_conversion_logs_march_2025.pdf",
    "02_ros_export/05_production_conversion_logs_april_2025.pdf",
    "02_ros_export/05_production_conversion_logs_may_2025.pdf",
    "02_ros_export/05_production_conversion_logs_june_2025.pdf",
    "02_ros_export/05_production_conversion_logs_july_2025.pdf",
    "02_ros_export/05_production_conversion_logs_august_2025.pdf",
    # Audit CSV ×8 (sibling audit trail agent)
    "05_audit_trail/06_audit_trail_export_january_2025.csv",
    "05_audit_trail/06_audit_trail_export_february_2025.csv",
    "05_audit_trail/06_audit_trail_export_march_2025.csv",
    "05_audit_trail/06_audit_trail_export_april_2025.csv",
    "05_audit_trail/06_audit_trail_export_may_2025.csv",
    "05_audit_trail/06_audit_trail_export_june_2025.csv",
    "05_audit_trail/06_audit_trail_export_july_2025.csv",
    "05_audit_trail/06_audit_trail_export_august_2025.csv",
    # Annex D (sibling stock carry-over agent)
    "06_annex_d_stock_carryover/07_stock_carryover_jan_feb_2025.pdf",
]


@dataclass(frozen=True, slots=True)
class FileMeta:
    """Static metadata describing a bundle file (story, DfT point, status)."""

    story: str
    point: str
    status: str
    status_class: str
    row_class: str = ""


# ---------------------------------------------------------------------------
# Mapping table — bundle-relative paths → metadata. Exact paths match first;
# directory-prefix entries act as catch-alls. Longer prefix wins.
# ---------------------------------------------------------------------------
PATH_METADATA: Final[list[tuple[str, FileMeta]]] = [
    # Cover letter
    (
        "00_cover_letter/00_cover_letter_FINAL.pdf",
        FileMeta("S1.10", "Submission framing + outstanding-items disclosure (8-month bundle)", "FINAL", "final"),
    ),
    # Annex A — 8 monthly mass balance reports
    (
        "01_annex_a_mass_balance/02_mass_balance_january_2025_FINAL.pdf",
        FileMeta("S1.5", "Mass-balance closure January 2025 (RP1, RP4)", "FINAL", "final"),
    ),
    (
        "01_annex_a_mass_balance/02_mass_balance_february_2025_FINAL.pdf",
        FileMeta("S1.5", "Mass-balance closure February 2025 (RP1, RP4)", "FINAL", "final"),
    ),
    (
        "01_annex_a_mass_balance/02_mass_balance_march_2025_FINAL.pdf",
        FileMeta("S1.5", "Mass-balance closure March 2025 (RP1, RP4)", "FINAL", "final"),
    ),
    (
        "01_annex_a_mass_balance/02_mass_balance_april_2025_FINAL.pdf",
        FileMeta("S1.5", "Mass-balance closure April 2025 (RP1, RP4)", "FINAL", "final"),
    ),
    (
        "01_annex_a_mass_balance/02_mass_balance_may_2025_FINAL.pdf",
        FileMeta("S1.5", "Mass-balance closure May 2025 (RP1, RP4)", "FINAL", "final"),
    ),
    (
        "01_annex_a_mass_balance/02_mass_balance_june_2025_FINAL.pdf",
        FileMeta("S1.5", "Mass-balance closure June 2025 (RP1, RP4)", "FINAL", "final"),
    ),
    (
        "01_annex_a_mass_balance/02_mass_balance_july_2025_FINAL.pdf",
        FileMeta("S1.5", "Mass-balance closure July 2025 (RP1, RP4)", "FINAL", "final"),
    ),
    (
        "01_annex_a_mass_balance/02_mass_balance_august_2025_FINAL.pdf",
        FileMeta("S1.5", "Mass-balance closure August 2025 (RP1, RP4)", "FINAL", "final"),
    ),
    # Production conversion logs ×8
    (
        "02_ros_export/05_production_conversion_logs_january_2025.pdf",
        FileMeta("S1.10", "Per-day kg-to-litre conversion log — January 2025 (RP2)", "FINAL", "final"),
    ),
    (
        "02_ros_export/05_production_conversion_logs_february_2025.pdf",
        FileMeta("S1.10", "Per-day kg-to-litre conversion log — February 2025 (RP2)", "FINAL", "final"),
    ),
    (
        "02_ros_export/05_production_conversion_logs_march_2025.pdf",
        FileMeta("S1.10", "Per-day kg-to-litre conversion log — March 2025 (RP2)", "FINAL", "final"),
    ),
    (
        "02_ros_export/05_production_conversion_logs_april_2025.pdf",
        FileMeta("S1.10", "Per-day kg-to-litre conversion log — April 2025 (RP2)", "FINAL", "final"),
    ),
    (
        "02_ros_export/05_production_conversion_logs_may_2025.pdf",
        FileMeta("S1.10", "Per-day kg-to-litre conversion log — May 2025 (RP2)", "FINAL", "final"),
    ),
    (
        "02_ros_export/05_production_conversion_logs_june_2025.pdf",
        FileMeta("S1.10", "Per-day kg-to-litre conversion log — June 2025 (RP2)", "FINAL", "final"),
    ),
    (
        "02_ros_export/05_production_conversion_logs_july_2025.pdf",
        FileMeta("S1.10", "Per-day kg-to-litre conversion log — July 2025 (RP2)", "FINAL", "final"),
    ),
    (
        "02_ros_export/05_production_conversion_logs_august_2025.pdf",
        FileMeta("S1.10", "Per-day kg-to-litre conversion log — August 2025 (RP2)", "FINAL", "final"),
    ),
    # ISCC PoS status
    (
        "03_supplier_evidence/03_iscc_pos_status.pdf",
        FileMeta("S1.7", "ISCC PoS status for 3 collecting points (RP3) — pending", "PENDING", "pending"),
    ),
    (
        "03_supplier_evidence/certificates/",
        FileMeta("S1.7", "ISCC EU / RedCert supplier certs", "FINAL", "final"),
    ),
    (
        "03_supplier_evidence/contracts/",
        FileMeta("S1.7", "Supply contracts active Jan–Aug 2025", "FINAL", "final"),
    ),
    (
        "03_supplier_evidence/ersv/",
        FileMeta("S1.7", "eRSV per-supplier statements", "FINAL", "final"),
    ),
    (
        "03_supplier_evidence/transport/",
        FileMeta("S1.7", "Outbound transport — Bill of Lading + arrivals tracker (CO→NL→UK)", "FINAL", "final"),
    ),
    # Compliance
    (
        "04_compliance/01_supply_chain_diagram.pdf",
        FileMeta("S1.8", "Supply-chain diagram (ELT → DEV-P100)", "FINAL", "final"),
    ),
    (
        "04_compliance/iscc_eu_certificate/",
        FileMeta("S1.8", "OisteBio ISCC EU certificate (chain of custody)", "FINAL", "final"),
    ),
    (
        "04_compliance/rtfo_pathway_declaration/",
        FileMeta("S1.8", "RTFO pathway declaration for DEV-P100 (ELT RCF, UK RTFO)", "FINAL", "final"),
    ),
    # Audit trail ×8
    (
        "05_audit_trail/06_audit_trail_export_january_2025.csv",
        FileMeta("S1.4", "Audit-log CSV export — January 2025", "FINAL", "final"),
    ),
    (
        "05_audit_trail/06_audit_trail_export_february_2025.csv",
        FileMeta("S1.4", "Audit-log CSV export — February 2025", "FINAL", "final"),
    ),
    (
        "05_audit_trail/06_audit_trail_export_march_2025.csv",
        FileMeta("S1.4", "Audit-log CSV export — March 2025", "FINAL", "final"),
    ),
    (
        "05_audit_trail/06_audit_trail_export_april_2025.csv",
        FileMeta("S1.4", "Audit-log CSV export — April 2025", "FINAL", "final"),
    ),
    (
        "05_audit_trail/06_audit_trail_export_may_2025.csv",
        FileMeta("S1.4", "Audit-log CSV export — May 2025", "FINAL", "final"),
    ),
    (
        "05_audit_trail/06_audit_trail_export_june_2025.csv",
        FileMeta("S1.4", "Audit-log CSV export — June 2025", "FINAL", "final"),
    ),
    (
        "05_audit_trail/06_audit_trail_export_july_2025.csv",
        FileMeta("S1.4", "Audit-log CSV export — July 2025", "FINAL", "final"),
    ),
    (
        "05_audit_trail/06_audit_trail_export_august_2025.csv",
        FileMeta("S1.4", "Audit-log CSV export — August 2025", "FINAL", "final"),
    ),
    (
        "05_audit_trail/db_snapshots/",
        FileMeta("S1.4", "Database snapshots (pg_dump, gzipped)", "FINAL", "final"),
    ),
    # Annex D stock carry-over
    (
        "06_annex_d_stock_carryover/07_stock_carryover_jan_feb_2025.pdf",
        FileMeta("S1.13", "Closing-stock 339.865 kg Jan→Feb 2025 carry-over declaration (RP5)", "FINAL", "final"),
    ),
    # Bundle README
    (
        "README.md",
        FileMeta("S1.14", "Bundle README — layout, regen instructions, integrity protocol", "META", "meta"),
    ),
]


def _classify(rel_path: str) -> FileMeta:
    """Find the most specific PATH_METADATA entry that matches ``rel_path``."""
    best: FileMeta | None = None
    best_specificity = -1
    for prefix, meta in PATH_METADATA:
        if prefix.endswith("/"):
            if rel_path.startswith(prefix) and len(prefix) > best_specificity:
                best = meta
                best_specificity = len(prefix)
        elif rel_path == prefix and len(prefix) > best_specificity:
            best = meta
            best_specificity = len(prefix)
    if best is not None:
        return best
    return FileMeta("—", "—", "META", "meta")


def _sha256_of(path: Path) -> str:
    """Return the SHA-256 hex digest of a file, preferring an adjacent sidecar."""
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if sidecar.is_file():
        text = sidecar.read_text(encoding="utf-8").strip()
        if text:
            return text.split()[0]
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_bundle_files() -> list[Path]:
    """Walk BUNDLE_ROOT, skip side-cars and skip-names. Sorted for determinism."""
    files: list[Path] = []
    for p in BUNDLE_ROOT.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix in SKIP_SUFFIXES:
            continue
        if p.name in SKIP_NAMES:
            continue
        files.append(p)
    files.sort(key=lambda x: x.relative_to(BUNDLE_ROOT).as_posix())
    return files


def _check_expected_files() -> list[str]:
    """Return list of expected sibling files that are still missing."""
    missing = []
    for rel in EXPECTED_SIBLING_FILES:
        if not (BUNDLE_ROOT / rel).is_file():
            missing.append(rel)
    return missing


def _poll_for_sibling_files() -> list[str]:
    """Poll until sibling files materialise, or return remaining missing list."""
    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        missing = _check_expected_files()
        if not missing:
            print(f"All {len(EXPECTED_SIBLING_FILES)} expected sibling files present.")
            return []
        print(
            f"Poll attempt {attempt}/{MAX_POLL_ATTEMPTS}: "
            f"{len(missing)} sibling file(s) still missing. "
            f"Sleeping {POLL_INTERVAL_S}s…",
            flush=True,
        )
        if attempt < MAX_POLL_ATTEMPTS:
            time.sleep(POLL_INTERVAL_S)
    missing = _check_expected_files()
    if missing:
        print(
            f"WARNING: {len(missing)} file(s) still missing after "
            f"{MAX_POLL_ATTEMPTS} attempts. Rendering index with present files.",
            file=sys.stderr,
        )
    return missing


def _build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in _iter_bundle_files():
        rel = path.relative_to(BUNDLE_ROOT).as_posix()
        meta = _classify(rel)
        rows.append(
            {
                "path": rel,
                "story": meta.story,
                "point": meta.point,
                "sha256": _sha256_of(path),
                "status": meta.status,
                "status_class": meta.status_class,
                "row_class": meta.row_class,
            }
        )
    return rows


def build_context(missing_files: list[str] | None = None) -> dict[str, Any]:
    rows = _build_rows()
    gap_note = ""
    if missing_files:
        gap_note = (
            f"NOTE: {len(missing_files)} expected artifact(s) were not yet rendered "
            f"by sibling agents at index generation time and are absent from this index: "
            + ", ".join(missing_files[:5])
            + ("…" if len(missing_files) > 5 else ".")
        )
    return {
        "submission_ref": "RTFO-310825",
        "period": "January–August 2025",
        "generated_at": "21 May 2026",
        "submission_date_label": "21 May 2026",
        "submitter_company": "OisteBio GmbH",
        "submitter_address": "Oberneuhofstrasse 5, 6340 Baar, Switzerland",
        "submitter_vat": "CHE-234.625.162",
        "intermediary_label": "Crown Oil Ltd (UK RTFO obligated supplier)",
        "off_taker": "Crown Oil Ltd (United Kingdom)",
        "feedstock": "End-of-Life Tyres (ELT)",
        "product": "DEV-P100 refined pyrolysis oil",
        "draft_status": "8-month bundle freeze (RTFO-310825)",
        "rows": rows,
        "total_files": len(rows),
        "gap_note": gap_note,
    }


def render(out_pdf: Path, missing_files: list[str] | None = None) -> "RenderResult":
    result: "RenderResult" = pdf_renderer.render_to_pdf(
        template_name=TEMPLATE_NAME,
        context=build_context(missing_files=missing_files),
        output_path=out_pdf,
    )
    return result


def main(argv: list[str]) -> int:
    out_pdf = Path(argv[1]) if len(argv) > 1 else DEFAULT_OUTPUT
    out_pdf = out_pdf.resolve()

    # Poll for sibling artifacts before rendering.
    missing = _poll_for_sibling_files()

    result = render(out_pdf, missing_files=missing)

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

    if on_disk_sha != result.pdf_sha256:
        print(
            "ERROR: on-disk SHA-256 differs from renderer-reported digest",
            file=sys.stderr,
        )
        return 2

    if missing:
        print(f"\nWARNING: {len(missing)} artifact(s) absent from index:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
