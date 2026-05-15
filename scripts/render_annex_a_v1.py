"""Render Annex A v1 from real January 2025 DB data (E1-S1.5).

Pulls daily mass-balance rows from ``mv_mass_balance_daily``, monthly totals
from ``mv_mass_balance_monthly``, and supplier breakdown from
``daily_inputs`` joined to ``suppliers`` + ``certificates``. Renders the
same Annex A template Worker F built (``templates/reports/mass_balance.html``)
and emits the PDF plus a SHA-256 side-car at the RTFO deliverable path.

Run inside repo root:

    python3 scripts/render_annex_a_v1.py

Or override the month / output path:

    python3 scripts/render_annex_a_v1.py --month 2025-01 --out path/to.pdf

Environment variables: ``DFT_DB_HOST`` (default ``localhost``), ``DFT_DB_PORT``
(default ``15432``), ``DFT_DB_USER`` (default ``dft``), ``DFT_DB_PASSWORD``
(default reads ``POSTGRES_PASSWORD`` from ``.env``), ``DFT_DB_NAME``
(default ``dft``).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pypdf import PdfReader
from weasyprint import HTML

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = REPO_ROOT / "templates" / "reports"
TEMPLATE_NAME = "mass_balance.html"
DEFAULT_OUT = (
    REPO_ROOT
    / "deliverables"
    / "RTFO-310125"
    / "01_annex_a_mass_balance"
    / "02_mass_balance_january_2025_v1.pdf"
)


# ---------------------------------------------------------------------------
# Jinja numeric filters (mirrored from scripts/render_mass_balance_sample.py
# so the template renders identically). Comma decimal, thin-space thousands.
# ---------------------------------------------------------------------------
def _format_thousands(value: float, decimals: int = 2) -> str:
    rounded = round(float(value), decimals)
    formatted = f"{rounded:,.{decimals}f}"
    return formatted.replace(",", " ").replace(".", ",")


def fmt_num(value: Any) -> str:
    if value is None:
        return "—"
    return _format_thousands(float(value), decimals=2)


def fmt_num_signed(value: Any) -> str:
    if value is None:
        return "—"
    v = float(value)
    sign = "+" if v >= 0 else "−"
    return f"{sign}{_format_thousands(abs(v), decimals=2)}"


def fmt_kg(value: Any) -> str:
    return f"{fmt_num(value)} kg" if value is not None else "—"


def fmt_kg_signed(value: Any) -> str:
    return f"{fmt_num_signed(value)} kg" if value is not None else "—"


def fmt_l(value: Any) -> str:
    return f"{fmt_num(value)} L" if value is not None else "—"


def fmt_pct(value: Any) -> str:
    if value is None:
        return "—"
    return f"{_format_thousands(float(value), decimals=2)} %"


def fmt_pct_signed(value: Any) -> str:
    if value is None:
        return "—"
    v = float(value)
    sign = "+" if v >= 0 else "−"
    return f"{sign}{_format_thousands(abs(v), decimals=2)} %"


# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------
def _load_env_password() -> str:
    env_path = REPO_ROOT / ".env"
    if not env_path.is_file():
        return ""
    for line in env_path.read_text().splitlines():
        if line.startswith("POSTGRES_PASSWORD="):
            return line.split("=", 1)[1].strip()
    return ""


def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.environ.get("DFT_DB_HOST", "localhost"),
        port=int(os.environ.get("DFT_DB_PORT", "15432")),
        user=os.environ.get("DFT_DB_USER", "dft"),
        password=os.environ.get("DFT_DB_PASSWORD") or _load_env_password(),
        dbname=os.environ.get("DFT_DB_NAME", "dft"),
    )


def _dec(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    return float(v)


def _fetch_daily(conn: psycopg2.extensions.connection, month_start: date, month_end: date) -> list[dict[str, Any]]:
    sql = """
        SELECT day, input_total_kg, eu_prod_kg, plus_prod_kg,
               eu_prod_litres, plus_prod_litres,
               output_total_kg, closure_diff_pct
        FROM mv_mass_balance_daily
        WHERE day >= %s AND day < %s
        ORDER BY day
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (month_start, month_end))
        rows: list[dict[str, Any]] = []
        for r in cur.fetchall():
            input_kg = _dec(r["input_total_kg"]) or 0.0
            output_kg = _dec(r["output_total_kg"]) or 0.0
            closure_kg = output_kg - input_kg
            rows.append(
                {
                    "date": r["day"].isoformat(),
                    "input_kg": input_kg,
                    "eu_prod_kg": _dec(r["eu_prod_kg"]) or 0.0,
                    "plus_prod_kg": _dec(r["plus_prod_kg"]) or 0.0,
                    "eu_prod_litres": _dec(r["eu_prod_litres"]) or 0.0,
                    "plus_prod_litres": _dec(r["plus_prod_litres"]) or 0.0,
                    "c14_pct": None,
                    "closure_diff_kg": closure_kg,
                }
            )
    return rows


