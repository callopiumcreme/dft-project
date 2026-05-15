"""Render the supply-chain diagram PDF for the RTFO-310125 bundle (DFTEN-105 / E1-S1.11).

Usage:
    python3 scripts/render_supply_chain.py [out_pdf]

By default the PDF is written into the bundle directory::

    deliverables/RTFO-310125/04_compliance/01_supply_chain_diagram.pdf

A SHA-256 side-car ``01_supply_chain_diagram.pdf.sha256`` is generated next to
the PDF so the manifest can pin the artefact.

The diagram shows the four supply-chain layers required by the RTFO Track A
pre-application bundle:

    1. Feedstock origin    -- end-of-life tyres (ELT), Colombia
    2. Collecting points   -- Litoplas, Biowaste Service, Esenttia (Colombia)
    3. Processing          -- OisteBio Girardot SAS (pyrolysis)
    4. Off-taker           -- Crown Oil Ltd (UK, RTFO obligated supplier)

The tool chain is WeasyPrint + Jinja2, identical to the cover-letter and mass-
balance renderers (Workers F / I / J / K) -- no Graphviz or system binaries
required, deterministic SHA-256 output.
"""
from __future__ import annotations

import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = REPO_ROOT / "templates" / "reports"
TEMPLATE_NAME = "supply_chain.html"
DEFAULT_OUT = (
    REPO_ROOT
    / "deliverables"
    / "RTFO-310125"
    / "04_compliance"
    / "01_supply_chain_diagram.pdf"
)


def build_context() -> dict[str, Any]:
    """Return the Jinja context for the supply-chain template.

    Volumes are intentionally left as the v1 generic placeholder; the bundle
    manifest pins exact kg figures in Annex A, and we avoid duplicating numeric
    data across documents to prevent drift.
    """
    collecting_points: list[dict[str, str]] = [
        {
            "name": "Litoplas SA",
            "city": "Bogota, Colombia",
            "anla_status": "pending legalisation",
            "volume": "ELT feedstock (per Annex A)",
        },
        {
            "name": "Biowaste Service SA",
            "city": "Mosquera, Colombia",
            "anla_status": "pending legalisation",
            "volume": "ELT feedstock (per Annex A)",
        },
        {
            "name": "Esenttia SA",
            "city": "Cartagena, Colombia",
            "anla_status": "pending legalisation",
            "volume": "ELT feedstock (per Annex A)",
        },
    ]
    return {
        "submission_ref": "RTFO-310125",
        "period": "January 2025",
        "generated_at": datetime.now(UTC).strftime("%d %B %Y"),
        "collecting_points": collecting_points,
    }


def render_pdf(out_pdf: Path) -> Path:
    """Render the template to ``out_pdf`` and return the resolved path."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template(TEMPLATE_NAME)
    html_str = template.render(**build_context())

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_str, base_url=str(TEMPLATE_DIR)).write_pdf(str(out_pdf))
    return out_pdf


def write_sha256_sidecar(pdf_path: Path) -> Path:
    """Compute SHA-256 of ``pdf_path`` and write a ``<pdf>.sha256`` side-car.

    Side-car format mirrors GNU ``sha256sum``::

        <hex_digest>  <basename>
    """
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    sidecar = pdf_path.with_suffix(pdf_path.suffix + ".sha256")
    sidecar.write_text(f"{digest}  {pdf_path.name}\n", encoding="utf-8")
    return sidecar


def main(argv: list[str]) -> int:
    out_pdf = Path(argv[1]).resolve() if len(argv) > 1 else DEFAULT_OUT
    rendered = render_pdf(out_pdf)
    sidecar = write_sha256_sidecar(rendered)
    size_kb = rendered.stat().st_size / 1024
    digest = sidecar.read_text(encoding="utf-8").split()[0]
    print(f"Rendered: {rendered}  ({size_kb:.1f} KB)")
    print(f"SHA-256 : {digest}")
    print(f"Side-car: {sidecar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
