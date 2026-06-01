"""Proforma / Supply Data Sheet on-demand renderer.

Some monthly feedstock suppliers (BOLDER, EFFICIEN, KALTIRE, PYRCOM) have
not yet issued their official commercial invoice for the 2025 audit window.
This module renders a *proforma data sheet* — a per-PoS document that
presents the quantity OisteBio recorded receiving, in a professional layout
the supplier can confirm and honour on its own official invoice.

It is explicitly NOT a fiscal invoice: unit price, total amount and the
final invoice number are left as placeholders for the supplier to complete.
This mirrors the supplier-driven correction flow used for ESENTTIA/LITOPLAS
and keeps the document audit-safe (it is a data presentation, never a
fabricated supplier-issued invoice presented to DfT as genuine).

Render technique mirrors ``ersv_renderer``: per-supplier branding JSON
(``data/ersv_branding/{code}.json`` — same files as eRSV, but driven by the
separate ``proforma_color`` key so the eRSV palette is untouched), a fresh
Jinja2 ``Environment`` per call, and ``render_to_pdf`` dispatched through
``anyio.to_thread.run_sync`` (WeasyPrint is CPU-bound). Documents are
ephemeral/advisory — ``full_fonts=False``, no SHA anchoring.
"""

from __future__ import annotations

import calendar
import json
import logging
import tempfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import anyio.to_thread
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import text

from app.services.pdf_renderer import TEMPLATES_DIR, render_to_pdf

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_TEMPLATE_NAME = "proforma_invoice.html"
_PLACEHOLDER = "—"
_PRICE_PLACEHOLDER = "—"
_INVOICE_NO_PLACEHOLDER = "[ to be assigned ]"
_HS_CODE = "4012.20.00"  # used pneumatic tyres (ELT)
_CURRENCY = "USD"

# Buyer — OisteBio (Swiss GmbH, Baar) — mirrors ersv_renderer constants.
_BUYER_NAME = "OisteBio GmbH"
_BUYER_ADDRESS = "Oberneuhofstrasse 5, 6340 Baar, Switzerland"
_BUYER_VAT = "CHE-234.625.162 MWSt"
_BUYER_PLANT = "Cra. 9 #32, Girardot, Cundinamarca — Colombia"

_BRANDING_DIR: Path = Path(__file__).resolve().parent.parent / "data" / "ersv_branding"


def _load_branding(supplier_code: str) -> dict[str, Any]:
    """Load per-supplier branding JSON merged on top of ``_default.json``."""
    try:
        default_cfg = json.loads(
            (_BRANDING_DIR / "_default.json").read_text(encoding="utf-8")
        )
    except FileNotFoundError:
        default_cfg = {}
    try:
        supplier_cfg = json.loads(
            (_BRANDING_DIR / f"{supplier_code}.json").read_text(encoding="utf-8")
        )
    except FileNotFoundError:
        logger.warning("No branding JSON for supplier_code=%s; using default.", supplier_code)
        supplier_cfg = {}
    return {**default_cfg, **{k: v for k, v in supplier_cfg.items() if v is not None}}


def _fmt_kg(value: object) -> str:
    """Format Decimal/float/None as ``491 518,000`` (3 decimals, EU style)."""
    if value is None:
        return _PLACEHOLDER
    try:
        formatted = f"{float(value):,.3f}"  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return _PLACEHOLDER
    return formatted.replace(",", " ").replace(".", ",")


def _period_for(issuance_date: date) -> str:
    """Build ``01.02.2025 - 28.02.2025`` from a month-end issuance date."""
    first = issuance_date.replace(day=1)
    last_day = calendar.monthrange(issuance_date.year, issuance_date.month)[1]
    last = issuance_date.replace(day=last_day)
    return f"{first.strftime('%d.%m.%Y')} - {last.strftime('%d.%m.%Y')}"


class ProformaNotFoundError(LookupError):
    """Raised when the product_purchase id is missing or soft-deleted."""

    def __init__(self, pp_id: int) -> None:
        super().__init__(f"Product purchase not found: {pp_id}")
        self.pp_id = pp_id


@dataclass(frozen=True, slots=True)
class ProformaHtmlArtifact:
    html: str
    pp_id: int
    pos_number: str


