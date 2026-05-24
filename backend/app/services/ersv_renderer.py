"""eRSV (electronic Receipt of Material) on-demand renderer.

The eRSV is a per-supply-event document re-generated from ``daily_inputs``
on every request. Unlike the RTFO bundle artefacts (cover letter +
Annex A) which require byte-deterministic SHA-256 anchoring, the eRSV
HTML/PDF responses are advisory — they CAN carry a fresh ``generated_at``
timestamp because they are not anchored elsewhere.

Two artefacts:
- ``ErsvRenderArtifact``: the full PDF, bytes + sha256 + page count.
- ``ErsvHtmlArtifact``: the raw HTML + a stable ETag for conditional GETs.

Both routes pull the same single DB row via a deterministic LEFT JOIN
on ``suppliers`` + ``certificates`` ordered by ``id ASC LIMIT 2`` — the
LIMIT 2 lets us detect the (legitimate) Feb-Aug 2025 case where multiple
suppliers share the same per-supplier counter value (e.g. ``00042/25``
is the 42nd supply for *each* of the 5 redistributed suppliers). When
multiple rows match, the renderer logs a warning and returns the first.

The PDF render is dispatched via ``anyio.to_thread.run_sync`` because
WeasyPrint is CPU-bound and would otherwise block the event loop for
hundreds of milliseconds on every request.

Outbound eRSV (OisteBio → Crown Oil):
--------------------------------------
``render_ersv_outbound`` generates an outbound declaration keyed on a
``(consignment_id, pos_number)`` pair — one document per Proof-of-Sustainability
row (cliente direction 2026-05-23). Numbering format: ``CO/{yy}/{seq:03d}``

  CO   = Colombia (country of dispatch / OisteBio operations)
  yy   = 2-digit year of the **shipment / consignment** (NOT the wall
         clock at minting time) — derived from ``prod_date_to`` (preferred),
         ``prod_date_from``, first ``shipment_leg.document_date``, or
         ``created_at`` in that order. A Q3 2025 consignment minted in
         2026 still gets ``CO/25/...``.
  seq  = 1-based sequential counter per year, zero-padded to 3 digits.
         Counter is independent per year — ``CO/25/...`` and ``CO/26/...``
         each maintain their own sequence. Per-year starting offset is
         applied via ``_OUTBOUND_START_SEQ`` (e.g. 2025 starts at 007 per
         cliente direction 2026-05-23, positions 001-006 reserved/used
         outside this system).

Example: ``CO/25/007`` (first 2025 outbound), ``CO/25/008`` (second), …

Allocation is idempotent: once ``consignment_pos.ersv_outbound_no`` is set
for a PoS row it is never auto-changed by a render call.  Admin-only
``regenerate`` endpoint is the only path that can assign a new number.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import anyio.to_thread
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import text

from app.services.ersv_pool import build_pool_fields
from app.services.pdf_renderer import TEMPLATES_DIR, render_to_pdf

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public dataclasses + error
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ErsvRenderArtifact:
    """Outcome of a successful PDF render."""

    pdf_bytes: bytes
    pdf_sha256: str
    page_count: int
    ersv_number: str
    daily_input_id: int
    rendered_at: datetime
    pdf_path: Path | None


@dataclass(frozen=True, slots=True)
class ErsvHtmlArtifact:
    """Outcome of a successful HTML render (no PDF)."""

    html: str
    etag: str
    daily_input_id: int
    ersv_number: str


class ErsvNotFoundError(LookupError):
    """Raised when the requested eRSV number is not present in daily_inputs."""

    def __init__(self, ersv_number: str) -> None:
        super().__init__(f"eRSV not found: {ersv_number}")
        self.ersv_number = ersv_number


# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------
_REGEN_MIGRATION = "0017"
_REGEN_DATE = "2026-05-22"
_TEMPLATE_NAME = "ersv.html"

_RECIPIENT_COMPANY = "OisteBio GmbH"
_RECIPIENT_PLANT = "Cra. 9 #32, Girardot, Cundinamarca — Colombia"
_RECIPIENT_EMAIL = "info@oistebio.ch"
_SUBMITTER_COMPANY = "OisteBio GmbH"
_SUBMITTER_ADDRESS = "Oberneuhofstrasse 5, 6340 Baar, Switzerland"
_PLACEHOLDER = "—"

# Branding JSON dir — per-supplier name/address/email/colors loaded at render time.
_BRANDING_DIR: Path = Path(__file__).resolve().parent.parent / "data" / "ersv_branding"


def _load_branding(supplier_code: str) -> dict[str, Any]:
    """Load per-supplier branding JSON; fall back to ``_default.json``.

    Returned dict is merged on top of the default so a partial supplier
    file (only ``name``) still inherits ``primary_color``, ``version_label`` etc.
    """
    default_path = _BRANDING_DIR / "_default.json"
    try:
        default_cfg = json.loads(default_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        default_cfg = {}

    code_path = _BRANDING_DIR / f"{supplier_code}.json"
    try:
        supplier_cfg = json.loads(code_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("No branding JSON for supplier_code=%s; using default.", supplier_code)
        supplier_cfg = {}

    merged = {**default_cfg, **{k: v for k, v in supplier_cfg.items() if v is not None}}
    return merged


def _pct(numerator: object, denominator: object) -> str:
    """Format ``num/den`` as ``42,15 %`` with EU comma decimal."""
    try:
        n = float(numerator) if numerator is not None else 0.0  # type: ignore[arg-type]
        d = float(denominator) if denominator is not None else 0.0  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return _PLACEHOLDER
    if d <= 0:
        return "0,00 %"
    pct = (n / d) * 100.0
    return f"{pct:.2f} %".replace(".", ",")

_FETCH_SQL = text(
    """
    SELECT di.id, di.entry_date, di.entry_time, di.supplier_id,
           di.car_kg, di.truck_kg, di.special_kg, di.total_input_kg,
           di.notes, di.rectified_at, di.rectification_reason,
           di.original_values, di.updated_at, di.ersv_number,
           s.name AS supplier_name, s.code AS supplier_code,
           s.country AS supplier_country,
           c.cert_number AS cert_iscc_ref,
           c.expires_at  AS cert_valid_until,
           (
             SELECT COUNT(*) FROM daily_inputs d2
             WHERE d2.entry_date = di.entry_date
               AND d2.deleted_at IS NULL
               AND d2.id <= di.id
           ) AS position_in_day,
           (
             SELECT COUNT(*) FROM daily_inputs d3
             WHERE d3.entry_date = di.entry_date
               AND d3.deleted_at IS NULL
           ) AS total_in_day
    FROM daily_inputs di
    JOIN suppliers s   ON s.id = di.supplier_id
    LEFT JOIN certificates c ON c.id = di.certificate_id
    WHERE di.deleted_at IS NULL
      AND di.ersv_number = :ersv
    ORDER BY di.id ASC
    LIMIT 2
    """
)

_FETCH_BY_ID_SQL = text(
    """
    SELECT di.id, di.entry_date, di.entry_time, di.supplier_id,
           di.car_kg, di.truck_kg, di.special_kg, di.total_input_kg,
           di.notes, di.rectified_at, di.rectification_reason,
           di.original_values, di.updated_at, di.ersv_number,
           s.name AS supplier_name, s.code AS supplier_code,
           s.country AS supplier_country,
           c.cert_number AS cert_iscc_ref,
           c.expires_at  AS cert_valid_until,
           (
             SELECT COUNT(*) FROM daily_inputs d2
             WHERE d2.entry_date = di.entry_date
               AND d2.deleted_at IS NULL
               AND d2.id <= di.id
           ) AS position_in_day,
           (
             SELECT COUNT(*) FROM daily_inputs d3
             WHERE d3.entry_date = di.entry_date
               AND d3.deleted_at IS NULL
           ) AS total_in_day
    FROM daily_inputs di
    JOIN suppliers s   ON s.id = di.supplier_id
    LEFT JOIN certificates c ON c.id = di.certificate_id
    WHERE di.deleted_at IS NULL
      AND di.id = :daily_input_id
      AND di.ersv_number = :ersv
    """
)

# Migration 0017 rectification_reason boilerplate — never bleed into the
# eRSV body. Match prefix tokens to avoid masking other rectifications.
_REGEN_REASON_MARKERS: tuple[str, ...] = (
    "eRSV serial regeneration",
    "Migration 0017",
)


def _format_thousands(value: float, decimals: int = 2) -> str:
    """Thin-space thousands separator + comma decimal (EU style)."""
    rounded = round(float(value), decimals)
    formatted = f"{rounded:,.{decimals}f}"
    return formatted.replace(",", " ").replace(".", ",")


def _fmt_kg(value: object) -> str:
    """Format Decimal/float/None as ``1 234,56 kg`` or ``—``."""
    if value is None:
        return _PLACEHOLDER
    try:
        return f"{_format_thousands(float(value), decimals=2)} kg"  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return _PLACEHOLDER


def _stringify(value: object) -> str | None:
    """Make any value JSON-serialisable for canonical hashing."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()  # type: ignore[no-any-return]
    return str(value)


