"""Backfill certificates.scope_material_groups + scope_raw + scope_parsed_at
+ scheme_pdf_detected by running cert_scope_parser over each cert PDF
on disk.

Usage:
    python3 scripts/backfill_cert_scope.py [--dry-run] [--cert-root PATH]
                                           [--only CERT_NUMBER]

Behaviour:
    * Reads every row in `certificates` with `pdf_ref IS NOT NULL`
      AND `deleted_at IS NULL`.
    * Resolves the PDF path under `--cert-root` (default
      `./data/certificates`).
    * Runs `app.services.cert_scope_parser.parse_cert_pdf`.
    * UPDATEs the 4 new columns by `cert_number` (portable, NOT by
      auto-id — per project_migration_row_id_portability).
    * Always sets `scope_parsed_at = now()` even when groups/raw are
      empty — so re-runs are explicit, not nullability-driven.
    * Prints a summary table at end: cert_number, db_scheme,
      detected_scheme (with MISMATCH flag), groups_count.

Safety:
    * `--dry-run` shows what would change without UPDATEs.
    * `--only CERT_NUMBER` limits to one cert (verification runs).
    * Never modifies `scheme` column (project_iscc_audit_safety).
    * Re-runnable: re-running overwrites with parser's current verdict
      — handy when parser is improved.

Per project_feedback_direct_db_queries: uses docker exec + psql so it
works regardless of the host's installed Python DB drivers.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Make the backend package importable when run from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.cert_scope_parser import parse_cert_pdf  # noqa: E402


DB_CONTAINER = os.environ.get("DFT_DB_CONTAINER", "dft-project_db_1")
DB_USER = os.environ.get("DFT_DB_USER", "dft")
DB_NAME = os.environ.get("DFT_DB_NAME", "dft")


def _psql_query(query: str) -> list[list[str]]:
    """Read-only SELECT — return rows as list of string lists."""
    cmd = [
        "docker", "exec", DB_CONTAINER,
        "psql", "-U", DB_USER, "-d", DB_NAME,
        "-t", "-A", "--field-separator=\x01",
        "-c", query,
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    rows: list[list[str]] = []
    for line in result.stdout.splitlines():
        line = line.rstrip("\n")
        if not line:
            continue
        rows.append(line.split("\x01"))
    return rows


def _psql_exec(sql: str) -> None:
    """Execute SQL via stdin so we can pass dollar-quoted blocks safely."""
    cmd = [
        "docker", "exec", "-i", DB_CONTAINER,
        "psql", "-U", DB_USER, "-d", DB_NAME,
        "-v", "ON_ERROR_STOP=1",
        "-f", "-",
    ]
    proc = subprocess.run(cmd, input=sql, text=True, capture_output=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"psql failed (exit {proc.returncode})")


def _quote_array(values: list[str], tag: str) -> str:
    """Build an ARRAY[...] literal with dollar-quoted elements.

    Empty list returns ``ARRAY[]::text[]`` (typed empty).
    """
    if not values:
        return "ARRAY[]::text[]"
    parts = [f"${tag}${v}${tag}$" for v in values]
    return "ARRAY[" + ", ".join(parts) + "]::text[]"


def _build_update_sql(
    cert_number: str,
    scheme_detected: str | None,
    material_groups: list[str],
    scope_raw: str,
    tag_seed: int,
) -> str:
    """Construct a single UPDATE statement using unique dollar-tags."""
    tag = f"b{tag_seed:04d}"
    arr = _quote_array(material_groups, f"{tag}g")
    if scheme_detected is None:
        scheme_clause = "NULL"
    else:
        scheme_clause = f"${tag}s${scheme_detected}${tag}s$"
    return (
        "UPDATE certificates SET\n"
        f"    scope_material_groups = {arr},\n"
        f"    scope_raw = ${tag}r${scope_raw}${tag}r$,\n"
        f"    scope_parsed_at = now(),\n"
        f"    scheme_pdf_detected = {scheme_clause},\n"
        "    updated_at = now()\n"
        f"WHERE cert_number = ${tag}n${cert_number}${tag}n$;\n"
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--cert-root",
        default="data/certificates",
        help="Root directory where pdf_ref paths are resolved (default: data/certificates)",
    )
    p.add_argument("--dry-run", action="store_true", help="Print plan, do not UPDATE")
    p.add_argument(
        "--only",
        default=None,
        help="Limit to a single cert_number (verification mode)",
    )
    args = p.parse_args()

    cert_root = Path(args.cert_root).resolve()
    if not cert_root.is_dir():
        sys.stderr.write(f"cert-root not found: {cert_root}\n")
        return 1

    only_clause = ""
    if args.only:
        # The query is single-quoted; escape any embedded apostrophe.
        safe = args.only.replace("'", "''")
        only_clause = f" AND cert_number = '{safe}'"

    rows = _psql_query(
        "SELECT cert_number, pdf_ref, scheme "
        "FROM certificates "
        "WHERE pdf_ref IS NOT NULL "
        "  AND deleted_at IS NULL"
        + only_clause
        + " ORDER BY cert_number"
    )

    if not rows:
        sys.stderr.write("no rows to process\n")
        return 0

    plan: list[tuple[str, str, str | None, list[str], str]] = []
    missing: list[tuple[str, str]] = []

    for cert_number, pdf_ref, db_scheme in rows:
        pdf_path = cert_root / pdf_ref
        if not pdf_path.is_file():
            missing.append((cert_number, str(pdf_path)))
            continue
        parsed = parse_cert_pdf(pdf_path)
        plan.append(
            (
                cert_number,
                db_scheme,
                parsed.scheme_detected,
                parsed.material_groups,
                parsed.raw,
            )
        )

    if missing:
        sys.stderr.write("WARN: pdf_ref points to a missing file (skipped):\n")
        for c, p in missing:
            sys.stderr.write(f"    {c}: {p}\n")

    # Build summary table for stdout
    print()
    print(f"{'cert_number':32s}  {'db_scheme':10s}  {'detected':12s}  groups")
    print("-" * 90)
    for cert_number, db_scheme, scheme_detected, groups, _raw in plan:
        flag = ""
        if scheme_detected and scheme_detected != db_scheme:
            flag = " ⚠ MISMATCH"
        det = scheme_detected or "—"
        groups_str = ", ".join(groups) if groups else "—"
        print(f"{cert_number:32s}  {db_scheme:10s}  {det:12s}  {groups_str}{flag}")

    if args.dry_run:
        print()
        print(f"[dry-run] {len(plan)} cert(s) would be updated. No DB change.")
        return 0

    # Apply UPDATEs in a single transaction so the run is all-or-nothing.
    sql_chunks = ["BEGIN;"]
    for i, (cert_number, _db_scheme, scheme_detected, groups, raw) in enumerate(plan):
        sql_chunks.append(
            _build_update_sql(cert_number, scheme_detected, groups, raw, i)
        )
    sql_chunks.append("COMMIT;")
    sql = "\n".join(sql_chunks)

    _psql_exec(sql)
    print()
    print(f"applied {len(plan)} UPDATE(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
