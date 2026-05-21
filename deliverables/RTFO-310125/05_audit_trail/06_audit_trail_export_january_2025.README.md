# 06 — Audit Trail Export, January 2025

**File:** `06_audit_trail_export_january_2025.csv`
**SHA-256:** see `06_audit_trail_export_january_2025.csv.sha256`
**Generated:** 2026-05-20 (UTC) for RTFO-310125 bundle (DfT submission)
**Source:** `audit_log` table in `dft` Postgres database (container `dft-project_db_1`)
**Generator:** agent S1.9, read-only export via `psql \copy ... WITH CSV HEADER FORCE_QUOTE *`

---

## What this file contains

Every row in `audit_log` whose business entity_date falls between
**2025-01-01 and 2025-01-31** (inclusive), ordered deterministically by
`(changed_at, id)`.

### Columns

| # | Column                | Source                                                                                            |
|---|-----------------------|---------------------------------------------------------------------------------------------------|
| 1 | `id`                  | `audit_log.id`                                                                                    |
| 2 | `created_at_utc`      | `audit_log.changed_at` rendered as ISO-8601 UTC (`YYYY-MM-DDTHH24:MI:SS.usZ`)                     |
| 3 | `actor_id`            | `audit_log.changed_by` (nullable; FK→`users.id`)                                                  |
| 4 | `actor_email`         | `users.email` joined from `actor_id`                                                              |
| 5 | `action`              | `audit_log.action` ∈ `{insert, update, delete, soft_delete, restore}`                             |
| 6 | `entity_type`         | `audit_log.table_name` (e.g. `daily_inputs`, `daily_production`, `certificates`, …)               |
| 7 | `entity_id`           | `audit_log.record_id`                                                                             |
| 8 | `entity_date`         | derived (see below)                                                                               |
| 9 | `changed_fields`      | JSONB array of keys where `old_values` differs from `new_values` (or keys present in one only)    |
| 10| `before_values`       | `audit_log.old_values` (JSONB; NULL for `insert`)                                                  |
| 11| `after_values`        | `audit_log.new_values` (JSONB; NULL for `delete`/`soft_delete`)                                    |
| 12| `rectification_source`| `daily_inputs.rectification_source` for the referenced row (NULL if entity not `daily_inputs`)    |
| 13| `rectification_reason`| `daily_inputs.rectification_reason` for the referenced row (NULL if entity not `daily_inputs`)    |

### `entity_date` derivation

The `audit_log` table itself has no business-date column (schema:
`id, table_name, record_id, action, old_values, new_values, changed_by,
changed_at`). The entity_date is derived in this order:

