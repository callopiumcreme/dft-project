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
"""

from __future__ import annotations

import hashlib
import json
import logging
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

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
        n = float(numerator) if numerator is not None else 0.0
        d = float(denominator) if denominator is not None else 0.0
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


__all__ = [
    "ErsvHtmlArtifact",
    "ErsvNotFoundError",
    "ErsvRenderArtifact",
    "fetch_ersv_row",
    "is_regenerated",
    "render_ersv_to_html",
    "render_ersv_to_pdf",
]
