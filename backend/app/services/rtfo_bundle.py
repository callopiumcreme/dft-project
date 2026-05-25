"""Verifier-bundle PDF generator — closes DFTEN-151 (E5-S5.6).

Renders a multi-page PDF bundle for a single consignment, packaged as a ZIP
with a SHA-256 manifest. The bundle has six sections, each rendered via the
deterministic ``pdf_renderer`` so that re-running the build produces a
byte-identical artefact (modulo the ``generated_at`` context the caller
provides).

Sections (concatenated into ``verifier-bundle-c{id}-{date}.pdf``):

    01_cover            — cover sheet, submission identity
    02_batch_summary    — consignment + production-link aggregate
    03_ghg_worksheet    — PoS GHG breakdown + mass-weighted aggregates
    04_event_timeline   — audit_log filtered by chain-of-custody resources
    05_audit_excerpt    — full row diffs (old_values / new_values)
    06_supply_chain     — shipment_leg sequence + operator certificates

Output layout::

    <out_root>/c-{id}/<YYYYMMDD>/
        verifier-bundle-c{id}-{date}.pdf       ← concat'd full bundle
        verifier-bundle-c{id}-{date}.pdf.sha256
        verifier-bundle-c{id}-{date}.zip       ← bundle + per-section PDFs + manifest
        MANIFEST.sha256                        ← <sha>  <filename> lines

Dependencies (semantic mapping):
    rtfc_batches (DFTEN-136) → ``consignment``
    rtfc_events  (DFTEN-137) → ``audit_log`` filtered by table/record

The "rtfc_batches/events" tables named in the DFTEN-151 dependency list
were never materialised; this generator queries the existing operational
tables instead — same semantics, no schema duplication.

Public API:
    build_verifier_bundle(db, consignment_id, out_root) -> BundleResult
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path  # noqa: TC003 — used at runtime, not just typing
from typing import TYPE_CHECKING, Any

from pypdf import PdfReader, PdfWriter
from sqlalchemy import text

from app.services.pdf_renderer import RenderResult, render_to_pdf
from app.services.pdf_signer import SignResult, sign_pdf

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Static submitter metadata — sourced from the OisteBio legal-entity record
# (Swiss GmbH, Zug). Kept here instead of the DB until we wire up a
# `submitter` config table.
# ---------------------------------------------------------------------------
SUBMITTER = {
    "company": "OisteBio GmbH",
    "address": "Oberneuhofstraße 5, 6340 Baar, Switzerland",
    "vat": "CHE-234.625.162",
    "contact": "compliance@oistebio.com",
}

SECTIONS: tuple[tuple[str, str, str], ...] = (
    # (filename_stem, template, section_label). Template paths are absolute
    # under templates/ (i.e. include the reports/ prefix) because the
    # pdf_renderer auto-prefix only fires for bare filenames without "/".
    ("01_cover", "reports/verifier_bundle/cover.html", "Cover"),
    ("02_batch_summary", "reports/verifier_bundle/batch_summary.html", "Batch summary"),
    ("03_ghg_worksheet", "reports/verifier_bundle/ghg_worksheet.html", "GHG worksheet"),
    ("04_event_timeline", "reports/verifier_bundle/event_timeline.html", "Event timeline"),
    ("05_audit_excerpt", "reports/verifier_bundle/audit_excerpt.html", "Audit excerpt"),
    ("06_supply_chain", "reports/verifier_bundle/supply_chain.html", "Supply chain"),
)


@dataclass(frozen=True, slots=True)
class BundleResult:
    consignment_id: int
    bundle_pdf_path: Path
    bundle_pdf_sha256: str
    bundle_pdf_size_bytes: int
    bundle_pdf_page_count: int
    zip_path: Path
    zip_sha256: str
    zip_size_bytes: int
    manifest_path: Path
    sections: tuple[RenderResult, ...]
    generated_at: datetime
    # Populated only when ``sign=True`` was requested. ``None`` otherwise.
    signed_pdf: SignResult | None = None


class VerifierBundleError(RuntimeError):
    """Raised on missing consignment, empty section list, or render failure."""


# ---------------------------------------------------------------------------
# DB queries — every SELECT is plain SQL bound through SQLAlchemy text().
# We deliberately avoid ORM models so the bundle service stays decoupled
# from model.py refactors and so the dataclass surface stays stable.
# ---------------------------------------------------------------------------

_Q_CONSIGNMENT = text("""
    SELECT c.id, c.code, c.off_taker_id, c.contract_ref, c.product_grade,
           c.prod_date_from, c.prod_date_to, c.total_kg, c.ersv_outbound_no,
           c.port_rsv_no, c.status, c.notes, c.created_at, c.updated_at,
           c.deleted_at
      FROM consignment c
     WHERE c.id = :cid AND c.deleted_at IS NULL
