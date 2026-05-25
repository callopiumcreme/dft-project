"""Render the UTB-2025-Q3-CONSOLIDATED transload report PDF.

Story: DFTEN-166 (E8-G1). Produces the ISCC EU §5 mass-balance continuity
record for the UTB BV Dordrecht transload node, covering consignment c-1
(DEL-CRW-2025-2). Output:
``data/transload/c-1/UTB-2025-Q3-CONSOLIDATED.pdf``.

Uses the deterministic Jinja + WeasyPrint pipeline from
``backend.app.services.pdf_renderer`` for byte-stable output — same /ID,
no creation date, full fonts embedded — so the SHA-256 anchor stays
valid across re-renders.

Run from repo root with the backend venv active::

    python scripts/render_transload_consolidated.py

Context values are hard-coded against the c-1 DEL-CRW-2025-2 row set as
seen in shipment_leg (ids 1, 2, 3, 4). The script does NOT read the DB —
the bundle artefact must be reproducible without network/DB access for
the audit trail.
"""

from __future__ import annotations

import hashlib
import sys
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

TEMPLATE_NAME: Final[str] = "transload_consolidated.html"
DEFAULT_OUTPUT: Final[Path] = (
    _REPO_ROOT / "data" / "transload" / "c-1" / "UTB-2025-Q3-CONSOLIDATED.pdf"
)


def _fmt_kg(value: float) -> str:
    """Match cover-letter Annex A convention: 1 234 567,890 kg."""
    rounded = round(float(value), 3)
    formatted = f"{rounded:,.3f}"
    return formatted.replace(",", " ").replace(".", ",")


def build_context() -> dict[str, Any]:
    """Fixed context for UTB-2025-Q3-CONSOLIDATED. Mirrors DB row state at
    cut-off 2026-05-25; values are stable inputs for byte-deterministic
    rendering.
    """
    kg_in_total = 576270.000
    kg_out_total = 500410.000
    kg_residual = 75860.000
    delta = kg_in_total - (kg_out_total + kg_residual)

    inbound_legs = [
        {
            "seq": 1,
            "document_ref": "CMDU856254189",
            "document_date": "11 Jun 2025",
            "carrier": "CARTAGENA EXPRES voy 007CONU",
            "origin_node": "Cartagena (CO)",
            "destination_node": "Rotterdam (NL)",
            "kg_in": _fmt_kg(298129.000),
        },
        {
            "seq": 2,
            "document_ref": "CMDU877254433",
            "document_date": "03 Jul 2025",
            "carrier": "ISTANBUL EXPRES voy 005COEN",
            "origin_node": "Cartagena (CO)",
            "destination_node": "Rotterdam (NL)",
            "kg_in": _fmt_kg(278141.000),
        },
    ]
    outbound_legs = [
        {
            "seq": 4,
            "document_ref": "JLY001-JLY020",
            "document_date": "15 Aug 2025",
            "carrier": "Crown Oil road delivery",
            "origin_node": "Dordrecht (NL)",
            "destination_node": "Bury (UK)",
            "kg_out": _fmt_kg(kg_out_total),
        },
    ]
    return {
        "document_ref": "UTB-2025-Q3-CONSOLIDATED",
        "period": "Q3 2025 (Jul–Aug)",
        "consignment_code": "DEL-CRW-2025-2",
        "product_grade": "DEV-P100",
        "inbound_legs": inbound_legs,
        "outbound_legs": outbound_legs,
        "kg_in": _fmt_kg(kg_in_total),
        "kg_out": _fmt_kg(kg_out_total),
        "kg_stock_residual": _fmt_kg(kg_residual),
        "conservation_ok": abs(delta) <= 1.0,
        "conservation_delta": _fmt_kg(delta),
    }


def _patched_env_factory() -> Environment:
    return _ORIGINAL_BUILD_ENV()


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

    if on_disk_sha != result.pdf_sha256:
        print(
            "ERROR: on-disk SHA-256 differs from renderer-reported digest",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
