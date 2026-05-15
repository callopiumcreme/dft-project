"""Render a sample RTFO cover-letter PDF for QA (DFTEN-96 / E1-S1.2).

Usage:
    python3 scripts/render_cover_letter_sample.py [out_pdf]

Produces ``cover_letter_sample.pdf`` at the repo root by default, using mock
data that mirrors the structure expected by the Sprint 3 reporting service.
WeasyPrint is invoked directly; no FastAPI or DB dependencies are required.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = REPO_ROOT / "templates" / "reports"
TEMPLATE_NAME = "cover_letter_rtfo_310125.html"


def build_context() -> dict[str, str]:
    """Return mock Jinja context matching the contract documented in S1.2."""
    return {
        "submission_ref": "RTFO-310125",
        "period": "January 2025",
        "rtfo_period": "RTFO obligation year 2024/2025",
        "submitter_company": "OisteBio GmbH",
        "submitter_address": "Oberneuhofstrasse 5, 6340 Baar, Switzerland",
        "submitter_contact": "compliance@oistebio.com",
        "regulator": "UK Department for Transport",
        "feedstock": "End-of-Life Tyres (ELT)",
        "product": "DEV-P100 refined pyrolysis oil",
        "off_taker": "Crown Oil UK Ltd",
        "ros_attached": "ROS_31012025_v1.xlsx, AnnexA_MassBalance_31012025.pdf",
        "annex_a_hash": (
            "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
        ),
        "generated_at": datetime.now(timezone.utc).strftime("%d %B %Y"),
    }


def render(out_pdf: Path) -> Path:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template(TEMPLATE_NAME)
    html_str = template.render(**build_context())

    HTML(string=html_str, base_url=str(TEMPLATE_DIR)).write_pdf(str(out_pdf))
    return out_pdf


def main(argv: list[str]) -> int:
    out_pdf = Path(argv[1]) if len(argv) > 1 else REPO_ROOT / "cover_letter_sample.pdf"
    out_pdf = out_pdf.resolve()
    rendered = render(out_pdf)
    size_kb = rendered.stat().st_size / 1024
    print(f"Rendered: {rendered}  ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