""")

_Q_OFF_TAKER = text("""
    SELECT id, code, name, country, address
      FROM off_taker WHERE id = :oid
""")

_Q_PRODUCTION_LINKS = text("""
    SELECT consignment_id, prod_date, kg_allocated, created_at
      FROM consignment_production_link
     WHERE consignment_id = :cid
     ORDER BY prod_date
""")

_Q_POS = text("""
    SELECT id, consignment_id, pos_number, kg_net, ghg_ep, ghg_etd,
           ghg_total, ghg_saving_pct, issuance_date, ersv_outbound_no,
           pdf_ref
      FROM consignment_pos
     WHERE consignment_id = :cid AND deleted_at IS NULL
     ORDER BY pos_number
""")

_Q_SHIPMENT_LEGS = text("""
    SELECT id, consignment_id, seq, leg_type, document_type, document_ref,
           document_date, carrier, origin_node, destination_node,
           kg_in, kg_out, kg_stock_residual, operator_certificate_id,
           pdf_ref, notes
      FROM shipment_leg
     WHERE consignment_id = :cid AND deleted_at IS NULL
     ORDER BY seq
""")

_Q_CERT = text("""
    SELECT id, cert_number, scheme, status, issued_at, expires_at, pdf_ref
      FROM certificates WHERE id = :cid AND deleted_at IS NULL
""")

# audit_log filter: union of consignment row + its consignment_pos / shipment_leg
# children, ordered chronologically.
_Q_AUDIT_EVENTS = text("""
    SELECT id, table_name, record_id, action, old_values, new_values,
           changed_by, changed_at
      FROM audit_log
     WHERE (table_name = 'consignment' AND record_id = :cid)
        OR (table_name = 'consignment_pos' AND record_id IN (
            SELECT id FROM consignment_pos WHERE consignment_id = :cid
        ))
        OR (table_name = 'shipment_leg' AND record_id IN (
            SELECT id FROM shipment_leg WHERE consignment_id = :cid
        ))
     ORDER BY changed_at, id
""")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_dict(row: Any) -> dict[str, Any]:  # noqa: ANN401
    """SQLAlchemy Row → plain dict (Jinja-friendly, JSON-friendly)."""
    return dict(row._mapping)


def _coerce_jsonable(value: Any) -> Any:  # noqa: ANN401
    """Recursively make Decimals/dates/datetimes safe for ``tojson`` in templates."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _coerce_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_coerce_jsonable(v) for v in value]
    return value


def _weighted(rows: list[dict[str, Any]], field: str, weight: str) -> float:
    """Mass-weighted average; rows with NULL value or weight are excluded."""
    num = Decimal(0)
    den = Decimal(0)
    for r in rows:
        v = r.get(field)
        w = r.get(weight)
        if v is None or w is None:
            continue
        num += Decimal(str(v)) * Decimal(str(w))
        den += Decimal(str(w))
    if den == 0:
        return 0.0
    return float(num / den)


def _sum_decimal(rows: list[dict[str, Any]], field: str) -> Decimal:
    total = Decimal(0)
    for r in rows:
        v = r.get(field)
        if v is None:
            continue
        total += Decimal(str(v))
    return total


# ---------------------------------------------------------------------------
# Section context builders — one per section, each pure (no I/O).
# ---------------------------------------------------------------------------


def _ctx_common(
    consignment: dict[str, Any],
    off_taker: dict[str, Any],
    generated_at: str,
    section_label: str,
) -> dict[str, Any]:
    return {
        "consignment": consignment,
        "off_taker": off_taker,
        "submitter": SUBMITTER,
        "generated_at": generated_at,
        "section_label": section_label,
    }


def _ctx_batch_summary(
    common: dict[str, Any],
    links: list[dict[str, Any]],
) -> dict[str, Any]:
    total_allocated = _sum_decimal(links, "kg_allocated")
    declared = common["consignment"].get("total_kg") or Decimal(0)
    return {
        **common,
        "production_links": links,
        "total_kg_allocated": float(total_allocated),
        "variance_kg": float(Decimal(str(declared)) - total_allocated),
    }


