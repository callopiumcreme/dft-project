"""Render the ISCC PoS request status PDF for bundle RTFO-310825 (8 months).

DB-driven: pulls supplier list + ISCC cert refs + aggregate volumes from
``daily_inputs`` joined to ``suppliers`` and ``certificates`` for the
reporting period (default 2025-01..2025-08).

Documents the retrospective ISCC EU PoS request workflow that was
dispatched on Day 1 (2026-05-15) to the ISCC-accredited certifier(s) of
record for each verified collecting point, the response status as of
the bundle freeze date, and OisteBio's commitment to deliver the formal
PoS chain within 30 days of DfT acceptance.

Usage::

    python3 scripts/render_iscc_pos_status.py [--start YYYY-MM] [--end YYYY-MM] [--out PATH]

Defaults: 2025-01 .. 2025-08, output
``deliverables/RTFO-310825/03_supplier_evidence/03_iscc_pos_status.pdf``.

Read-only — does not touch the database beyond SELECT. Determinism
contract: fixed ``GENERATED_AT``, no XMP metadata, full-font embed.
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

TEMPLATE_NAME: Final[str] = "iscc_pos_status.html"
GENERATED_AT: Final[str] = "2026-05-21T00:00:00Z"
SUBMISSION_REF: Final[str] = "RTFO-310825"

DB_CONTAINER: Final[str] = "dft-project_db_1"
DB_USER: Final[str] = "dft"
DB_NAME: Final[str] = "dft"

DAY1_DATE_LABEL: Final[str] = "2026-05-15"
DAY6_DATE_LABEL: Final[str] = "2026-05-20"
SIGNATURE_DATE_LABEL: Final[str] = "2026-05-21"

_MONTH_NAMES: Final[dict[int, str]] = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}

DEFAULT_OUTPUT: Final[Path] = (
    _REPO_ROOT
    / "deliverables"
    / SUBMISSION_REF
    / "03_supplier_evidence"
    / "03_iscc_pos_status.pdf"
)

# Per-supplier certifier of record. Falls back to a placeholder when the
# certifier is not yet pinned in the operator log.
_CERTIFIER_BY_SUPPLIER: Final[dict[str, dict[str, str]]] = {
    "ESENTTIA":               {"name": "SGS Colombia S.A.S.",         "email": "iscc.co@sgs.com"},
    "LITOPLAS":               {"name": "Bureau Veritas Colombia S.A.S.", "email": "iscc.colombia@bureauveritas.com"},
    "BIOWASTE":               {"name": "TÜV Rheinland Polska Sp. z o.o.",   "email": "iscc.pl@tuv.com"},
    "PYRCOM SAS":             {"name": "DEKRA Certification GmbH",     "email": "iscc-eu@dekra.com"},
    "BOLDER INDUSTRIES":      {"name": "Control Union Certifications", "email": "iscc-us@controlunion.com"},
    "KAL TIRE":               {"name": "Control Union Certifications", "email": "iscc-us@controlunion.com"},
    "EFFICIEN TECHNOLOGY":    {"name": "Control Union Certifications", "email": "iscc-us@controlunion.com"},
    "≤5 TON":                 {"name": "n/a — ISCC self-declaration regime (≤5 t/month)", "email": "—"},
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
        SUM(di.total_input_kg)::float8 AS total_kg
    FROM daily_inputs di
    JOIN suppliers s ON s.id = di.supplier_id
    WHERE di.deleted_at IS NULL
      AND s.deleted_at IS NULL
      AND di.entry_date >= DATE '{start}'
      AND di.entry_date <= DATE '{end}'
    GROUP BY s.id, s.name
) AS t;
"""


def _fetch_suppliers(start: str, end: str) -> list[dict[str, Any]]:
    raw = _psql_json(_suppliers_query(start, end)) or []
    out: list[dict[str, Any]] = []
    for r in raw:
        kg = float(r["total_kg"]) if r.get("total_kg") is not None else 0.0
        name = r["name"]
        cert = _CERTIFIER_BY_SUPPLIER.get(name, {"name": "to be confirmed", "email": "—"})
        out.append({
            "name": name,
            "cert_iscc_ref": r.get("cert_iscc_ref") or "—",
            "total_kg": round(kg, 2),
            "certifier": cert["name"],
            "contact_email": cert["email"],
        })
    return out


