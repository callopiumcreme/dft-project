"""Read-only mass-balance + analytics reports.

Backed by mv_mass_balance_daily / mv_mass_balance_monthly + live
aggregates over daily_inputs joined to suppliers. All endpoints viewer+.
"""
from __future__ import annotations

import re
import tempfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ViewerUser
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.schemas.reports import (
    BySupplierRow,
    ClosureStatusRow,
    MassBalanceDailyRow,
    MassBalanceMonthlyRow,
)
from app.services.pdf_renderer import PDFRenderError, render_to_pdf

router = APIRouter(prefix="/reports", tags=["reports"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_IT_MONTHS = (
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
)

# Product densities at 15 °C — must match templates/reports/mass_balance.html
# methodology section and scripts/render_mass_balance_sample.py.
_DENSITY_EU = 0.78
_DENSITY_PLUS = 0.856


@router.get("/mass-balance/daily", response_model=list[MassBalanceDailyRow])
async def mass_balance_daily(
    _: ViewerUser,
    db: DbDep,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    supplier_id: int | None = Query(None),
    limit: int = Query(366, ge=1, le=3660),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    params: dict = {"limit": limit, "offset": offset}
    if supplier_id is not None:
        # Live aggregation from daily_inputs filtered by supplier. Production
        # cols (eu_prod, output, closure) are not tracked per supplier → NULL.
        where = ["di.deleted_at IS NULL", "di.supplier_id = :supplier_id"]
        params["supplier_id"] = supplier_id
        if date_from is not None:
            where.append("di.entry_date >= :date_from")
            params["date_from"] = date_from
        if date_to is not None:
            where.append("di.entry_date <= :date_to")
            params["date_to"] = date_to
        where_sql = "WHERE " + " AND ".join(where)
        sql = text(
            f"""
            SELECT di.entry_date                AS day,
                   SUM(di.total_input_kg)       AS input_total_kg,
                   NULL::numeric                AS kg_to_production,
                   NULL::numeric                AS eu_prod_kg,
                   NULL::numeric                AS plus_prod_kg,
                   NULL::numeric                AS carbon_black_kg,
                   NULL::numeric                AS metal_scrap_kg,
                   NULL::numeric                AS h2o_kg,
                   NULL::numeric                AS gas_syngas_kg,
                   NULL::numeric                AS losses_kg,
                   NULL::numeric                AS output_eu_kg,
                   NULL::numeric                AS eu_prod_litres,
                   NULL::numeric                AS plus_prod_litres,
                   NULL::numeric                AS total_prod_litres,
                   NULL::numeric                AS output_total_kg,
                   NULL::numeric                AS closure_diff_pct
            FROM daily_inputs di
            {where_sql}
            GROUP BY di.entry_date
            ORDER BY di.entry_date DESC
            LIMIT :limit OFFSET :offset
            """
        )
    else:
        where = []
        if date_from is not None:
            where.append("day >= :date_from")
            params["date_from"] = date_from
        if date_to is not None:
            where.append("day <= :date_to")
            params["date_to"] = date_to
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        sql = text(
            f"""
            SELECT day, input_total_kg, kg_to_production, eu_prod_kg, plus_prod_kg,
                   carbon_black_kg, metal_scrap_kg, h2o_kg, gas_syngas_kg,
                   losses_kg, output_eu_kg,
                   eu_prod_litres, plus_prod_litres, total_prod_litres,
                   output_total_kg, closure_diff_pct
            FROM mv_mass_balance_daily
            {where_sql}
            ORDER BY day DESC
            LIMIT :limit OFFSET :offset
            """
        )
    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


@router.get("/mass-balance/monthly", response_model=list[MassBalanceMonthlyRow])
async def mass_balance_monthly(
    _: ViewerUser,
    db: DbDep,
    date_from: date | None = Query(None, description="month start (e.g., 2025-01-01)"),
    date_to: date | None = Query(None),
    supplier_id: int | None = Query(None),
) -> list[dict]:
    params: dict = {}
    if supplier_id is not None:
        where = ["di.deleted_at IS NULL", "di.supplier_id = :supplier_id"]
        params["supplier_id"] = supplier_id
        if date_from is not None:
            where.append("di.entry_date >= :date_from")
            params["date_from"] = date_from
        if date_to is not None:
            where.append("di.entry_date <= :date_to")
            params["date_to"] = date_to
        where_sql = "WHERE " + " AND ".join(where)
        sql = text(
            f"""
            SELECT DATE_TRUNC('month', di.entry_date)::date AS month,
                   SUM(di.total_input_kg)                   AS input_total_kg,
                   NULL::numeric                            AS eu_prod_kg,
                   NULL::numeric                            AS plus_prod_kg,
                   NULL::numeric                            AS carbon_black_kg,
                   NULL::numeric                            AS metal_scrap_kg,
                   NULL::numeric                            AS h2o_kg,
                   NULL::numeric                            AS gas_syngas_kg,
                   NULL::numeric                            AS losses_kg,
                   NULL::numeric                            AS output_eu_kg,
                   NULL::numeric                            AS eu_prod_litres,
                   NULL::numeric                            AS plus_prod_litres,
                   NULL::numeric                            AS total_prod_litres,
                   NULL::numeric                            AS output_total_kg,
                   NULL::numeric                            AS closure_diff_pct
            FROM daily_inputs di
            {where_sql}
            GROUP BY DATE_TRUNC('month', di.entry_date)
            ORDER BY month DESC
            """
        )
    else:
        where = []
        if date_from is not None:
            where.append("month >= CAST(date_trunc('month', CAST(:date_from AS date)) AS date)")
            params["date_from"] = date_from
        if date_to is not None:
            where.append("month <= CAST(date_trunc('month', CAST(:date_to AS date)) AS date)")
            params["date_to"] = date_to
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        sql = text(
            f"""
            SELECT month, input_total_kg, eu_prod_kg, plus_prod_kg, carbon_black_kg,
                   metal_scrap_kg, h2o_kg, gas_syngas_kg, losses_kg, output_eu_kg,
                   eu_prod_litres, plus_prod_litres, total_prod_litres,
                   output_total_kg, closure_diff_pct
            FROM mv_mass_balance_monthly
            {where_sql}
            ORDER BY month DESC
            """
        )
    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


@router.get("/by-supplier", response_model=list[BySupplierRow])
async def by_supplier(
    _: ViewerUser,
    db: DbDep,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> list[dict]:
    where = ["di.deleted_at IS NULL", "s.deleted_at IS NULL"]
    params: dict = {}
    if date_from is not None:
        where.append("di.entry_date >= :date_from")
        params["date_from"] = date_from
    if date_to is not None:
        where.append("di.entry_date <= :date_to")
        params["date_to"] = date_to
    where_sql = "WHERE " + " AND ".join(where)
    sql = text(
        f"""
        SELECT s.id  AS supplier_id,
               s.code AS supplier_code,
               s.name AS supplier_name,
               SUM(di.total_input_kg) AS total_input_kg,
               COUNT(*)               AS entries,
               COUNT(DISTINCT di.entry_date) AS days
        FROM daily_inputs di
        JOIN suppliers s ON s.id = di.supplier_id
        {where_sql}
        GROUP BY s.id, s.code, s.name
        ORDER BY total_input_kg DESC
        """
    )
    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


@router.get("/closure-status", response_model=list[ClosureStatusRow])
async def closure_status(
    _: ViewerUser,
    db: DbDep,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> list[dict]:
    where = []
    params: dict = {}
    if date_from is not None:
        where.append("day >= :date_from")
        params["date_from"] = date_from
    if date_to is not None:
        where.append("day <= :date_to")
        params["date_to"] = date_to
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = text(
        f"""
        SELECT day, input_total_kg, output_total_kg, closure_diff_pct,
               CASE
                 WHEN COALESCE(input_total_kg, 0) = 0 THEN 'no_input'
                 WHEN COALESCE(output_total_kg, 0) = 0 THEN 'no_output'
                 WHEN ABS(closure_diff_pct) <= 2 THEN 'ok'
                 WHEN ABS(closure_diff_pct) <= 5 THEN 'warn'
                 ELSE 'alert'
               END AS bucket
        FROM mv_mass_balance_daily
        {where_sql}
        ORDER BY day DESC
        """
    )
    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


# ---------------------------------------------------------------------------
# /mass-balance/export — PDF rendering (DFTEN-98, E1-S1.4)
# ---------------------------------------------------------------------------
def _format_thousands(value: float, decimals: int = 2) -> str:
    """Thin-space thousands separator + comma decimal (Italian/EU style)."""
    rounded = round(float(value), decimals)
    formatted = f"{rounded:,.{decimals}f}"
    return formatted.replace(",", " ").replace(".", ",")


def _fmt_num(value: float | int | None) -> str:
    if value is None:
        return "—"
    return _format_thousands(float(value), decimals=2)


def _fmt_num_signed(value: float | int | None) -> str:
    if value is None:
        return "—"
    rounded = round(float(value), 2)
    sign = "+" if rounded > 0 else ("−" if rounded < 0 else "±")  # noqa: RUF001
    return f"{sign}{_format_thousands(abs(rounded), decimals=2)}"


def _fmt_kg(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{_format_thousands(float(value), decimals=2)} kg"


def _fmt_kg_signed(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{_fmt_num_signed(value)} kg"


def _fmt_l(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{_format_thousands(float(value), decimals=2)} L"


def _fmt_pct(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{_format_thousands(float(value), decimals=2)} %"


def _fmt_pct_signed(value: float | int | None) -> str:
    if value is None:
        return "—"
    rounded = round(float(value), 2)
    sign = "+" if rounded > 0 else ("−" if rounded < 0 else "±")  # noqa: RUF001
    return f"{sign}{_format_thousands(abs(rounded), decimals=2)} %"


_REPORT_FILTERS: dict[str, Any] = {
    "fmt_num": _fmt_num,
    "fmt_num_signed": _fmt_num_signed,
    "fmt_kg": _fmt_kg,
    "fmt_kg_signed": _fmt_kg_signed,
    "fmt_l": _fmt_l,
    "fmt_pct": _fmt_pct,
    "fmt_pct_signed": _fmt_pct_signed,
}


def _month_bounds(month: str) -> tuple[date, date]:
    """Return (first_day, last_day) inclusive for ``YYYY-MM`` input."""
    year, mo = int(month[:4]), int(month[5:7])
    first = date(year, mo, 1)
    last = date(year, 12, 31) if mo == 12 else date(year, mo + 1, 1) - timedelta(days=1)
    return first, last


def _month_to_record_id(month: str) -> int:
    """Pack ``YYYY-MM`` into ``YYYYMM`` int for audit_log.record_id."""
    return int(month[:4]) * 100 + int(month[5:7])


async def _fetch_daily_rows(db: AsyncSession, first: date, last: date) -> list[dict[str, Any]]:
    """Pull mv_mass_balance_daily rows for the period, ordered chronologically."""
    sql = text(
        """
        SELECT day,
               input_total_kg,
               eu_prod_kg, plus_prod_kg,
               eu_prod_litres, plus_prod_litres,
               output_total_kg,
               closure_diff_pct
        FROM mv_mass_balance_daily
        WHERE day >= :first AND day <= :last
        ORDER BY day ASC
        """
    )
    result = await db.execute(sql, {"first": first, "last": last})
    rows: list[dict[str, Any]] = []
    for r in result.mappings().all():
        input_kg = float(r["input_total_kg"]) if r["input_total_kg"] is not None else 0.0
        closure_pct = (
            float(r["closure_diff_pct"]) if r["closure_diff_pct"] is not None else None
        )
        closure_kg = (closure_pct / 100.0) * input_kg if closure_pct is not None else None
        rows.append(
            {
                "date": r["day"].isoformat(),
                "input_kg": float(r["input_total_kg"]) if r["input_total_kg"] is not None else None,
                "eu_prod_kg": float(r["eu_prod_kg"]) if r["eu_prod_kg"] is not None else None,
                "plus_prod_kg": float(r["plus_prod_kg"]) if r["plus_prod_kg"] is not None else None,
                "eu_prod_litres": (
                    float(r["eu_prod_litres"]) if r["eu_prod_litres"] is not None else None
                ),
                "plus_prod_litres": (
                    float(r["plus_prod_litres"]) if r["plus_prod_litres"] is not None else None
                ),
                # c14 not tracked in MVs (no measurement column upstream) — surfaced as None
                # so the template prints "—" rather than a misleading zero.
                "c14_pct": None,
                "closure_diff_kg": closure_kg,
            }
        )
    return rows


async def _fetch_monthly_totals(
    db: AsyncSession, first: date
) -> dict[str, Any]:
    """Pull aggregated row from mv_mass_balance_monthly for month starting ``first``."""
    sql = text(
        """
        SELECT input_total_kg,
               eu_prod_kg, plus_prod_kg,
               eu_prod_litres, plus_prod_litres,
               output_total_kg,
               closure_diff_pct
        FROM mv_mass_balance_monthly
        WHERE month = :first
        """
    )
    result = await db.execute(sql, {"first": first})
    row = result.mappings().first()
    if row is None:
        return {
            "input_kg": 0.0,
            "eu_prod_kg": 0.0,
            "plus_prod_kg": 0.0,
            "eu_prod_litres": 0.0,
            "plus_prod_litres": 0.0,
            "c14_pct": None,
            "closure_diff_kg": 0.0,
            "closure_diff_pct": 0.0,
        }
    input_kg = float(row["input_total_kg"]) if row["input_total_kg"] is not None else 0.0
    closure_pct = (
        float(row["closure_diff_pct"]) if row["closure_diff_pct"] is not None else 0.0
    )
    closure_kg = (closure_pct / 100.0) * input_kg
    return {
        "input_kg": input_kg,
        "eu_prod_kg": float(row["eu_prod_kg"]) if row["eu_prod_kg"] is not None else 0.0,
        "plus_prod_kg": float(row["plus_prod_kg"]) if row["plus_prod_kg"] is not None else 0.0,
        "eu_prod_litres": (
            float(row["eu_prod_litres"]) if row["eu_prod_litres"] is not None else 0.0
        ),
        "plus_prod_litres": (
            float(row["plus_prod_litres"]) if row["plus_prod_litres"] is not None else 0.0
        ),
        "c14_pct": None,
        "closure_diff_kg": closure_kg,
        "closure_diff_pct": closure_pct,
    }


async def _fetch_supplier_breakdown(
    db: AsyncSession, first: date, last: date
) -> list[dict[str, Any]]:
    """Per-supplier totals + share% within the month."""
    sql = text(
        """
        SELECT s.name                  AS name,
               s.cert_iscc_ref         AS cert_iscc_ref,
               SUM(di.total_input_kg)  AS total_kg
        FROM daily_inputs di
        JOIN suppliers s ON s.id = di.supplier_id
        WHERE di.deleted_at IS NULL
          AND s.deleted_at IS NULL
          AND di.entry_date >= :first
          AND di.entry_date <= :last
        GROUP BY s.id, s.name, s.cert_iscc_ref
        ORDER BY total_kg DESC
        """
    )
    result = await db.execute(sql, {"first": first, "last": last})
    rows = list(result.mappings().all())
    grand_total = sum(float(r["total_kg"]) for r in rows if r["total_kg"] is not None) or 0.0
    suppliers: list[dict[str, Any]] = []
    for r in rows:
        kg = float(r["total_kg"]) if r["total_kg"] is not None else 0.0
        share = (kg / grand_total * 100.0) if grand_total > 0 else 0.0
        suppliers.append(
            {
                "name": r["name"],
                "cert_iscc_ref": r["cert_iscc_ref"] or "—",
                "total_kg": round(kg, 2),
                "share_pct": round(share, 2),
            }
        )
    return suppliers


def _build_context(
    month: str,
    daily_rows: list[dict[str, Any]],
    totals: dict[str, Any],
    suppliers: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    year, mo = int(month[:4]), int(month[5:7])
    period_label = f"{_IT_MONTHS[mo - 1]} {year}"
    return {
        "submission_ref": f"RTFO-{mo:02d}{str(year)[2:]}{str(year)[:2]}",
        "period": month,
        "period_label": period_label,
        "generated_at": generated_at,
        "submitter_company": "OisteBio GmbH",
        "submitter_address": "Oberneuhofstrasse 5, 6340 Baar, Switzerland",
        "plant_name": "Girardot, Colombia",
        "feedstock": "ELT — End-of-Life Tyres",
        "product": "DEV-P100 — refined pyrolysis oil",
        "off_taker": "Crown Oil UK",
        "regulator": "UK DfT — LCF Delivery Unit",
        "totals": totals,
        "daily_rows": daily_rows,
        "suppliers": suppliers,
        "annex_a_hash": None,
    }


@router.get("/mass-balance/export")
async def mass_balance_export(
    user: ViewerUser,
    db: DbDep,
    month: str = Query(..., description="Reporting month, ``YYYY-MM``"),
    format: str = Query("pdf", description="Output format — only ``pdf`` is supported"),
) -> Response:
    """Render Annex A mass-balance PDF for the given month.

    Assumes the materialized views ``mv_mass_balance_daily`` and
    ``mv_mass_balance_monthly`` are fresh — refresh is the caller's
    responsibility (see ``POST /mass-balance/refresh``). This handler is
    a pure read + render path: it never refreshes the MVs, so a stale
    view will produce a stale PDF. Caller (UI / cron) MUST refresh first
    when underlying ``daily_inputs`` / ``daily_production`` have changed.

    Response headers:
        - ``X-Content-SHA256``: deterministic digest of the rendered PDF.
        - ``Content-Disposition``: ``attachment; filename=...``.

    Audit:
        Inserts an ``audit_log`` row with ``action='insert'`` (the CHECK
        constraint restricts ``action`` to a fixed set; ``insert`` is the
        canonical "create" action for this exported artifact) and
        ``new_values`` containing ``kind=REPORT_EXPORT``, the month, and
        the SHA-256 digest — enough to reconstruct the audit trail of
        every regulator-facing PDF emitted by the system.
    """
    if not _MONTH_RE.match(month):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="month must match YYYY-MM (e.g. 2025-01)",
        )
    if format != "pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="format must be 'pdf'",
        )

    first, last = _month_bounds(month)
    daily_rows = await _fetch_daily_rows(db, first, last)
    totals = await _fetch_monthly_totals(db, first)
    suppliers = await _fetch_supplier_breakdown(db, first, last)

    # generated_at is captured at request time; deterministic per-request,
    # but two different requests for the same month WILL produce different
    # PDFs (different timestamp). Determinism contract is per-context, not
    # per-month — see backend/app/services/pdf_renderer.py docstring.
    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    context = _build_context(month, daily_rows, totals, suppliers, generated_at)

    filename = f"mass_balance_{month}.pdf"
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / filename
        try:
            rendered = render_to_pdf(
                "mass_balance.html",
                context,
                out_path,
                filters=_REPORT_FILTERS,
            )
        except PDFRenderError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"PDF render failed: {exc}",
            ) from exc
        pdf_bytes = rendered.pdf_path.read_bytes()
        sha256_hex = rendered.pdf_sha256
        page_count = rendered.page_count

    audit = AuditLog(
        table_name="mass_balance",
        record_id=_month_to_record_id(month),
        action="insert",
        old_values=None,
        new_values={
            "kind": "REPORT_EXPORT",
            "month": month,
            "format": "pdf",
            "sha256": sha256_hex,
            "page_count": page_count,
            "size_bytes": len(pdf_bytes),
        },
        changed_by=user.id,
    )
    db.add(audit)
    await db.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "X-Content-SHA256": sha256_hex,
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