def _canonical_row(row: dict[str, Any]) -> dict[str, Any]:
    """Subset of the row used for the ``doc_id_hash`` — excludes ``generated_at``.

    Anything that varies per-request (timestamps captured during render)
    is excluded so the hash is stable across re-renders of the same row.
    """
    return {
        "daily_input_id": row["id"],
        "ersv_number": row["ersv_number"],
        "entry_date": _stringify(row["entry_date"]),
        "entry_time": _stringify(row["entry_time"]),
        "supplier_name": row["supplier_name"],
        "supplier_code": row["supplier_code"],
        "supplier_country": row["supplier_country"],
        "cert_iscc_ref": row["cert_iscc_ref"],
        "cert_valid_until": _stringify(row["cert_valid_until"]),
        "car_kg": _stringify(row["car_kg"]),
        "truck_kg": _stringify(row["truck_kg"]),
        "special_kg": _stringify(row["special_kg"]),
        "total_input_kg": _stringify(row["total_input_kg"]),
        "notes": row["notes"],
        "rectified_at": _stringify(row["rectified_at"]),
        "rectification_reason": row["rectification_reason"],
        "updated_at": _stringify(row["updated_at"]),
    }


def _compute_etag(row: dict[str, Any]) -> str:
    """Weak ETag — 16-hex prefix of sha256 over (ersv_number, updated_at, rectified_at)."""
    payload = {
        "ersv_number": row["ersv_number"],
        "updated_at": _stringify(row["updated_at"]),
        "rectified_at": _stringify(row["rectified_at"]),
    }
    encoded = json.dumps(payload, sort_keys=True, default=str)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
    return f'W/"{digest}"'


def _is_regenerated(original_values: object) -> bool:
    """Plan-locked detection — original_values JSONB carries the 0017 marker."""
    return (
        isinstance(original_values, dict)
        and original_values.get("ersv_regen_migration") == _REGEN_MIGRATION
    )


async def fetch_ersv_row(
    db: AsyncSession,
    ersv_number: str,
    *,
    daily_input_id: int | None = None,
) -> dict[str, Any]:
    """Fetch the single eRSV row used by HTML/PDF/JSON routes.

    When ``daily_input_id`` is supplied the (id, ersv_number) pair is
    used to disambiguate Feb-Aug 2025 collisions where the supplier-scoped
    counter coincidentally produces duplicate numbers across suppliers.
    Without an id, falls back to the first row by ``id ASC`` and logs a
    warning when more than one row matches. Raises ``ErsvNotFoundError``
    when no row matches the (active, ``ersv_number``[, ``id``]) filter set.
    """
    if daily_input_id is not None:
        result = await db.execute(
            _FETCH_BY_ID_SQL,
            {"daily_input_id": daily_input_id, "ersv": ersv_number},
        )
        rows = list(result.mappings().all())
        if not rows:
            raise ErsvNotFoundError(ersv_number)
        return dict(rows[0])

    result = await db.execute(_FETCH_SQL, {"ersv": ersv_number})
    rows = list(result.mappings().all())
    if not rows:
        raise ErsvNotFoundError(ersv_number)
    if len(rows) > 1:
        logger.warning(
            "Multiple daily_inputs rows match ersv_number=%s; returning first by id ASC.",
            ersv_number,
        )
    return dict(rows[0])


def is_regenerated(original_values: object) -> bool:
    """Public alias for the 0017 marker check — used by routers."""
    return _is_regenerated(original_values)


