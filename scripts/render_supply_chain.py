"""Render the supply-chain diagram PDF for the RTFO-310825 bundle.

DB-driven: pulls supplier list + ISCC cert refs + aggregate volumes from
``daily_inputs`` joined to ``suppliers`` and ``certificates`` for the
configured reporting period. No hardcoded supplier list, no ANLA refs
(ELT-only RCF pathway is ISCC EU + UK RTFO; ANLA is irrelevant to
DfT submission).

Deterministic SHA-256 via shared ``app.services.pdf_renderer`` pipeline
(fixed ``generated_at``, no XMP metadata, full-font embed).

Usage::

    python3 scripts/render_supply_chain.py [--period YYYY-MM | --start YYYY-MM --end YYYY-MM] [--out PATH]

Defaults: period range 2025-01 .. 2025-08, output
``deliverables/RTFO-310825/04_compliance/01_supply_chain_diagram.pdf``.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from jinja2 import Environment

    from app.services.pdf_renderer import RenderResult  # type: ignore[import-not-found]

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
_BACKEND_DIR: Final[Path] = _REPO_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.services import pdf_renderer  # type: ignore[import-not-found]  # noqa: E402

_ORIGINAL_BUILD_ENV: Final = pdf_renderer._build_env

TEMPLATE_NAME: Final[str] = "supply_chain.html"
GENERATED_AT: Final[str] = "2026-05-21T00:00:00Z"
SUBMISSION_REF: Final[str] = "RTFO-310825"

DB_CONTAINER: Final[str] = "dft-project_db_1"
DB_USER: Final[str] = "dft"
DB_NAME: Final[str] = "dft"

_MONTH_NAMES: Final[dict[int, str]] = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


def _format_thousands(value: float, decimals: int = 2) -> str:
    rounded = round(float(value), decimals)
    formatted = f"{rounded:,.{decimals}f}"
    return formatted.replace(",", " ").replace(".", ",")


def fmt_num(value: float | int | None) -> str:
    if value is None:
        return "—"
    return _format_thousands(float(value), decimals=2)


def fmt_kg(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{_format_thousands(float(value), decimals=2)} kg"


def fmt_pct(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{_format_thousands(float(value), decimals=2)} %"


def _psql_json(query: str) -> Any:
    cmd = [
        "docker", "exec", DB_CONTAINER,
        "psql", "-U", DB_USER, "-d", DB_NAME,
        "-At", "-c", query,
    ]
    completed = subprocess.run(  # noqa: S603
        cmd, check=True, capture_output=True, text=True,
    )
    payload = completed.stdout.strip()
    if not payload or payload == "\\N":
        return None
    return json.loads(payload)


def _suppliers_query(start: str, end: str) -> str:
    return f"""
