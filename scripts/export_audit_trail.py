"""Export audit-trail CSV for one calendar month into an RTFO bundle.

Usage:
    python3 scripts/export_audit_trail.py --period YYYY-MM --out PATH/TO/FILE.csv

Output:
    - PATH/TO/FILE.csv  (deterministic, header always written even for 0 rows)
    - PATH/TO/FILE.csv.sha256

Column layout matches RTFO-310125 reference:
    id, created_at_utc, actor_id, actor_email, action, entity_type, entity_id,
    entity_date, changed_fields, before_values, after_values,
    rectification_source, rectification_reason

Filter logic (per README):
    - entity_date is derived from live JOIN to daily_inputs.entry_date /
      daily_production.prod_date, falling back to JSONB snapshots.
    - Only daily_inputs and daily_production rows are exported (other
      table_names have no business date and are excluded, matching Jan template).
    - Rows ordered deterministically by (changed_at, id).

changed_fields derivation:
    - Sorted comma-joined set of keys that differ between old_values and
      new_values (or keys present in either for insert/delete).

Constraints:
    - DB read-only — no writes.
    - Deterministic output (same DB state → same bytes).
    - DO NOT commit or push.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

DB_CONTAINER = "dft-project_db_1"
DB_USER = "dft"
DB_NAME = "dft"

COLUMNS = [
    "id",
    "created_at_utc",
    "actor_id",
    "actor_email",
    "action",
    "entity_type",
    "entity_id",
    "entity_date",
    "changed_fields",
    "before_values",
    "after_values",
    "rectification_source",
    "rectification_reason",
]


def _psql_rows(query: str) -> list[list[str]]:
    """Run psql and return rows as lists of strings (empty string for NULL)."""
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
        if line == "":
            continue
        rows.append(line.split("\x01"))
    return rows


def _changed_fields(old_json: str, new_json: str) -> str:
    """Return sorted comma-joined set of differing/new/removed keys."""
    old: dict = {}
    new: dict = {}
    if old_json:
        try:
            old = json.loads(old_json)
        except json.JSONDecodeError:
            pass
    if new_json:
        try:
            new = json.loads(new_json)
        except json.JSONDecodeError:
            pass

    all_keys = set(old.keys()) | set(new.keys())
    changed = sorted(k for k in all_keys if old.get(k) != new.get(k))
    return ",".join(changed)


def build_query(start_date: str, end_date: str) -> str:
    """Build the SELECT query for a given date range (inclusive)."""
    return f"""
SELECT
    al.id::text,
    to_char(al.changed_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') AS created_at_utc,
    COALESCE(al.changed_by::text, '')                        AS actor_id,
    COALESCE(u.email, '')                                     AS actor_email,
    al.action,
    al.table_name                                             AS entity_type,
    al.record_id::text                                        AS entity_id,
    COALESCE(
        di.entry_date::text,
        dp.prod_date::text,
        al.new_values->>'entry_date',
        al.old_values->>'entry_date',
        al.new_values->>'prod_date',
        al.old_values->>'prod_date'
    )                                                         AS entity_date,
    COALESCE(al.old_values::text, '')                        AS before_values,
    COALESCE(al.new_values::text, '')                        AS after_values,
    COALESCE(di.rectification_source, '')                    AS rectification_source,
    COALESCE(di.rectification_reason, '')                    AS rectification_reason
FROM audit_log al
LEFT JOIN users u ON u.id = al.changed_by
LEFT JOIN daily_inputs di
       ON al.table_name = 'daily_inputs' AND di.id = al.record_id
LEFT JOIN daily_production dp
       ON al.table_name = 'daily_production' AND dp.id = al.record_id
WHERE al.table_name IN ('daily_inputs', 'daily_production')
  AND COALESCE(
        di.entry_date,
        dp.prod_date,
        (al.new_values->>'entry_date')::date,
        (al.old_values->>'entry_date')::date,
        (al.new_values->>'prod_date')::date,
        (al.old_values->>'prod_date')::date
      ) BETWEEN DATE '{start_date}' AND DATE '{end_date}'
ORDER BY al.changed_at, al.id
"""


def export_month(period: str, out_path: Path) -> int:
    """Export one month's audit trail. Returns row count."""
    year, month = map(int, period.split("-"))
    last_day = calendar.monthrange(year, month)[1]
    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year:04d}-{month:02d}-{last_day:02d}"

    query = build_query(start_date, end_date)
    raw_rows = _psql_rows(query)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writerow(COLUMNS)
        for raw in raw_rows:
            # raw columns order from SELECT:
            # 0:id 1:created_at_utc 2:actor_id 3:actor_email 4:action
            # 5:entity_type 6:entity_id 7:entity_date
            # 8:before_values 9:after_values
            # 10:rectification_source 11:rectification_reason
            if len(raw) < 12:
                # pad if NULL columns collapsed
                raw = raw + [""] * (12 - len(raw))
            before = raw[8]
            after = raw[9]
            changed = _changed_fields(before, after)
            row = [
                raw[0],   # id
                raw[1],   # created_at_utc
                raw[2],   # actor_id
                raw[3],   # actor_email
                raw[4],   # action
                raw[5],   # entity_type
                raw[6],   # entity_id
                raw[7],   # entity_date
                changed,  # changed_fields (computed)
                before,   # before_values
                after,    # after_values
                raw[10],  # rectification_source
                raw[11],  # rectification_reason
            ]
            writer.writerow(row)

    # Write SHA-256 sidecar
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    sha_path = out_path.with_suffix(".csv.sha256")
    sha_path.write_text(f"{digest}  {out_path.name}\n", encoding="utf-8")

    return len(raw_rows)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Export audit trail CSV for one month.")
    parser.add_argument("--period", required=True, help="YYYY-MM (e.g. 2025-02)")
    parser.add_argument("--out", required=True, help="Output CSV path")
    args = parser.parse_args(argv[1:])

    out_path = Path(args.out).resolve()
    count = export_month(args.period, out_path)
    sha_path = out_path.with_suffix(".csv.sha256")
    digest = sha_path.read_text().split()[0]

    print(f"Period:    {args.period}")
    print(f"Rows:      {count}")
    print(f"Output:    {out_path}")
    print(f"SHA-256:   {digest}")
    print(f"Sidecar:   {sha_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