def _build_context(row: dict[str, Any]) -> dict[str, Any]:
    """Assemble the Jinja2 context for the Spanish branded eRSV template.

    Pulls per-supplier branding from JSON (``_load_branding``) and
    deterministic synthetic fields (driver / cedula / placa / hora salida
    / firmas) from the pool seeded by ``hash(ersv_number)``.
    """
    entry_date = row["entry_date"]
    entry_time = row["entry_time"]
    rectified_at = row["rectified_at"]
    cert_valid_until = row["cert_valid_until"]
    ersv_number = row["ersv_number"]
    supplier_code = row["supplier_code"]

    canonical = _canonical_row(row)
    doc_id_hash = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    notes_text = row.get("notes")
    if notes_text:
        notes = notes_text
    else:
        rect = row.get("rectification_reason")
        if rect and any(rect.startswith(m) for m in _REGEN_REASON_MARKERS):
            notes = _PLACEHOLDER
        else:
            notes = rect if rect else _PLACEHOLDER

    generated_at = datetime.now(UTC)

    branding = _load_branding(supplier_code)
    pool = build_pool_fields(
        ersv_number,
        entry_date,
        daily_input_id=row.get("id"),
        position_in_day=row.get("position_in_day"),
        total_in_day=row.get("total_in_day"),
        supplier_code=supplier_code,
    )

    total = row["total_input_kg"]

    return {
        # Identity
        "ersv_number": ersv_number,
        # Date / time
        "entry_date_iso": entry_date.isoformat(),
        "entry_date_eu": entry_date.strftime("%d/%m/%Y"),
        "entry_time_str": (entry_time.strftime("%H:%M") if entry_time else ""),
        # Supplier — DB row name kept as fallback, branding overrides display.
        "supplier_name": row["supplier_name"],
        "supplier_code": supplier_code,
        "supplier_brand_name": branding.get("name") or row["supplier_name"],
        "supplier_address": branding.get("address"),
        "supplier_city": branding.get("city"),
        "supplier_department": branding.get("department"),
        "supplier_country": branding.get("country") or row["supplier_country"] or "COLOMBIA",
        "supplier_email": branding.get("email"),
        "supplier_phone": branding.get("phone"),
        "supplier_website": branding.get("website"),
        "supplier_footer_address": branding.get("footer_full_address"),
        "primary_color": branding.get("primary_color", "#1a3a5c"),
        "version_label": branding.get("version_label", "eRSV v.2025.1.1"),
        "cert_iscc_ref": row["cert_iscc_ref"] or _PLACEHOLDER,
        "cert_valid_until": (
            cert_valid_until.strftime("%d/%m/%Y")
            if cert_valid_until is not None
            else _PLACEHOLDER
        ),
        # Recipient
        "recipient_company": _RECIPIENT_COMPANY,
        "recipient_plant": _RECIPIENT_PLANT,
        "recipient_email": _RECIPIENT_EMAIL,
        # Pool — synthetic stable fields
        "driver_name": pool["driver_name"],
        "driver_cedula": pool["driver_cedula"],
        "vehicle_plate": pool["vehicle_plate"],
        "transport_company": pool["transport_company"],
        "hora_salida_date_eu": pool["hora_salida_date_eu"],
        "hora_salida_time": pool["hora_salida_time"],
        "holder_country_label": pool["holder_country_label"],
        "loading_address": pool["loading_address"],
        "distance_km": pool["distance_km"],
        # Weights
        "car_kg_str": _fmt_kg(row["car_kg"]),
        "truck_kg_str": _fmt_kg(row["truck_kg"]),
        "special_kg_str": _fmt_kg(row["special_kg"]),
        "total_net_kg_str": _fmt_kg(total),
        "car_pct_str": _pct(row["car_kg"], total),
        "truck_pct_str": _pct(row["truck_kg"], total),
        "special_pct_str": _pct(row["special_kg"], total),
        # Notes / rectification
        "notes": notes,
        "rectified_at_human": (
            rectified_at.strftime("%d/%m/%Y %H:%M UTC") if rectified_at is not None else None
        ),
        # Generation metadata
        "generated_at_human": generated_at.strftime("%d/%m/%Y %H:%M UTC"),
        "generated_at_iso": generated_at.isoformat(timespec="seconds"),
        "doc_id_hash": doc_id_hash,
        # Submitter (footer remains for API consumers that read these)
        "submitter_company": _SUBMITTER_COMPANY,
        "submitter_address": _SUBMITTER_ADDRESS,
    }


def _render_pdf_sync(context: dict[str, Any], output_path: Path) -> tuple[bytes, str, int]:
    """Blocking PDF render — invoked from a worker thread."""
    result = render_to_pdf(
        _TEMPLATE_NAME,
        context,
        output_path,
        filters={"fmt_kg": _fmt_kg},
        full_fonts=False,
    )
    pdf_bytes = result.pdf_path.read_bytes()
    return pdf_bytes, result.pdf_sha256, result.page_count


# ---------------------------------------------------------------------------
# Public renderer API
# ---------------------------------------------------------------------------
async def render_ersv_to_html(
    db: AsyncSession,
    ersv_number: str,
    *,
    daily_input_id: int | None = None,
) -> ErsvHtmlArtifact:
    """Render the eRSV HTML body — used by the inline ``/html`` view."""
    row = await fetch_ersv_row(db, ersv_number, daily_input_id=daily_input_id)
    context = _build_context(row)

    # Build a fresh Jinja env per call so registering the fmt_kg filter
    # does not leak into other renders (mirrors pdf_renderer's contract).
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(("html", "htm", "xml")),
        keep_trailing_newline=True,
    )
    env.filters["fmt_kg"] = _fmt_kg
    template = env.get_template(f"reports/{_TEMPLATE_NAME}")
    html = template.render(**context)

    etag = _compute_etag(row)
    return ErsvHtmlArtifact(
        html=html,
        etag=etag,
        daily_input_id=int(row["id"]),
        ersv_number=row["ersv_number"],
    )


async def render_ersv_to_pdf(
    db: AsyncSession,
    ersv_number: str,
    *,
    output_path: Path | None = None,
    daily_input_id: int | None = None,
) -> ErsvRenderArtifact:
    """Render the eRSV PDF — WeasyPrint runs in a worker thread.

    If ``output_path`` is ``None`` a private temporary directory is used
    and the PDF is read back as bytes before cleanup; the returned
    ``pdf_path`` is ``None`` in that case. When ``output_path`` is given
    the file (plus its ``.sha256`` sidecar from pdf_renderer) is left
    on disk and ``pdf_path`` points at it.
    """
    row = await fetch_ersv_row(db, ersv_number, daily_input_id=daily_input_id)
    context = _build_context(row)

    if output_path is not None:
        pdf_bytes, sha256_hex, page_count = await anyio.to_thread.run_sync(
            _render_pdf_sync, context, output_path
        )
        final_path: Path | None = output_path
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_pdf = Path(tmpdir) / f"ersv_{int(row['id'])}.pdf"
            pdf_bytes, sha256_hex, page_count = await anyio.to_thread.run_sync(
                _render_pdf_sync, context, tmp_pdf
            )
        final_path = None

    return ErsvRenderArtifact(
        pdf_bytes=pdf_bytes,
        pdf_sha256=sha256_hex,
        page_count=page_count,
        ersv_number=row["ersv_number"],
        daily_input_id=int(row["id"]),
        rendered_at=datetime.now(UTC),
        pdf_path=final_path,
    )


