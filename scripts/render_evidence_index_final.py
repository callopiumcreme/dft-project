"""Render the FINAL Evidence Index PDF for the RTFO-310125 bundle.

Story: E1-S1.17 / DFTEN-111 — Day 6 bundle freeze. Produces
``09_evidence_index_FINAL.pdf`` at the bundle root. Enumerates every file
in the bundle (excluding ``.sha256`` sidecars and ``.gitkeep`` markers and
``MANIFEST.sha256`` itself), reads each adjacent ``.sha256`` sidecar (or
computes the digest inline if absent), and maps each file to:
- bundle-relative path
- SHA-256 digest
- producing story (S1.5, S1.6, ...)
- DfT rejection point addressed (if any)
- status (FINAL / PENDING / META)

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

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
_BACKEND_DIR: Final[Path] = _REPO_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.services import pdf_renderer  # type: ignore[import-not-found]  # noqa: E402

TEMPLATE_NAME: Final[str] = "evidence_index_final.html"
BUNDLE_ROOT: Final[Path] = _REPO_ROOT / "deliverables" / "RTFO-310125"
DEFAULT_OUTPUT: Final[Path] = BUNDLE_ROOT / "09_evidence_index_FINAL.pdf"

# Files to skip when enumerating (will not appear in the index).
SKIP_SUFFIXES: Final[frozenset[str]] = frozenset({".sha256"})
SKIP_NAMES: Final[frozenset[str]] = frozenset(
    {".gitkeep", "MANIFEST.sha256", "09_evidence_index_FINAL.pdf"}
)


@dataclass(frozen=True, slots=True)
class FileMeta:
    """Static metadata describing a bundle file (story, DfT point, status)."""

    story: str
    point: str
    status: str
    status_class: str
    row_class: str = ""


# ---------------------------------------------------------------------------
# Mapping table — bundle-relative paths → metadata. Path prefixes match in
# order; the first prefix that matches a file's path wins.
# ---------------------------------------------------------------------------
PATH_METADATA: Final[list[tuple[str, FileMeta]]] = [
    (
        "00_cover_letter/00_cover_letter_FINAL.pdf",
        FileMeta("S1.10", "Submission framing + outstanding-items disclosure", "FINAL", "final"),
    ),
    (
        "00_cover_letter/00_cover_letter_v0.pdf",
        FileMeta("S1.10 (superseded)", "Day-1 draft, kept for audit trail", "META", "meta"),
    ),
    (
        "01_annex_a_mass_balance/02_mass_balance_january_2025_FINAL.pdf",
        FileMeta("S1.5", "Mass-balance closure (RP1, RP4)", "FINAL", "final"),
    ),
    (
        "01_annex_a_mass_balance/02_mass_balance_january_2025_v1.pdf",
        FileMeta("S1.5 (v1)", "Mass-balance closure (v1 archive)", "META", "meta"),
    ),
    (
        "01_annex_a_mass_balance/03_mass_balance_january_2025_v2_endpoint.pdf",
        FileMeta("S1.5 (v2)", "Mass-balance via /export endpoint (archive)", "META", "meta"),
    ),
    (
        "01_annex_a_mass_balance/07_stock_carryover_explanation.pdf",
        FileMeta("S1.13", "Closing-stock 339.865 kg declaration (RP5)", "FINAL", "final"),
    ),
    (
        "02_ros_export/05_production_conversion_logs_january_2025.pdf",
        FileMeta("S1.10", "Per-day kg-to-litre conversion log (RP2)", "FINAL", "final"),
    ),
    (
        "03_supplier_evidence/03_iscc_pos_status.pdf",
        FileMeta("S1.7", "ISCC PoS status for 3 collecting points (RP3)", "PENDING", "pending"),
    ),
    (
        "03_supplier_evidence/certificates/",
        FileMeta("S1.7", "ISCC EU / RedCert supplier certs", "FINAL", "final"),
    ),
    (
        "03_supplier_evidence/contracts/",
        FileMeta("S1.7", "Supply contracts active in Jan 2025", "FINAL", "final"),
    ),
    (
        "03_supplier_evidence/ersv/",
        FileMeta("S1.7", "eRSV per-supplier statements", "FINAL", "final"),
    ),
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
        FileMeta("S1.8", "RTFO pathway declaration for DEV-P100", "FINAL", "final"),
    ),
    (
        "05_audit_trail/06_audit_trail_export_january_2025.csv",
        FileMeta("S1.4", "Audit-log CSV export (Jan 2025)", "FINAL", "final"),
    ),
    (
        "05_audit_trail/06_audit_trail_export_january_2025.README.md",
        FileMeta("S1.4", "Audit-log CSV README", "META", "meta"),
    ),
    (
        "05_audit_trail/preaudit_checklist_day4.md",
        FileMeta("S1.16", "Day-4 pre-audit checklist", "META", "meta"),
    ),
    (
        "05_audit_trail/db_snapshots/",
        FileMeta("S1.4", "Database snapshots (pg_dump, gzipped)", "FINAL", "final"),
    ),
    (
        "09_evidence_index_v0.pdf",
        FileMeta("S1.12 (v0)", "Day-1 evidence index (superseded)", "META", "meta"),
    ),
    (
        "README.md",
        FileMeta("Bundle", "Bundle layout + governance", "META", "meta"),
    ),
]


def _classify(rel_path: str) -> FileMeta:
    """Find the most specific PATH_METADATA entry that matches ``rel_path``."""
    # Prefer exact-file match; fall back to directory-prefix match.
    best: FileMeta | None = None
    best_specificity = -1
    for prefix, meta in PATH_METADATA:
        if prefix.endswith("/"):
            # Directory prefix.
            if rel_path.startswith(prefix) and len(prefix) > best_specificity:
                best = meta
                best_specificity = len(prefix)
        elif rel_path == prefix and len(prefix) > best_specificity:
            best = meta
            best_specificity = len(prefix)
    if best is not None:
        return best
    return FileMeta(
        "—",
        "—",
        "META",
        "meta",
    )


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


def build_context() -> dict[str, Any]:
    rows = _build_rows()
    return {
        "submission_ref": "RTFO-310125",
        "period": "January 2025",
        "generated_at": "20 May 2026",
        "submission_date_label": "21 May 2026",
        "submitter_company": "OisteBio GmbH",
        "submitter_address": "Oberneuhofstrasse 5, 6340 Baar, Switzerland",
        "submitter_vat": "CHE-234.625.162",
        "intermediary_label": "Crown Oil Ltd (UK RTFO obligated supplier)",
        "off_taker": "Crown Oil Ltd (United Kingdom)",
        "feedstock": "End-of-Life Tyres (ELT)",
        "product": "DEV-P100 refined pyrolysis oil",
        "rows": rows,
        "total_files": len(rows),
    }


def render(out_pdf: Path) -> RenderResult:
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