def _fetch_monthly(
    conn: psycopg2.extensions.connection, month_start: date
) -> dict[str, Any] | None:
    sql = """
        SELECT input_total_kg, eu_prod_kg, plus_prod_kg,
               eu_prod_litres, plus_prod_litres,
               output_total_kg, closure_diff_pct
        FROM mv_mass_balance_monthly
        WHERE month = %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (month_start,))
        row = cur.fetchone()
        if row is None:
            return None
        input_kg = _dec(row["input_total_kg"]) or 0.0
        output_kg = _dec(row["output_total_kg"]) or 0.0
        closure_kg = output_kg - input_kg
        return {
            "input_kg": input_kg,
            "eu_prod_kg": _dec(row["eu_prod_kg"]) or 0.0,
            "plus_prod_kg": _dec(row["plus_prod_kg"]) or 0.0,
            "eu_prod_litres": _dec(row["eu_prod_litres"]) or 0.0,
            "plus_prod_litres": _dec(row["plus_prod_litres"]) or 0.0,
            "c14_pct": None,
            "closure_diff_kg": closure_kg,
            "closure_diff_pct": _dec(row["closure_diff_pct"]) or 0.0,
        }


def _fetch_suppliers(
    conn: psycopg2.extensions.connection, month_start: date, month_end: date
) -> list[dict[str, Any]]:
    sql = """
        SELECT s.name,
               COALESCE(MAX(c.cert_number), '—') AS cert_iscc_ref,
               SUM(di.total_input_kg) AS total_kg
        FROM daily_inputs di
        JOIN suppliers s ON s.id = di.supplier_id
        LEFT JOIN certificates c ON c.id = di.certificate_id
        WHERE di.entry_date >= %s AND di.entry_date < %s
          AND di.deleted_at IS NULL
        GROUP BY s.name
        ORDER BY total_kg DESC
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (month_start, month_end))
        rows = cur.fetchall()
    total = sum(_dec(r["total_kg"]) or 0.0 for r in rows) or 1.0
    out: list[dict[str, Any]] = []
    for r in rows:
        kg = _dec(r["total_kg"]) or 0.0
        out.append(
            {
                "name": r["name"],
                "cert_iscc_ref": r["cert_iscc_ref"] or "—",
                "total_kg": kg,
                "share_pct": round(kg / total * 100, 2),
            }
        )
    return out


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
def _build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["fmt_num"] = fmt_num
    env.filters["fmt_num_signed"] = fmt_num_signed
    env.filters["fmt_kg"] = fmt_kg
    env.filters["fmt_kg_signed"] = fmt_kg_signed
    env.filters["fmt_l"] = fmt_l
    env.filters["fmt_pct"] = fmt_pct
    env.filters["fmt_pct_signed"] = fmt_pct_signed
    return env


ITALIAN_MONTHS = {
    1: "Gennaio",
    2: "Febbraio",
    3: "Marzo",
    4: "Aprile",
    5: "Maggio",
    6: "Giugno",
    7: "Luglio",
    8: "Agosto",
    9: "Settembre",
    10: "Ottobre",
    11: "Novembre",
    12: "Dicembre",
}


def build_context(month: str) -> dict[str, Any]:
    year_s, month_s = month.split("-")
    year_i, month_i = int(year_s), int(month_s)
    month_start = date(year_i, month_i, 1)
    next_month = date(year_i + (month_i // 12), (month_i % 12) + 1, 1)

    with _connect() as conn:
        daily_rows = _fetch_daily(conn, month_start, next_month)
        monthly = _fetch_monthly(conn, month_start)
        suppliers = _fetch_suppliers(conn, month_start, next_month)

    if monthly is None:
        raise SystemExit(f"No monthly row found for {month} — refresh MVs first.")

    return {
        "submission_ref": "RTFO-310125",
        "period": month,
        "period_label": f"{ITALIAN_MONTHS[month_i]} {year_i}",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "submitter_company": "OisteBio GmbH",
        "submitter_address": "Oberneuhofstrasse 5, 6340 Baar, Switzerland",
        "plant_name": "Girardot, Colombia",
        "feedstock": "ELT — End-of-Life Tyres",
        "product": "DEV-P100 — refined pyrolysis oil",
        "off_taker": "Crown Oil UK",
        "regulator": "UK DfT — LCF Delivery Unit",
        "totals": monthly,
        "daily_rows": daily_rows,
        "suppliers": suppliers,
        "annex_a_hash": "(computed post-render — see side-car)",
    }


def render(month: str, out_pdf: Path) -> tuple[Path, str, int]:
    env = _build_env()
    template = env.get_template(TEMPLATE_NAME)
    html_str = template.render(**build_context(month))
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_str, base_url=str(TEMPLATE_DIR)).write_pdf(str(out_pdf))
    digest = hashlib.sha256(out_pdf.read_bytes()).hexdigest()
    pages = len(PdfReader(str(out_pdf)).pages)
    sidecar = out_pdf.with_suffix(out_pdf.suffix + ".sha256")
    sidecar.write_text(f"{digest}  {out_pdf.name}\n")
    return out_pdf, digest, pages


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--month", default="2025-01")
    p.add_argument("--out", default=str(DEFAULT_OUT))
    args = p.parse_args(argv[1:])
    out_pdf = Path(args.out).resolve()
    rendered, digest, pages = render(args.month, out_pdf)
    size_kb = rendered.stat().st_size / 1024
    print(f"Rendered: {rendered}")
    print(f"Size: {size_kb:.1f} KB  Pages: {pages}")
    print(f"SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