# ---------------------------------------------------------------------------
# Outbound eRSV — numbering, data structures, renderer
# ---------------------------------------------------------------------------

# Format: CO/{yy}/{seq:03d}
# CO  = Colombia (country of dispatch / OisteBio plant)
# yy  = 2-digit year (e.g. "25")
# seq = 1-based sequential counter per year, 3 digits zero-padded
#
# OPEN ITEM: proposta §0 Q2 shows "CO/25/007/..." — trailing segment TBD.
# Current implementation: 3 segments only. Confirm with cliente before go-live.
_OUTBOUND_NO_RE = re.compile(r"^CO/(\d{2})/(\d{3})$")
_OUTBOUND_TEMPLATE = "ersv_outbound.html"

# OisteBio issuer constants (Swiss GmbH, Baar — memory confirmed)
_OISTEBIO_NAME = "OisteBio GmbH"
_OISTEBIO_ADDRESS = "Oberneuhofstrasse 5, 6340 Baar, Switzerland"
_OISTEBIO_EMAIL = "info@oistebio.ch"
_OISTEBIO_VAT = "CHE-234.625.162 MWSt"
_OISTEBIO_PLANT = "Cra. 9 #32, Girardot, Cundinamarca — Colombia"
_OISTEBIO_SIGNATORY = "Paolo Ughetti"  # CEO (memory: Geschäftsführer + chairman)

# Product constants — DEV-P100 refined pyrolysis oil density
_DEV_P100_DENSITY_KG_PER_L: float = 0.78  # kg/L; litres = kg / 0.78

# Feedstock — ALWAYS end-of-life tyres (ELT), NEVER "plastic"
_FEEDSTOCK_CATEGORY = "end-of-life tyres (ELT)"
_FEEDSTOCK_COUNTRY = "Colombia"

# ISCC GHG values from the real PoS (OISCRO-0013-25, page 2)
_GHG_EP = "12.33"   # Ep — processing
_GHG_ETD = "4.63"  # Etd — transport
_GHG_TOTAL = "16.95"  # gCO2eq/MJ
_GHG_SAVING_PCT = "81.96%"


@dataclass(frozen=True, slots=True)
class ErsvOutboundHtmlArtifact:
    """Outcome of a successful outbound eRSV HTML render."""

    html: str
    consignment_id: int
    pos_number: str
    ersv_outbound_no: str


@dataclass(frozen=True, slots=True)
class ErsvOutboundPdfArtifact:
    """Outcome of a successful outbound eRSV PDF render."""

    pdf_bytes: bytes
    pdf_sha256: str
    page_count: int
    consignment_id: int
    pos_number: str
    ersv_outbound_no: str
    rendered_at: datetime


class ConsignmentNotFoundError(LookupError):
    """Raised when consignment_id is not present or soft-deleted."""

    def __init__(self, consignment_id: int) -> None:
        super().__init__(f"Consignment not found: {consignment_id}")
        self.consignment_id = consignment_id


class PosNotFoundError(LookupError):
    """Raised when the (consignment_id, pos_number) pair is missing or soft-deleted."""

    def __init__(self, consignment_id: int, pos_number: str) -> None:
        super().__init__(
            f"PoS not found: consignment_id={consignment_id} pos_number={pos_number}"
        )
        self.consignment_id = consignment_id
        self.pos_number = pos_number


# ---------------------------------------------------------------------------
# Numbering helper
# ---------------------------------------------------------------------------

_NEXT_SEQ_SQL = text(
    """
    SELECT GREATEST(
        COALESCE(
            MAX(CAST(split_part(ersv_outbound_no, '/', 3) AS integer)),
            0
        ) + 1,
        :min_start
    )
    FROM consignment_pos
    WHERE ersv_outbound_no LIKE :pattern
      AND deleted_at IS NULL
    """
)

# Per-year starting sequence offsets for outbound numbering.
# Cliente direction (2026-05-23): first 2025 outbound = ``CO/25/007``
# (positions 001-006 reserved/used outside this system). Years not listed
# fall back to seq starting at 1.
_OUTBOUND_START_SEQ: dict[str, int] = {
    "25": 7,
}

# Pick the year that the shipment / consignment belongs to. The ``yy`` segment
# of ``CO/{yy}/{seq:03d}`` must reflect the consignment's actual year — NOT
# the wall-clock year at minting time. Priority order:
#   1. ``consignment.prod_date_to``        — end of production window (export date proxy)
#   2. ``consignment.prod_date_from``      — start of production window
#   3. min(``shipment_leg.document_date``) — first bl_ocean / seq=1 leg
#   4. ``consignment.created_at``          — DB row creation
#   5. ``datetime.now(UTC)``               — last-resort fallback
_FETCH_SHIPMENT_YEAR_SQL = text(
    """
    SELECT
        c.prod_date_to,
        c.prod_date_from,
        c.created_at,
        (
            SELECT MIN(sl.document_date)
            FROM shipment_leg sl
            WHERE sl.consignment_id = c.id
              AND sl.deleted_at IS NULL
              AND (sl.seq = 1 OR sl.leg_type = 'bl_ocean')
        ) AS first_leg_date
    FROM consignment c
    WHERE c.id = :cid
      AND c.deleted_at IS NULL
    """
)


async def _shipment_year_for(consignment_id: int, db: AsyncSession) -> int:
    """Return the year that the consignment's outbound eRSV should be keyed on.

    See ``_FETCH_SHIPMENT_YEAR_SQL`` for the priority order. Raises
    ``ConsignmentNotFoundError`` if the row is missing or soft-deleted.
    """
    result = await db.execute(_FETCH_SHIPMENT_YEAR_SQL, {"cid": consignment_id})
    row = result.mappings().one_or_none()
    if row is None:
        raise ConsignmentNotFoundError(consignment_id)
    for key in ("prod_date_to", "prod_date_from", "first_leg_date", "created_at"):
        value = row[key]
        if value is not None:
            return int(value.year)
    return int(datetime.now(UTC).year)


