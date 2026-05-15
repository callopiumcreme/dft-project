"""Tests for pdf_renderer service (DFTEN-97).

Covers:
- Happy path: cover_letter_rtfo_310125.html renders, sha256 sidecar correct.
- Determinism: two consecutive renders produce identical SHA-256 digests.
- Missing template raises PDFRenderError.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from app.services.pdf_renderer import (
    PDFRenderError,
    RenderResult,
    render_to_pdf,
)

# Stable, fully-populated context — caller-provided ``generated_at`` is what
# makes back-to-back renders deterministic (the renderer itself never injects
# ``now()``).
MOCK_CONTEXT: dict[str, object] = {
    "submission_ref": "RTFO-310125",
    "period": "2025-01",
    "rtfo_period": "Q1 2025",
    "product": "DEV-P100",
    "feedstock": "End-of-life tyres (ELT)",
    "submitter_company": "OisteBio GmbH",
    "submitter_address": "Oberneuhofstrasse 5, 6340 Baar, Switzerland",
    "submitter_contact": "compliance@oistebio.com",
    "regulator": "Department for Transport",
    "off_taker": "Crown Oil UK",
    "ros_attached": "ROS-2025-01.xlsx",
    "generated_at": "15 May 2026",
    "annex_a_hash": "deadbeef" * 8,  # 64-char hex digest stand-in
}


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    out = tmp_path / "out"
    out.mkdir()
    return out


def test_render_cover_letter_happy_path(output_dir: Path) -> None:
    """Renders cover letter, writes PDF + .sha256 sidecar, hash matches bytes."""
    pdf_path = output_dir / "cover_letter.pdf"

    result = render_to_pdf(
        template_name="cover_letter_rtfo_310125.html",
        context=MOCK_CONTEXT,
        output_path=pdf_path,
    )

    assert isinstance(result, RenderResult)
    assert result.pdf_path.exists()
    assert result.pdf_path == pdf_path.resolve()
    assert result.pdf_size_bytes > 0
    assert result.pdf_size_bytes == pdf_path.stat().st_size

    # SHA-256 sidecar exists and follows ``sha256sum`` format.
    sidecar = pdf_path.with_suffix(".pdf.sha256")
    assert result.pdf_sha256_path == sidecar
    assert sidecar.exists()
    sidecar_text = sidecar.read_text(encoding="utf-8")
    assert sidecar_text == f"{result.pdf_sha256}  {pdf_path.name}\n"

    # Recomputed hash of on-disk PDF equals the reported digest.
    on_disk_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    assert on_disk_hash == result.pdf_sha256
    assert len(result.pdf_sha256) == 64

    assert result.page_count >= 1
    assert result.template_name == "reports/cover_letter_rtfo_310125.html"
    assert result.rendered_at is not None


def test_render_is_deterministic(output_dir: Path) -> None:
    """Two back-to-back renders of identical input yield identical SHA-256."""
    first = output_dir / "first.pdf"
    second = output_dir / "second.pdf"

    r1 = render_to_pdf("cover_letter_rtfo_310125.html", MOCK_CONTEXT, first)
    r2 = render_to_pdf("cover_letter_rtfo_310125.html", MOCK_CONTEXT, second)

    assert r1.pdf_sha256 == r2.pdf_sha256, (
        "Renders are non-deterministic — submission anchoring would break"
    )
    assert first.read_bytes() == second.read_bytes()


def test_missing_template_raises(output_dir: Path) -> None:
    """Lookup failure on unknown template surfaces as PDFRenderError."""
    with pytest.raises(PDFRenderError, match="Template not found"):
        render_to_pdf(
            template_name="does_not_exist_12345.html",
            context=MOCK_CONTEXT,
            output_path=output_dir / "nope.pdf",
        )


def test_sidecar_is_sha256sum_compatible_format(output_dir: Path) -> None:
    """Sidecar text matches ``<64hex>  <filename>\\n`` exactly."""
    pdf_path = output_dir / "verify.pdf"
    result = render_to_pdf("cover_letter_rtfo_310125.html", MOCK_CONTEXT, pdf_path)

    text = result.pdf_sha256_path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    digest, _, filename = text.rstrip("\n").partition("  ")
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)
    assert filename == pdf_path.name