@dataclass(frozen=True, slots=True)
class ProformaPdfArtifact:
    pdf_bytes: bytes
    pdf_sha256: str
    page_count: int
    pp_id: int
    pos_number: str
    rendered_at: datetime


_FETCH_SQL = text(
    """
    SELECT pp.id, pp.pos_number, pp.issuance_date, pp.quantity_kg, pp.feedstock,
           s.code AS supplier_code, s.name AS supplier_name,
           c.code AS contract_code
    FROM product_purchases pp
    JOIN suppliers s ON s.id = pp.supplier_id
    LEFT JOIN contracts c ON c.id = pp.contract_id
    WHERE pp.id = :pp_id
      AND pp.deleted_at IS NULL
    """
)


async def _fetch_row(db: AsyncSession, pp_id: int) -> dict[str, Any]:
    result = await db.execute(_FETCH_SQL, {"pp_id": pp_id})
    row = result.mappings().one_or_none()
    if row is None:
        raise ProformaNotFoundError(pp_id)
    return dict(row)


def _build_context(row: dict[str, Any]) -> dict[str, Any]:
    """Assemble the Jinja2 context for the proforma template."""
    branding = _load_branding(row["supplier_code"])
    issuance: date = row["issuance_date"]

    return {
        "proforma_color": branding.get("proforma_color", "#334155"),
        "supplier_name": branding.get("name") or row["supplier_name"],
        "supplier_address": branding.get("address") or "",
        "supplier_city": branding.get("city"),
        "supplier_department": branding.get("department"),
        "supplier_country": branding.get("country") or "COLOMBIA",
        "supplier_footer_address": branding.get("footer_full_address") or "",
        "version_label": "Supply Data Sheet v.2025.1.0",
        # Document meta
        "pos_number": row["pos_number"],
        "contract_code": row["contract_code"] or _PLACEHOLDER,
        "period": _period_for(issuance),
        "issue_date_eu": issuance.strftime("%d/%m/%Y"),
        "invoice_no": _INVOICE_NO_PLACEHOLDER,
        "currency": _CURRENCY,
        # Line item
        "feedstock": row["feedstock"],
        "hs_code": _HS_CODE,
        "quantity_kg_str": _fmt_kg(row["quantity_kg"]),
        "price_placeholder": _PRICE_PLACEHOLDER,
        # Buyer
        "buyer_name": _BUYER_NAME,
        "buyer_address": _BUYER_ADDRESS,
        "buyer_vat": _BUYER_VAT,
        "buyer_plant": _BUYER_PLANT,
    }


def _render_pdf_sync(context: dict[str, Any], output_path: Path) -> tuple[bytes, str, int]:
    result = render_to_pdf(
        _TEMPLATE_NAME,
        context,
        output_path,
        filters={"fmt_kg": _fmt_kg},
        full_fonts=False,
    )
    return result.pdf_path.read_bytes(), result.pdf_sha256, result.page_count


async def render_proforma_to_html(db: AsyncSession, pp_id: int) -> ProformaHtmlArtifact:
    row = await _fetch_row(db, pp_id)
    context = _build_context(row)
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(("html", "htm", "xml")),
        keep_trailing_newline=True,
    )
    env.filters["fmt_kg"] = _fmt_kg
    template = env.get_template(f"reports/{_TEMPLATE_NAME}")
    html = template.render(**context)
    return ProformaHtmlArtifact(html=html, pp_id=int(row["id"]), pos_number=row["pos_number"])


async def render_proforma_to_pdf(db: AsyncSession, pp_id: int) -> ProformaPdfArtifact:
    row = await _fetch_row(db, pp_id)
    context = _build_context(row)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_pdf = Path(tmpdir) / f"proforma_{int(row['id'])}.pdf"
        pdf_bytes, sha256_hex, page_count = await anyio.to_thread.run_sync(
            _render_pdf_sync, context, tmp_pdf
        )
    return ProformaPdfArtifact(
        pdf_bytes=pdf_bytes,
        pdf_sha256=sha256_hex,
        page_count=page_count,
        pp_id=int(row["id"]),
        pos_number=row["pos_number"],
        rendered_at=datetime.now(UTC),
    )


__all__ = [
    "ProformaHtmlArtifact",
    "ProformaNotFoundError",
    "ProformaPdfArtifact",
    "render_proforma_to_html",
    "render_proforma_to_pdf",
]