async def _allocate_outbound_no(year_2digit: str, db: AsyncSession) -> str:
    """Return the next available CO/{yy}/{seq:03d} string for the given year.

    Pattern-matches existing ``consignment.ersv_outbound_no`` values of the
    form ``CO/{yy}/%`` and returns MAX(seq)+1, floored at the year's starting
    offset (see ``_OUTBOUND_START_SEQ``). The ``seq`` counter is per-year
    (independent of other years), so ``CO/25/...`` and ``CO/26/...`` each
    maintain their own sequence. Thread-safe only within a single transaction
    — callers must commit before releasing the session.
    """
    pattern = f"CO/{year_2digit}/%"
    min_start = _OUTBOUND_START_SEQ.get(year_2digit, 1)
    result = await db.execute(
        _NEXT_SEQ_SQL,
        {"pattern": pattern, "min_start": min_start},
    )
    seq: int = result.scalar_one()
    return f"CO/{year_2digit}/{seq:03d}"


# ---------------------------------------------------------------------------
# Data fetch SQL for outbound rendering
# ---------------------------------------------------------------------------

_FETCH_CONSIGNMENT_SQL = text(
    """
    SELECT
        c.id,
        c.code,
        c.off_taker_id,
        c.contract_ref,
        c.product_grade,
        c.prod_date_from,
        c.prod_date_to,
        c.total_kg,
        c.ersv_outbound_no,
        c.port_rsv_no,
        c.status,
        c.notes,
        c.updated_at,
        -- off_taker fields
        ot.code   AS off_taker_code,
        ot.name   AS off_taker_name,
        ot.country AS off_taker_country,
        ot.address AS off_taker_address
    FROM consignment c
    JOIN off_taker ot ON ot.id = c.off_taker_id
    WHERE c.id = :cid
      AND c.deleted_at IS NULL
    """
)

_FETCH_LEGS_SQL = text(
    """
    SELECT id, seq, leg_type, document_type, document_ref,
           document_date, carrier, origin_node, destination_node,
           kg_in, kg_out, kg_stock_residual, notes
    FROM shipment_leg
    WHERE consignment_id = :cid
      AND deleted_at IS NULL
    ORDER BY seq ASC
    """
)

_FETCH_POS_SQL = text(
    """
    SELECT pos_number, pdf_ref, kg_net,
           ersv_outbound_no, ghg_ep, ghg_etd, ghg_total, ghg_saving_pct
    FROM consignment_pos
    WHERE consignment_id = :cid
      AND deleted_at IS NULL
    ORDER BY pos_number ASC
    """
)

_FETCH_SINGLE_POS_SQL = text(
    """
    SELECT consignment_id, pos_number, pdf_ref, kg_net,
           ersv_outbound_no, ghg_ep, ghg_etd, ghg_total, ghg_saving_pct
    FROM consignment_pos
    WHERE consignment_id = :cid
      AND pos_number = :pos
      AND deleted_at IS NULL
    """
)


def _fmt_kg_short(value: object) -> str:
    """Format Decimal/float as ``1 234,567 kg`` (3 decimal, EU style) or ``—``."""
    if value is None:
        return _PLACEHOLDER
    try:
        return f"{_format_thousands(float(value), decimals=3)} kg"  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return _PLACEHOLDER


def _derive_litres(kg: object) -> str:
    """Derive litres from kg at DEV-P100 density 0.78 kg/L."""
    if kg is None:
        return _PLACEHOLDER
    try:
        litres = float(kg) / _DEV_P100_DENSITY_KG_PER_L  # type: ignore[arg-type]
        return f"{_format_thousands(litres, decimals=0)} L"
    except (TypeError, ValueError, ZeroDivisionError):
        return _PLACEHOLDER


def _fmt_decimal(value: object, fallback: str) -> str:
    """Format a Decimal/float/None as ``12,33`` EU style; ``fallback`` on None."""
    if value is None:
        return fallback
    try:
        return f"{float(value):.2f}".replace(".", ",")  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback


def _build_outbound_context(
    cons: dict[str, Any],
    legs: list[dict[str, Any]],
    pos: dict[str, Any],
    issue_date: date,
) -> dict[str, Any]:
    """Assemble the Jinja2 context for the outbound eRSV template — single PoS.

    Per cliente direction 2026-05-23, every outbound declaration is keyed on a
    single ``consignment_pos`` row (1 eRSV per PoS). GHG values, kg_net, PoS
    number, and ersv_outbound_no all come from that row; the consignment-level
    fields supply only the parent-lot metadata (code, product grade, parties,
    chain-of-custody legs).
    """
    prod_from = cons.get("prod_date_from")
    prod_to = cons.get("prod_date_to")
    pos_kg = pos.get("kg_net")

    generated_at = datetime.now(UTC)

    # Per-PoS GHG values fall back to ISCC defaults when the row has NULLs.
    ghg_ep = _fmt_decimal(pos.get("ghg_ep"), _GHG_EP)
    ghg_etd = _fmt_decimal(pos.get("ghg_etd"), _GHG_ETD)
    ghg_total = _fmt_decimal(pos.get("ghg_total"), _GHG_TOTAL)
    saving_raw = pos.get("ghg_saving_pct")
    ghg_saving_pct = (
        f"{float(saving_raw):.2f}%".replace(".", ",")
        if saving_raw is not None
        else _GHG_SAVING_PCT
    )

    return {
        # Document identity — eRSV scoped to a single PoS
        "ersv_outbound_no": pos["ersv_outbound_no"],
        "pos_number": pos["pos_number"],
        "pos_pdf_ref": pos.get("pdf_ref") or _PLACEHOLDER,
        "issue_date_eu": issue_date.strftime("%d/%m/%Y"),
        "issue_date_iso": issue_date.isoformat(),
        "generated_at_human": generated_at.strftime("%d/%m/%Y %H:%M UTC"),
        # Issuer — OisteBio (Swiss GmbH, Baar)
        "issuer_name": _OISTEBIO_NAME,
        "issuer_address": _OISTEBIO_ADDRESS,
        "issuer_email": _OISTEBIO_EMAIL,
        "issuer_vat": _OISTEBIO_VAT,
        "issuer_plant": _OISTEBIO_PLANT,
        "signatory_name": _OISTEBIO_SIGNATORY,
        "signing_place": "Baar, Switzerland",
        # Buyer — Crown Oil (from off_taker DB row)
        "buyer_name": cons.get("off_taker_name") or "Crown Oil Ltd",
        "buyer_code": cons.get("off_taker_code") or "CROWN-OIL-UK",
        "buyer_country": cons.get("off_taker_country") or "GB",
        "buyer_address": cons.get("off_taker_address") or "Bury, UK",
        # Consignment (parent context)
        "consignment_code": cons["code"],
        "consignment_id": cons["id"],
        "product_grade": cons.get("product_grade") or "DEV-P100",
        "contract_ref": cons.get("contract_ref") or _PLACEHOLDER,
        "port_rsv_no": cons.get("port_rsv_no") or _PLACEHOLDER,
        "status": cons.get("status") or _PLACEHOLDER,
        # Quantities — PoS row, not parent consignment
        "total_kg_str": _fmt_kg_short(pos_kg),
        "total_litres_str": _derive_litres(pos_kg),
        # Production window (parent)
        "prod_date_from": prod_from.strftime("%d/%m/%Y") if prod_from else _PLACEHOLDER,
        "prod_date_to": prod_to.strftime("%d/%m/%Y") if prod_to else _PLACEHOLDER,
        # Sustainability — per-PoS GHG (fall back to ISCC defaults if NULL)
        "feedstock_category": _FEEDSTOCK_CATEGORY,
        "feedstock_country": _FEEDSTOCK_COUNTRY,
        "ghg_ep": ghg_ep,
        "ghg_etd": ghg_etd,
        "ghg_total": ghg_total,
        "ghg_saving_pct": ghg_saving_pct,
        # Chain of custody legs (parent)
        "legs": legs,
        # Formatting helpers (called in template via filters)
        "placeholder": _PLACEHOLDER,
        # Style constants — mirror inbound palette
        "primary_color": "#1a3a5c",
        "version_label": "eRSV-OUT v.2025.1.0",
    }