SELECT json_agg(t ORDER BY t.total_kg DESC) FROM (
    SELECT
        s.name AS name,
        COALESCE(s.country, '') AS country,
        COALESCE(
            (SELECT c2.cert_number
             FROM daily_inputs di2
             JOIN certificates c2 ON c2.id = di2.certificate_id
             WHERE di2.deleted_at IS NULL
               AND di2.supplier_id = s.id
               AND di2.entry_date >= DATE '{start}'
               AND di2.entry_date <= DATE '{end}'
             GROUP BY c2.id, c2.cert_number
             ORDER BY SUM(di2.total_input_kg) DESC NULLS LAST, c2.cert_number ASC
             LIMIT 1),
            'self-declared ≤5 t/m'
        ) AS cert_iscc_ref,
        SUM(di.total_input_kg)::float8 AS total_kg,
        COUNT(*)::int AS delivery_count
    FROM daily_inputs di
    JOIN suppliers s ON s.id = di.supplier_id
    WHERE di.deleted_at IS NULL
      AND s.deleted_at IS NULL
      AND di.entry_date >= DATE '{start}'
      AND di.entry_date <= DATE '{end}'
    GROUP BY s.id, s.name, s.country
) AS t;
"""


def _fetch_suppliers(start: str, end: str) -> tuple[list[dict[str, Any]], float]:
    raw = _psql_json(_suppliers_query(start, end)) or []
    grand_total = sum(float(r["total_kg"]) for r in raw if r.get("total_kg") is not None)
    out: list[dict[str, Any]] = []
    for r in raw:
        kg = float(r["total_kg"]) if r.get("total_kg") is not None else 0.0
        share = (kg / grand_total * 100.0) if grand_total > 0 else 0.0
        country = r.get("country") or ""
        country_label = {
            "CO": "Colombia",
            "US": "United States",
            "ES": "Spain",
            "PL": "Poland",
            "BE": "Belgium",
            "FR": "France",
            "DE": "Germany",
        }.get(country, country or "supplier of record")
        out.append({
            "name": r["name"],
            "country": country_label,
            "cert_iscc_ref": r.get("cert_iscc_ref") or "—",
            "total_kg": round(kg, 2),
            "share_pct": round(share, 2),
            "delivery_count": int(r.get("delivery_count") or 0),
        })
    return out, grand_total


def _period_bounds(start: str, end: str) -> tuple[str, str]:
    sy, sm = start.split("-")
    ey, em = end.split("-")
    start_iso = date(int(sy), int(sm), 1).isoformat()
    last_day = calendar.monthrange(int(ey), int(em))[1]
    end_iso = date(int(ey), int(em), last_day).isoformat()
    if start == end:
        label = f"{_MONTH_NAMES[int(sm)]} {sy}"
    else:
        label = f"{_MONTH_NAMES[int(sm)]} {sy} – {_MONTH_NAMES[int(em)]} {ey}"
    return start_iso, end_iso, label  # type: ignore[return-value]


def build_context(start_period: str, end_period: str) -> dict[str, Any]:
    start_iso, end_iso, label = _period_bounds(start_period, end_period)  # type: ignore[misc]
    suppliers, total_kg = _fetch_suppliers(start_iso, end_iso)
    return {
        "submission_ref": SUBMISSION_REF,
        "period_label": label,
        "period_start": start_iso,
        "period_end": end_iso,
        "generated_at": GENERATED_AT,
        "submitter_company": "OisteBio GmbH",
        "submitter_address": "Oberneuhofstrasse 5, 6340 Baar, Switzerland",
        "plant_name": "Girardot, Cundinamarca — Colombia",
        "feedstock": "ELT — End-of-Life Tyres",
        "product": "DEV-P100 — refined pyrolysis oil",
        "off_taker": "Crown Oil Limited (UK)",
        "regulator": "UK DfT — LCF Delivery Unit (RTFO RCF pathway)",
        "suppliers": suppliers,
        "total_input_kg": round(total_kg, 2),
        "supplier_count": len(suppliers),
    }


def _patched_env_factory() -> Environment:
    base_env: Environment = _ORIGINAL_BUILD_ENV()
    base_env.filters["fmt_num"] = fmt_num
    base_env.filters["fmt_kg"] = fmt_kg
    base_env.filters["fmt_pct"] = fmt_pct
    return base_env


def render(out_pdf: Path, start_period: str, end_period: str) -> RenderResult:
    pdf_renderer._build_env = _patched_env_factory
    try:
        result: RenderResult = pdf_renderer.render_to_pdf(
            template_name=TEMPLATE_NAME,
            context=build_context(start_period, end_period),
            output_path=out_pdf,
        )
        return result
    finally:
        pdf_renderer._build_env = _ORIGINAL_BUILD_ENV


def _default_output() -> Path:
    return (
        _REPO_ROOT
        / "deliverables"
        / SUBMISSION_REF
        / "04_compliance"
        / "01_supply_chain_diagram.pdf"
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Render supply-chain diagram PDF.")
    parser.add_argument("--start", default="2025-01", help="Start period YYYY-MM")
    parser.add_argument("--end", default="2025-08", help="End period YYYY-MM")
    parser.add_argument("--period", default=None, help="Single period YYYY-MM (sets start=end)")
    parser.add_argument("--out", type=Path, default=None, help="Output PDF path")
    args = parser.parse_args(argv[1:])

    if args.period:
        args.start = args.period
        args.end = args.period

    out_pdf = (args.out or _default_output()).resolve()
    result = render(out_pdf, args.start, args.end)

    size_kb = result.pdf_size_bytes / 1024
    on_disk_sha = hashlib.sha256(result.pdf_path.read_bytes()).hexdigest()

    print(f"Rendered:    {result.pdf_path}")
    print(f"Size:        {size_kb:.1f} KB ({result.pdf_size_bytes} bytes)")
    print(f"Pages:       {result.page_count}")
    print(f"Template:    {result.template_name}")
    print(f"SHA-256:     {result.pdf_sha256}")
    print(f"On-disk:     {on_disk_sha}")
    print(f"Side-car:    {result.pdf_sha256_path}")
    print(f"Rendered at: {result.rendered_at.isoformat()}")
    print(f"Generated at (context, fixed for determinism): {GENERATED_AT}")
    print(f"Sanity (UTC now): {datetime.now(UTC).isoformat()}")

    if on_disk_sha != result.pdf_sha256:
        print("ERROR: on-disk SHA-256 differs from renderer-reported digest", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
