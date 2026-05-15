"""WeasyPrint Jinja2 PDF renderer with deterministic SHA-256 side-car.

Used by RTFO submission bundle pipeline (cover letter + Annex A mass balance).
Determinism contract: rendering the same template + context twice MUST produce
byte-identical PDFs, so the SHA-256 anchored in the cover letter footer
remains valid across re-runs of the same submission package.

Determinism levers used (WeasyPrint >= 60):
- No ``custom_metadata`` (default ``False``) → no XMP block with creation date.
- Fixed ``pdf_identifier`` (16 zero bytes) → /ID array stable.
- ``pdf_variant=None``, ``pdf_version=None`` → no variant-specific timestamps.
- ``full_fonts=True`` — fontTools' subsetter relies on ``set`` iteration whose
  order varies with PYTHONHASHSEED randomization, so subsetted glyph tables
  hash differently across processes (and even within one process across GC
  cycles). Embedding full fonts trades file size (~1MB vs ~20KB) for a
  byte-stable PDF, which is the contract required for SHA-256 anchoring in
  the RTFO cover letter footer.
- Template is rendered with a Jinja2 environment that does NOT inject
  ``now()`` / random helpers — caller provides ``generated_at`` explicitly.
- ``base_url`` pointed at ``templates/reports/`` so relative CSS/asset paths
  resolve identically regardless of CWD.

Public API:
    render_to_pdf(template_name, context, output_path) -> RenderResult
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape
from pypdf import PdfReader
from weasyprint import HTML

if TYPE_CHECKING:
    from collections.abc import Callable

# Repo-root anchored templates dir (templates/ at repo root, NOT under backend/).
# backend/app/services/pdf_renderer.py → parents[3] == repo root.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
TEMPLATES_DIR: Final[Path] = _REPO_ROOT / "templates"
REPORTS_DIR: Final[Path] = TEMPLATES_DIR / "reports"

# Fixed 16-byte PDF /ID makes the trailer dictionary deterministic across runs.
_FIXED_PDF_IDENTIFIER: Final[bytes] = b"\x00" * 16


class PDFRenderError(RuntimeError):
    """Raised on template lookup failure, render error, or hash verification mismatch."""


@dataclass(frozen=True, slots=True)
class RenderResult:
    """Outcome of a successful render — all fields populated, paths absolute."""

    pdf_path: Path
    pdf_size_bytes: int
    pdf_sha256: str
    pdf_sha256_path: Path
    page_count: int
    template_name: str
    rendered_at: datetime


def _build_env() -> Environment:
    """Jinja2 env rooted at repo-level ``templates/``.

    Templates are referenced as ``reports/cover_letter_rtfo_310125.html`` etc.
    """
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(("html", "htm", "xml")),
        keep_trailing_newline=True,
    )


def _resolve_template_name(template_name: str) -> str:
    """Accept either ``cover_letter_rtfo_310125.html`` or ``reports/<file>``.

    Bare filenames are auto-prefixed with ``reports/`` since all report templates
    live there. Already-prefixed paths pass through unchanged.
    """
    if "/" in template_name:
        return template_name
    return f"reports/{template_name}"


def _write_sha256_sidecar(sidecar_path: Path, sha256_hex: str, pdf_filename: str) -> None:
    """Emit ``<sha256>  <filename>\\n`` — compatible with ``sha256sum -c``.

    Two-space separator is the GNU coreutils format (text mode).
    """
    sidecar_path.write_text(f"{sha256_hex}  {pdf_filename}\n", encoding="utf-8")


def _count_pages(pdf_bytes: bytes) -> int:
    """Parse PDF bytes with pypdf and return /Page count."""
    import io

    reader = PdfReader(io.BytesIO(pdf_bytes))
    return len(reader.pages)


def render_to_pdf(
    template_name: str,
    context: dict[str, Any],
    output_path: Path,
    filters: dict[str, Callable[..., Any]] | None = None,
) -> RenderResult:
    """Render a Jinja2 template to a deterministic PDF + SHA-256 side-car.

    Args:
        template_name: Bare filename (auto-prefixed with ``reports/``) or
            an already-qualified path under ``templates/``.
        context: Template variables. Caller is responsible for providing
            stable values (e.g. pre-computed ``generated_at`` string) to
            preserve byte-level determinism.
        output_path: Destination ``.pdf`` file. Parent directory is created
            if missing. The side-car file is written next to it with the
            same stem plus ``.sha256``.
        filters: Optional Jinja2 custom filters (e.g. ``fmt_kg``, ``fmt_pct``)
            registered on a per-call Environment. The renderer builds a fresh
            ``Environment`` for every call so registering filters here does
            NOT leak into other renders — keeping determinism intact.

    Returns:
        RenderResult with absolute paths, byte size, hex digest, page count,
        and the timestamp of THIS render call (not embedded in the PDF).

    Raises:
        PDFRenderError: template not found, render failed, or written PDF
            does not hash to the expected digest (filesystem corruption).
    """
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    qualified_name = _resolve_template_name(template_name)
    env = _build_env()
    if filters:
        for name, fn in filters.items():
            env.filters[name] = fn

    try:
        template = env.get_template(qualified_name)
    except TemplateNotFound as exc:
        raise PDFRenderError(f"Template not found: {qualified_name}") from exc

    try:
        rendered_html = template.render(**context)
    except Exception as exc:  # Jinja errors are varied; wrap them all.
        raise PDFRenderError(f"Template render failed for {qualified_name}: {exc}") from exc

    try:
        html_doc = HTML(string=rendered_html, base_url=str(REPORTS_DIR))
        pdf_bytes = html_doc.write_pdf(
            pdf_identifier=_FIXED_PDF_IDENTIFIER,
            pdf_variant=None,
            pdf_version=None,
            custom_metadata=False,
            presentational_hints=True,
            uncompressed_pdf=False,
            full_fonts=True,
        )
    except Exception as exc:  # WeasyPrint raises a wide variety of errors.
        raise PDFRenderError(f"WeasyPrint failed to render {qualified_name}: {exc}") from exc

    if pdf_bytes is None:
        raise PDFRenderError(f"WeasyPrint returned no bytes for {qualified_name}")

    output_path.write_bytes(pdf_bytes)

    sha256_hex = hashlib.sha256(pdf_bytes).hexdigest()

    # Read back and re-hash to guard against filesystem corruption / partial writes.
    written = output_path.read_bytes()
    written_hash = hashlib.sha256(written).hexdigest()
    if written_hash != sha256_hex:
        raise PDFRenderError(
            f"Hash mismatch after write: expected {sha256_hex}, got {written_hash}"
        )

    sidecar_path = output_path.with_suffix(output_path.suffix + ".sha256")
    _write_sha256_sidecar(sidecar_path, sha256_hex, output_path.name)

    page_count = _count_pages(pdf_bytes)

    return RenderResult(
        pdf_path=output_path,
        pdf_size_bytes=len(pdf_bytes),
        pdf_sha256=sha256_hex,
        pdf_sha256_path=sidecar_path,
        page_count=page_count,
        template_name=qualified_name,
        rendered_at=datetime.now(UTC),
    )