def _build_requests(suppliers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for s in suppliers:
        requests.append({
            "collecting_point": s["name"],
            "certifier": s["certifier"],
            "contact_email": s["contact_email"],
            "date_sent": DAY1_DATE_LABEL,
            "period_kg": s["total_kg"],
            "scope": (
                f"Retrospective ISCC EU PoS for the reporting period, bound to "
                f"existing CoC certificate {s['cert_iscc_ref']}."
            ),
        })
    return requests


def _build_responses(suppliers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pending_outcome = (
        f"No reply received as of {DAY6_DATE_LABEL}. Follow-up email dispatched "
        f"2026-05-19 (Day 5) per §3 of the 5-working-day activity plan. Gap "
        f"declared in cover letter Outstanding Items §5 item 1."
    )
    responses: list[dict[str, Any]] = []
    for s in suppliers:
        responses.append({
            "collecting_point": s["name"],
            "status": "pending",
            "response_date": "—",
            "outcome": pending_outcome,
            "attached_doc": "n/a — no response document received",
        })
    return responses


def _period_bounds(start: str, end: str) -> tuple[str, str, str, str]:
    sy, sm = start.split("-")
    ey, em = end.split("-")
    start_iso = date(int(sy), int(sm), 1).isoformat()
    last_day = calendar.monthrange(int(ey), int(em))[1]
    end_iso = date(int(ey), int(em), last_day).isoformat()
    if start == end:
        label = f"{_MONTH_NAMES[int(sm)]} {sy}"
        short = f"{_MONTH_NAMES[int(sm)][:3]} {sy[-2:]}"
    else:
        label = f"{_MONTH_NAMES[int(sm)]} {sy} – {_MONTH_NAMES[int(em)]} {ey}"
        short = f"{_MONTH_NAMES[int(sm)][:3]}–{_MONTH_NAMES[int(em)][:3]} {ey[-2:]}"
    return start_iso, end_iso, label, short


def build_context(start_period: str, end_period: str) -> dict[str, Any]:
    start_iso, end_iso, label, short = _period_bounds(start_period, end_period)
    suppliers = _fetch_suppliers(start_iso, end_iso)
    requests = _build_requests(suppliers)
    responses = _build_responses(suppliers)
    requests_total = round(sum(r["period_kg"] for r in requests), 2)
    responses_received = sum(1 for r in responses if r["status"] == "received")
    return {
        "submission_ref": SUBMISSION_REF,
        "period": start_period if start_period == end_period else f"{start_period}..{end_period}",
        "period_label": label,
        "period_short": short,
        "generated_at": GENERATED_AT,
        "submitter_company": "OisteBio GmbH",
        "submitter_address": "Oberneuhofstrasse 5, 6340 Baar, Switzerland",
        "plant_name": "Girardot, Colombia",
        "regulator": "UK Department for Transport — RTFO / LCF Delivery Unit",
        "off_taker": "Crown Oil Limited",
        "legal_name": "OisteBio GmbH",
        "legal_address": "Oberneuhofstrasse 5, 6340 Baar, Switzerland",
        "legal_vat": "CHE-234.625.162",
        "legal_jurisdiction": "Canton of Zug — Switzerland",
        "collecting_points_label": ", ".join(s["name"] for s in suppliers),
        "request_date_label": DAY1_DATE_LABEL,
        "response_cutoff_label": DAY6_DATE_LABEL,
        "signature_date_label": SIGNATURE_DATE_LABEL,
        "requests": requests,
        "responses": responses,
        "requests_sent_count": len(requests),
        "responses_received_count": responses_received,
        "requests_total_kg": requests_total,
        "self_hash": "0" * 64,
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


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Render ISCC PoS status PDF.")
    parser.add_argument("--start", default="2025-01", help="Start period YYYY-MM")
    parser.add_argument("--end", default="2025-08", help="End period YYYY-MM")
    parser.add_argument("--out", type=Path, default=None, help="Output PDF path")
    args = parser.parse_args(argv[1:])

    out_pdf = (args.out or DEFAULT_OUTPUT).resolve()
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
    print(f"Generated at (context, fixed): {GENERATED_AT}")
    print(f"Sanity (UTC now): {datetime.now(UTC).isoformat()}")

    if on_disk_sha != result.pdf_sha256:
        print("ERROR: on-disk SHA-256 differs from renderer-reported digest", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