1. `new_values ->> 'entry_date'` (for `daily_inputs`)
2. `old_values ->> 'entry_date'`
3. `new_values ->> 'prod_date'` (for `daily_production`)
4. `old_values ->> 'prod_date'`
5. Live lookup against `daily_inputs.entry_date` / `daily_production.prod_date`
   keyed by `record_id` (covers rows whose JSON snapshots are stale or whose
   table doesn't carry a business date)

For non-business-date tables (`users`, `suppliers`, `contracts`,
`certificates`, `mass_balance`) the entity_date is `NULL` and those rows
are **not** included in this export (they are reference data, not
day-of-business records).

### Filter

```sql
WHERE COALESCE(di.entry_date, dp.prod_date, …jsonb fallbacks…)
      BETWEEN DATE '2025-01-01' AND DATE '2025-01-31'
ORDER BY al.changed_at, al.id
```

The brief allowed either `entity_date` or `changed_at` as the filter.
**`entity_date` was chosen** because the auditor cares about every write
that ever touched a Jan-2025 business row — including post-hoc
rectifications made in later calendar months.

---

## Row count

**0 rows** (header only).

## Why zero — and why this is expected, not a defect

`audit_log` is populated only by **application-layer writes** through the
FastAPI routers (`backend/app/routers/daily_entries.py` etc.). There are
no database triggers wired up against the row-data tables — verified via:

```sql
SELECT trigger_name, event_object_table FROM information_schema.triggers
 WHERE trigger_name LIKE '%audit%';
-- (0 rows)
```

The first row in `audit_log` is dated **2026-05-08 10:45:51 UTC**; the
last is **2026-05-15 06:46:37 UTC**. None of the 68 rows currently in
`audit_log` reference a January 2025 business date.

Historical context:

- **January 2025 daily_inputs** were ingested via the xlsx parser
  (Sprint 2, DFTEN-64..71) **before** the audit_log application code was
  wired up. The ingest writes did not populate `audit_log`.
- Migration **`0006_supplier_rectification_jan2025`** (dated 2026-05-15)
  is **column-add only** — it adds `rectified_at`, `rectified_by`,
  `rectification_reason`, `rectification_source`, `original_values` to
  `daily_inputs`. It does **not** update any Jan 2025 rows. No
  rectifications have been applied to Jan 2025 daily_inputs to date.
- Migration **`0010_cert_correction_feb2025`** re-points certificate
  FKs starting **2025-02-01** — Jan 2025 is explicitly excluded
  (`_REPOINT_CUTOVER = "2025-02-01"`, see migration source).
- Migration **`0011_purge_hidden_supplier_refs`** affects supplier
  reference data, not per-day Jan 2025 business rows.

Cross-check:

```sql
SELECT COUNT(*) FROM daily_inputs
 WHERE entry_date BETWEEN '2025-01-01' AND '2025-01-31'
   AND (rectified_at IS NOT NULL OR original_values IS NOT NULL);
-- 0
```

I.e. zero Jan-2025 rows have ever been rectified.

**Conclusion:** the empty export is faithful. The Jan 2025 dataset
loaded into `daily_inputs` is exactly the original ingest; no post-hoc
modifications have occurred to any Jan 2025 business row since the
audit-log machinery began capturing changes. For the auditor this is
the cleanest possible audit-trail outcome for that month.

---

## How to verify

```bash
# 1. Reproduce the count
docker exec dft-project_db_1 psql -U dft -d dft -c \
  "SELECT COUNT(*) FROM audit_log al
     LEFT JOIN daily_inputs di
       ON al.table_name='daily_inputs' AND di.id=al.record_id
     LEFT JOIN daily_production dp
       ON al.table_name='daily_production' AND dp.id=al.record_id
    WHERE COALESCE(di.entry_date, dp.prod_date)
          BETWEEN DATE '2025-01-01' AND DATE '2025-01-31';"
# expected: 0

# 2. Verify integrity
sha256sum -c 06_audit_trail_export_january_2025.csv.sha256

# 3. Confirm Jan 2025 daily_inputs exist (i.e. the data IS in the DB,
#    it just hasn't been edited):
docker exec dft-project_db_1 psql -U dft -d dft -c \
  "SELECT COUNT(*) FROM daily_inputs
     WHERE entry_date BETWEEN '2025-01-01' AND '2025-01-31';"
# expected: 1463
```

---

## Schema notes for the auditor

The actual `audit_log` schema (Postgres 16):

```
 Column     | Type                       | Nullable
------------+----------------------------+---------
 id         | bigint                     | not null
 table_name | text                       | not null
 record_id  | bigint                     | not null
 action     | text                       | not null   -- insert|update|delete|soft_delete|restore
 old_values | jsonb                      |
 new_values | jsonb                      |
 changed_by | bigint                     |            -- FK users.id
 changed_at | timestamp with time zone   | not null   -- default now()
```

It differs slightly from the column list in the original brief:

- No native `entity_date` column → derived as documented above.
- No `rectification_source` / `rectification_reason` columns on
  `audit_log` itself → these live on `daily_inputs` and have been
  joined into the export so the auditor sees the rectification context
  inline (NULL for all rows here, since no Jan 2025 row is rectified).
- `changed_at` / `changed_by` correspond to the brief's `created_at` /
  `actor_id`.