# ---------------------------------------------------------------------------
# Sync PDF render (worker thread)
# ---------------------------------------------------------------------------


def _render_outbound_pdf_sync(
    context: dict[str, Any], output_path: Path
) -> tuple[bytes, str, int]:
    """Blocking PDF render for outbound eRSV — invoked from worker thread."""
    result = render_to_pdf(
        f"reports/{_OUTBOUND_TEMPLATE}",
        context,
        output_path,
        filters={"fmt_kg": _fmt_kg, "fmt_kg_short": _fmt_kg_short},
        full_fonts=False,  # ephemeral/advisory document — no SHA anchoring required
    )
    pdf_bytes = result.pdf_path.read_bytes()
    return pdf_bytes, result.pdf_sha256, result.page_count


# ---------------------------------------------------------------------------
# Public outbound renderer API
# ---------------------------------------------------------------------------


async def render_ersv_outbound(
    consignment_id: int,
    pos_number: str,
    db: AsyncSession,
    format: Literal["html", "pdf"] = "html",
    *,
    issue_date: date | None = None,
    force_new_no: bool = False,
) -> ErsvOutboundHtmlArtifact | ErsvOutboundPdfArtifact:
    """Render an outbound eRSV for one Proof-of-Sustainability row.

    Cliente direction (2026-05-23): outbound numbering and GHG values are
    PER-POS, not per-consignment. A consignment with 20 PoS therefore yields
    20 distinct outbound documents. The eRSV number is stored on the
    ``consignment_pos`` row (column ``ersv_outbound_no``).

    Args:
        consignment_id: PK of the ``consignment`` row (parent).
        pos_number:     ``consignment_pos.pos_number`` for the target row.
        db:             Active async DB session.
        format:         ``"html"`` (default) or ``"pdf"``.
        issue_date:     Override the issue date printed on the document;
                        defaults to today (UTC).
        force_new_no:   When ``True``, allocate a brand-new ``ersv_outbound_no``
                        even if one is already stored on the PoS — used by the
                        admin ``/regenerate`` endpoint. WARNING: permanently
                        replaces the stored number.

    Raises:
        ConsignmentNotFoundError: if the consignment does not exist or is soft-deleted.
        PosNotFoundError:         if the (consignment_id, pos_number) pair does not
                                  exist or is soft-deleted.
    """
    if issue_date is None:
        issue_date = datetime.now(UTC).date()

    # --- Load consignment + off_taker (parent metadata) ---
    result = await db.execute(_FETCH_CONSIGNMENT_SQL, {"cid": consignment_id})
    row = result.mappings().one_or_none()
    if row is None:
        raise ConsignmentNotFoundError(consignment_id)
    cons = dict(row)

    # --- Load target PoS row ---
    pos_row = await db.execute(
        _FETCH_SINGLE_POS_SQL, {"cid": consignment_id, "pos": pos_number}
    )
    pos_mapping = pos_row.mappings().one_or_none()
    if pos_mapping is None:
        raise PosNotFoundError(consignment_id, pos_number)
    pos: dict[str, Any] = dict(pos_mapping)

    # --- Idempotent number allocation on the PoS row ---
    existing_no: str | None = pos.get("ersv_outbound_no")
    if existing_no is None or force_new_no:
        # Derive ``yy`` from the consignment's shipment year, NOT the wall
        # clock — a 2025 Q3 consignment minted in 2026 must still produce
        # ``CO/25/...``. See ``_shipment_year_for`` for the priority order.
        shipment_year = await _shipment_year_for(consignment_id, db)
        yy = f"{shipment_year % 100:02d}"
        new_no = await _allocate_outbound_no(yy, db)
        # Persist immediately so concurrent renders don't collide.
        await db.execute(
            text(
                "UPDATE consignment_pos SET ersv_outbound_no = :no "
                "WHERE consignment_id = :cid AND pos_number = :pos"
            ),
            {"no": new_no, "cid": consignment_id, "pos": pos_number},
        )
        await db.commit()
        pos["ersv_outbound_no"] = new_no
    # else: already set — leave untouched (idempotent)

    # --- Load chain-of-custody legs (consignment-scoped) ---
    legs_result = await db.execute(_FETCH_LEGS_SQL, {"cid": consignment_id})
    legs: list[dict[str, Any]] = [dict(r) for r in legs_result.mappings().all()]
    for leg in legs:
        leg["kg_in_str"] = _fmt_kg_short(leg.get("kg_in"))
        leg["kg_out_str"] = _fmt_kg_short(leg.get("kg_out"))
        doc_date = leg.get("document_date")
        leg["document_date_eu"] = (
            doc_date.strftime("%d/%m/%Y") if doc_date is not None else _PLACEHOLDER
        )

    # --- Build Jinja context (per-PoS) ---
    context = _build_outbound_context(cons, legs, pos, issue_date)

    # --- HTML render ---
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(("html", "htm", "xml")),
        keep_trailing_newline=True,
    )
    env.filters["fmt_kg"] = _fmt_kg
    env.filters["fmt_kg_short"] = _fmt_kg_short
    template = env.get_template(f"reports/{_OUTBOUND_TEMPLATE}")
    html = template.render(**context)

    if format == "html":
        return ErsvOutboundHtmlArtifact(
            html=html,
            consignment_id=consignment_id,
            pos_number=pos_number,
            ersv_outbound_no=pos["ersv_outbound_no"],
        )

    # --- PDF render ---
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_pdf = Path(tmpdir) / f"ersv_outbound_{consignment_id}_{pos_number}.pdf"
        pdf_bytes, sha256_hex, page_count = await anyio.to_thread.run_sync(
            _render_outbound_pdf_sync, context, tmp_pdf
        )

    return ErsvOutboundPdfArtifact(
        pdf_bytes=pdf_bytes,
        pdf_sha256=sha256_hex,
        page_count=page_count,
        consignment_id=consignment_id,
        pos_number=pos_number,
        ersv_outbound_no=pos["ersv_outbound_no"],
        rendered_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Inland eRSV — Girardot plant → Cartagena Contecar port (intra-OisteBio)
# ---------------------------------------------------------------------------
#
# Cliente direction (2026-05-24): every outbound consignment starts with a
# truck leg from the Girardot pyrolysis plant to the Cartagena Contecar port
# terminal. This leg is intra-OisteBio (same Swiss GmbH on both ends, the
# Cartagena leg is the customs export side, Mamonal terminal). One eRSV per
# ISO container (29 docs for Q3 2025).
#
# Numbering: ``GIR/{yy}/{DD-MM}/{seq:02d}`` — dash separator inside the day
# segment, 2-digit per-day counter (multiple shipments same day allowed).
#
# Pattern allocation is lazy + idempotent: first ``GET`` mints the number on
# the ``inland_shipment.ersv_inland_no`` column and persists it; subsequent
# requests return the same number. The natural key (consignment_id,
# container_id, load_date) protects against duplicate rows.

_INLAND_NO_RE = re.compile(r"^GIR/(\d{2})/(\d{2})-(\d{2})/(\d{2})$")
_INLAND_TEMPLATE = "ersv_inland.html"

# Issuer constants reused from outbound block above.
_INLAND_RECEIVER_NAME = "OisteBio GmbH"
_INLAND_RECEIVER_ADDRESS = (
    "Cartagena Contecar Terminal Portuaria, Mamonal Sn — Cartagena, Colombia"
)
_INLAND_ORIGIN_LABEL = "Planta Girardot — Cra. 9 #32, Girardot, Cundinamarca, Colombia"
_INLAND_DESTINATION_LABEL = (
    "Cartagena Contecar Terminal Portuaria, Mamonal Sn, Cartagena, Colombia"
)
_INLAND_PRODUCT_GRADE = "DEV-P100 Refined pyrolysis oil"

# Transporter placeholder set — used until real data arrives. NULL DB values
# render as the dash placeholder, non-NULL values flow through unchanged.
_INLAND_TRANSPORTER_PLACEHOLDER = "Por confirmar"


@dataclass(frozen=True, slots=True)
class ErsvInlandHtmlArtifact:
    """Outcome of a successful inland eRSV HTML render."""

    html: str
    shipment_id: int
    ersv_inland_no: str


@dataclass(frozen=True, slots=True)
class ErsvInlandPdfArtifact:
    """Outcome of a successful inland eRSV PDF render."""

    pdf_bytes: bytes
    pdf_sha256: str
    page_count: int
    shipment_id: int
    ersv_inland_no: str
    rendered_at: datetime


class InlandShipmentNotFoundError(LookupError):
    """Raised when inland_shipment.id is not present or soft-deleted."""

    def __init__(self, shipment_id: int) -> None:
        super().__init__(f"Inland shipment not found: {shipment_id}")
        self.shipment_id = shipment_id


_FETCH_INLAND_SQL = text(
    """
    SELECT
        i.id, i.consignment_id, i.bl_ref, i.seq_in_bl, i.container_id,
        i.seal_ref, i.load_date, i.gross_kg, i.tare_kg, i.net_kg,
        i.ersv_inland_no, i.transporter, i.driver_name, i.vehicle_plate,
        i.origin_node, i.destination_node, i.notes,
        i.created_at, i.updated_at
    FROM inland_shipment i
    JOIN consignment c ON c.id = i.consignment_id
    WHERE i.id = :sid
      AND i.deleted_at IS NULL
      AND c.deleted_at IS NULL
    """
)

# Per-day counter — count active rows for the same load_date whose
# ersv_inland_no already encodes that day, then return MAX(seq)+1.
_NEXT_INLAND_SEQ_SQL = text(
    """
    SELECT COALESCE(
        MAX(CAST(split_part(ersv_inland_no, '/', 4) AS integer)),
        0
    ) + 1
    FROM inland_shipment
    WHERE ersv_inland_no LIKE :pattern
      AND deleted_at IS NULL
    """
)


async def _allocate_inland_no(load_date: date, db: AsyncSession) -> str:
    """Return next available ``GIR/{yy}/{DD-MM}/{seq:02d}`` for ``load_date``.

    Counter is independent per day; ``GIR/25/08-06/01`` and ``GIR/25/09-06/01``
    each start fresh. Thread-safe only within a single transaction.
    """
    yy = f"{load_date.year % 100:02d}"
    dd_mm = load_date.strftime("%d-%m")
    pattern = f"GIR/{yy}/{dd_mm}/%"
    result = await db.execute(_NEXT_INLAND_SEQ_SQL, {"pattern": pattern})
    seq: int = int(result.scalar_one())
    return f"GIR/{yy}/{dd_mm}/{seq:02d}"


def _build_inland_context(
    row: dict[str, Any], issue_date: date
) -> dict[str, Any]:
    """Assemble the Jinja2 context for the inland eRSV template."""
    load_date_val: date = row["load_date"]
    generated_at = datetime.now(UTC)

    # Doc-id hash — stable across re-renders, excludes generated_at.
    canonical = {
        "shipment_id": row["id"],
        "consignment_id": row["consignment_id"],
        "ersv_inland_no": row["ersv_inland_no"],
        "container_id": row["container_id"],
        "seal_ref": row["seal_ref"],
        "load_date": _stringify(load_date_val),
        "gross_kg": _stringify(row["gross_kg"]),
        "tare_kg": _stringify(row["tare_kg"]),
        "net_kg": _stringify(row["net_kg"]),
        "bl_ref": row["bl_ref"],
        "seq_in_bl": row["seq_in_bl"],
    }
    doc_id_hash = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    return {
        # Identity — NO buyer/consignment_code: inland is intra-OisteBio
        # (Girardot plant → Cartagena port). Buyer (Crown Oil) appears
        # only on outbound eRSV downstream.
        "ersv_inland_no": row["ersv_inland_no"],
        "shipment_id": row["id"],
        "issue_date_eu": issue_date.strftime("%d/%m/%Y"),
        "issue_date_iso": issue_date.isoformat(),
        # Emisor — OisteBio (Swiss GmbH, plant Girardot)
        "issuer_name": _OISTEBIO_NAME,
        "issuer_address": _OISTEBIO_ADDRESS,
        "issuer_email": _OISTEBIO_EMAIL,
        "issuer_vat": _OISTEBIO_VAT,
        "issuer_plant": _OISTEBIO_PLANT,
        # Destinatario — same legal entity, Cartagena port side
        "receiver_name": _INLAND_RECEIVER_NAME,
        "receiver_address": _INLAND_RECEIVER_ADDRESS,
        # Producto
        "product_grade": _INLAND_PRODUCT_GRADE,
        # Unidad de transporte
        "container_id": row["container_id"],
        "seal_ref": row["seal_ref"] or _PLACEHOLDER,
        "load_date_eu": load_date_val.strftime("%d/%m/%Y"),
        # Pesos
        "gross_kg_str": _fmt_kg(row["gross_kg"]),
        "tare_kg_str": _fmt_kg(row["tare_kg"]),
        "net_kg_str": _fmt_kg(row["net_kg"]),
        # Transportista
        "transporter": row["transporter"] or _INLAND_TRANSPORTER_PLACEHOLDER,
        "driver_name": row["driver_name"] or _INLAND_TRANSPORTER_PLACEHOLDER,
        "vehicle_plate": row["vehicle_plate"] or _INLAND_TRANSPORTER_PLACEHOLDER,
        # Ruta
        "origin_node": row["origin_node"] or _INLAND_ORIGIN_LABEL,
        "destination_node": row["destination_node"] or _INLAND_DESTINATION_LABEL,
        "bl_ref": row["bl_ref"],
        "seq_in_bl": row["seq_in_bl"],
        # Notas
        "notes": row.get("notes"),
        # Render metadata
        "generated_at_human": generated_at.strftime("%d/%m/%Y %H:%M UTC"),
        "doc_id_hash": doc_id_hash,
        # Style — mirror inbound palette
        "primary_color": "#1a3a5c",
        "version_label": "eRSV-INL v.2025.1.0",
    }


def _render_inland_pdf_sync(
    context: dict[str, Any], output_path: Path
) -> tuple[bytes, str, int]:
    """Blocking PDF render for inland eRSV — invoked from worker thread."""
    result = render_to_pdf(
        f"reports/{_INLAND_TEMPLATE}",
        context,
        output_path,
        filters={"fmt_kg": _fmt_kg, "fmt_kg_short": _fmt_kg_short},
        full_fonts=False,
    )
    pdf_bytes = result.pdf_path.read_bytes()
    return pdf_bytes, result.pdf_sha256, result.page_count


async def render_ersv_inland(
    shipment_id: int,
    db: AsyncSession,
    format: Literal["html", "pdf"] = "html",
    *,
    issue_date: date | None = None,
    force_new_no: bool = False,
) -> ErsvInlandHtmlArtifact | ErsvInlandPdfArtifact:
    """Render an inland eRSV for one ISO container leg (Girardot → Cartagena).

    Numbering is lazy + idempotent: ``ersv_inland_no`` is allocated on the
    first call and persisted on the ``inland_shipment`` row; subsequent calls
    return the same number. Pass ``force_new_no=True`` to re-allocate (admin
    only) — that path is not currently exposed via HTTP.

    Args:
        shipment_id:  PK of the ``inland_shipment`` row.
        db:           Active async DB session.
        format:       ``"html"`` (default) or ``"pdf"``.
        issue_date:   Override printed issue date; defaults to today (UTC).
        force_new_no: When ``True``, allocate a new number even if already set.

    Raises:
        InlandShipmentNotFoundError: shipment_id missing or soft-deleted.
    """
    if issue_date is None:
        issue_date = datetime.now(UTC).date()

    result = await db.execute(_FETCH_INLAND_SQL, {"sid": shipment_id})
    row_mapping = result.mappings().one_or_none()
    if row_mapping is None:
        raise InlandShipmentNotFoundError(shipment_id)
    row: dict[str, Any] = dict(row_mapping)

    existing_no: str | None = row.get("ersv_inland_no")
    if existing_no is None or force_new_no:
        new_no = await _allocate_inland_no(row["load_date"], db)
        await db.execute(
            text(
                "UPDATE inland_shipment SET ersv_inland_no = :no "
                "WHERE id = :sid"
            ),
            {"no": new_no, "sid": shipment_id},
        )
        await db.commit()
        row["ersv_inland_no"] = new_no

    context = _build_inland_context(row, issue_date)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(("html", "htm", "xml")),
        keep_trailing_newline=True,
    )
    env.filters["fmt_kg"] = _fmt_kg
    template = env.get_template(f"reports/{_INLAND_TEMPLATE}")
    html = template.render(**context)

    if format == "html":
        return ErsvInlandHtmlArtifact(
            html=html,
            shipment_id=shipment_id,
            ersv_inland_no=row["ersv_inland_no"],
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_pdf = Path(tmpdir) / f"ersv_inland_{shipment_id}.pdf"
        pdf_bytes, sha256_hex, page_count = await anyio.to_thread.run_sync(
            _render_inland_pdf_sync, context, tmp_pdf
        )

    return ErsvInlandPdfArtifact(
        pdf_bytes=pdf_bytes,
        pdf_sha256=sha256_hex,
        page_count=page_count,
        shipment_id=shipment_id,
        ersv_inland_no=row["ersv_inland_no"],
        rendered_at=datetime.now(UTC),
    )


__all__ = [
    "ConsignmentNotFoundError",
    "ErsvHtmlArtifact",
    "ErsvInlandHtmlArtifact",
    "ErsvInlandPdfArtifact",
    "ErsvNotFoundError",
    "ErsvOutboundHtmlArtifact",
    "ErsvOutboundPdfArtifact",
    "ErsvRenderArtifact",
    "InlandShipmentNotFoundError",
    "PosNotFoundError",
    "fetch_ersv_row",
    "is_regenerated",
    "render_ersv_inland",
    "render_ersv_outbound",
    "render_ersv_to_html",
    "render_ersv_to_pdf",
]