def _ctx_ghg_worksheet(
    common: dict[str, Any],
    pos_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        **common,
        "pos_rows": pos_rows,
        "total_mass_kg": float(_sum_decimal(pos_rows, "kg_net")),
        "weighted_ep": _weighted(pos_rows, "ghg_ep", "kg_net"),
        "weighted_etd": _weighted(pos_rows, "ghg_etd", "kg_net"),
        "weighted_total": _weighted(pos_rows, "ghg_total", "kg_net"),
        "weighted_saving_pct": _weighted(pos_rows, "ghg_saving_pct", "kg_net"),
    }


def _ctx_timeline(
    common: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    window_from = events[0]["changed_at"] if events else None
    window_to = events[-1]["changed_at"] if events else None
    return {
        **common,
        "events": events,
        "window_from": window_from,
        "window_to": window_to,
    }


def _ctx_audit_excerpt(
    common: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    # Coerce Decimals/dates inside jsonb so tojson doesn't choke at render time.
    safe_events = [
        {**e,
         "old_values": _coerce_jsonable(e.get("old_values")),
         "new_values": _coerce_jsonable(e.get("new_values"))}
        for e in events
    ]
    return {**common, "events": safe_events}


def _ctx_supply_chain(
    common: dict[str, Any],
    legs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {**common, "legs": legs}


# ---------------------------------------------------------------------------
# PDF concat + ZIP packaging
# ---------------------------------------------------------------------------


def _concat_pdfs(sources: list[Path], target: Path) -> tuple[int, int, str]:
    """Concat *sources* into *target* via pypdf. Returns (bytes, pages, sha256)."""
    writer = PdfWriter()
    pages = 0
    for src in sources:
        reader = PdfReader(str(src))
        for page in reader.pages:
            writer.add_page(page)
            pages += 1
    buf = io.BytesIO()
    writer.write(buf)
    body = buf.getvalue()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    return len(body), pages, hashlib.sha256(body).hexdigest()


def _write_manifest(
    manifest_path: Path,
    entries: list[tuple[str, str]],
) -> str:
    """Write ``<sha>  <filename>`` lines (GNU coreutils format). Returns sha of manifest."""
    body = "".join(f"{sha}  {fname}\n" for sha, fname in entries)
    manifest_path.write_bytes(body.encode("utf-8"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _build_zip(
    zip_path: Path,
    files: list[tuple[Path, str]],
) -> tuple[int, str]:
    """Pack *files* (path, arcname) into deterministic zip. Returns (bytes, sha256).

    Deterministic = fixed mtime (1980-01-01, the zip-format epoch floor)
    so re-running the build produces a byte-identical ZIP. Matches the
    determinism contract of pdf_renderer.
    """
    fixed_dt = (1980, 1, 1, 0, 0, 0)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path, arcname in files:
            data = path.read_bytes()
            info = zipfile.ZipInfo(filename=arcname, date_time=fixed_dt)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)
    body = buf.getvalue()
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    zip_path.write_bytes(body)
    return len(body), hashlib.sha256(body).hexdigest()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def build_verifier_bundle(
    db: AsyncSession,
    consignment_id: int,
    out_root: Path,
    generated_at: datetime | None = None,
    sign: bool = False,
) -> BundleResult:
    """Render the verifier bundle for *consignment_id* under *out_root*.

    Args:
        db: AsyncSession (read-only — no writes from this service).
        consignment_id: target consignment.id (must exist, not soft-deleted).
        out_root: filesystem root for output, typically
            ``/data/verifier_bundles`` inside the container. Subdir
            ``c-{id}/<YYYYMMDD>/`` is created beneath.
        generated_at: timestamp to embed in templates (controls determinism).
            Defaults to ``datetime.now(UTC)``.
        sign: if ``True``, run the PAdES-B signer on the concatenated bundle
            PDF as the final step and populate ``BundleResult.signed_pdf``.
            Requires ``data/signing/dev_cert.p12`` (generated by
            ``scripts/gen_signing_cert.sh``).

    Returns:
        BundleResult with paths + hashes for the concat bundle and the ZIP.

    Raises:
        VerifierBundleError: consignment not found or render failure.
    """
    gen_at = generated_at or datetime.now(UTC)
    gen_at_iso = gen_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    day_dir = gen_at.strftime("%Y%m%d")

    cons_row = (await db.execute(_Q_CONSIGNMENT, {"cid": consignment_id})).first()
    if cons_row is None:
        raise VerifierBundleError(
            f"consignment id={consignment_id} not found or soft-deleted"
        )
    consignment = _row_to_dict(cons_row)

    off_row = (
        await db.execute(_Q_OFF_TAKER, {"oid": consignment["off_taker_id"]})
    ).first()
    if off_row is None:
        raise VerifierBundleError(
            f"off_taker id={consignment['off_taker_id']} not found"
        )
    off_taker = _row_to_dict(off_row)

    links = [_row_to_dict(r) for r in (
        await db.execute(_Q_PRODUCTION_LINKS, {"cid": consignment_id})
    ).all()]
    pos_rows = [_row_to_dict(r) for r in (
        await db.execute(_Q_POS, {"cid": consignment_id})
    ).all()]
    legs = [_row_to_dict(r) for r in (
        await db.execute(_Q_SHIPMENT_LEGS, {"cid": consignment_id})
    ).all()]
    events = [_row_to_dict(r) for r in (
        await db.execute(_Q_AUDIT_EVENTS, {"cid": consignment_id})
    ).all()]

    # Resolve operator_certificate_id → embedded cert dict for the supply-chain view.
    for leg in legs:
        cid = leg.get("operator_certificate_id")
        if cid is None:
            leg["operator_cert"] = None
            continue
        cert_row = (await db.execute(_Q_CERT, {"cid": cid})).first()
        leg["operator_cert"] = _row_to_dict(cert_row) if cert_row else None

    target_dir = out_root / f"c-{consignment_id}" / day_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    rendered: list[RenderResult] = []
    section_pdf_paths: list[Path] = []
    manifest_entries: list[tuple[str, str]] = []

    for stem, template, label in SECTIONS:
        common = _ctx_common(consignment, off_taker, gen_at_iso, label)
        if stem == "01_cover":
            ctx = common
        elif stem == "02_batch_summary":
            ctx = _ctx_batch_summary(common, links)
        elif stem == "03_ghg_worksheet":
            ctx = _ctx_ghg_worksheet(common, pos_rows)
        elif stem == "04_event_timeline":
            ctx = _ctx_timeline(common, events)
        elif stem == "05_audit_excerpt":
            ctx = _ctx_audit_excerpt(common, events)
        elif stem == "06_supply_chain":
            ctx = _ctx_supply_chain(common, legs)
        else:  # pragma: no cover — SECTIONS is closed.
            raise VerifierBundleError(f"unknown section stem: {stem}")

        out_path = target_dir / f"{stem}.pdf"
        result = render_to_pdf(template, ctx, out_path)
        rendered.append(result)
        section_pdf_paths.append(result.pdf_path)
        manifest_entries.append((result.pdf_sha256, out_path.name))

    bundle_name = f"verifier-bundle-c{consignment_id}-{day_dir}.pdf"
    bundle_path = target_dir / bundle_name
    bundle_size, bundle_pages, bundle_sha = _concat_pdfs(
        section_pdf_paths, bundle_path
    )
    bundle_sidecar = bundle_path.with_suffix(bundle_path.suffix + ".sha256")
    bundle_sidecar.write_text(
        f"{bundle_sha}  {bundle_name}\n", encoding="utf-8"
    )
    manifest_entries.append((bundle_sha, bundle_name))

    manifest_path = target_dir / "MANIFEST.sha256"
    _write_manifest(manifest_path, manifest_entries)

    zip_name = f"verifier-bundle-c{consignment_id}-{day_dir}.zip"
    zip_path = target_dir / zip_name
    zip_files: list[tuple[Path, str]] = [
        (manifest_path, "MANIFEST.sha256"),
        (bundle_path, bundle_name),
        (bundle_sidecar, bundle_sidecar.name),
    ]
    for p in section_pdf_paths:
        zip_files.append((p, p.name))
    zip_size, zip_sha = _build_zip(zip_path, zip_files)

    signed: SignResult | None = None
    if sign:
        signed_path = bundle_path.with_name(bundle_path.stem + ".signed.pdf")
        signed = sign_pdf(
            input_path=bundle_path,
            output_path=signed_path,
            signer_name="DFT verifier",
        )

    return BundleResult(
        consignment_id=consignment_id,
        bundle_pdf_path=bundle_path,
        bundle_pdf_sha256=bundle_sha,
        bundle_pdf_size_bytes=bundle_size,
        bundle_pdf_page_count=bundle_pages,
        zip_path=zip_path,
        zip_sha256=zip_sha,
        zip_size_bytes=zip_size,
        manifest_path=manifest_path,
        sections=tuple(rendered),
        generated_at=gen_at,
        signed_pdf=signed,
    )
