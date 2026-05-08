"""Ingest parsed xlsx into Postgres — dry-run validator + live bulk insert.

Usage:
    # Inside backend container (DATABASE_URL points to db:5432):
    python scripts/ingest_xlsx.py /path/to/file.xlsx --dry-run
    python scripts/ingest_xlsx.py /path/to/file.xlsx --commit

Idempotent on (source_file, source_row) — re-running --commit skips already-inserted rows.

Validates:
  - supplier_code resolves in suppliers table
  - cert_number resolves in certificates (or NULL allowed)
  - contract_code resolves in contracts (or NULL allowed)
  - duplicate (source_file, source_row) tuples
  - daily_production.prod_date uniqueness
  - arithmetic sanity: per-day sum(total_input_kg) sanity check (warning only)
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections import defaultdict
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# parse_xlsx lives next to this script
sys.path.insert(0, str(Path(__file__).parent))
from parse_xlsx import DailyInput, DailyProduction, parse_workbook  # noqa: E402

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dft:dft@db:5432/dft",
)


async def fetch_anagrafica(conn) -> dict[str, dict[str, int]]:
    suppliers = (await conn.execute(text("SELECT id, code FROM suppliers"))).all()
    certs = (await conn.execute(text("SELECT id, cert_number FROM certificates"))).all()
    contracts = (await conn.execute(text("SELECT id, code FROM contracts"))).all()
    return {
        "supplier": {r.code: r.id for r in suppliers},
        "cert": {r.cert_number: r.id for r in certs},
        "contract": {r.code: r.id for r in contracts},
    }


async def fetch_existing_keys(
    conn, source_file: str
) -> tuple[set[tuple[str, int]], set[tuple[str, int]]]:
    pat = f"{source_file}#%"
    in_rows = (
        await conn.execute(
            text(
                "SELECT source_file, source_row FROM daily_inputs "
                "WHERE (source_file = :sf OR source_file LIKE :pat) "
                "AND deleted_at IS NULL"
            ),
            {"sf": source_file, "pat": pat},
        )
    ).all()
    pr_rows = (
        await conn.execute(
            text(
                "SELECT source_file, source_row FROM daily_production "
                "WHERE (source_file = :sf OR source_file LIKE :pat) "
                "AND deleted_at IS NULL"
            ),
            {"sf": source_file, "pat": pat},
        )
    ).all()
    return (
        {(r.source_file, r.source_row) for r in in_rows},
        {(r.source_file, r.source_row) for r in pr_rows},
    )


def validate(
    inputs: list[DailyInput],
    prods: list[DailyProduction],
    anagrafica: dict[str, dict[str, int]],
    existing_inputs: set[tuple[str, int]],
    existing_prods: set[tuple[str, int]],
) -> dict:
    sup_map = anagrafica["supplier"]
    cert_map = anagrafica["cert"]
    contract_map = anagrafica["contract"]

    unknown_suppliers: dict[str, int] = defaultdict(int)
    unknown_certs: dict[str, int] = defaultdict(int)
    unknown_contracts: dict[str, int] = defaultdict(int)
    seen_input_keys: set[tuple[str, int]] = set()
    duplicate_input_keys: list[tuple[str, int]] = []
    seen_prod_dates: set = set()
    duplicate_prod_dates: list = []
    skipped_inputs_existing = 0
    skipped_prods_existing = 0

    valid_inputs: list[DailyInput] = []
    for i in inputs:
        key = (i.source_file, i.source_row)
        if key in existing_inputs:
            skipped_inputs_existing += 1
            continue
        if key in seen_input_keys:
            duplicate_input_keys.append(key)
            continue
        seen_input_keys.add(key)

        if i.supplier_code not in sup_map:
            unknown_suppliers[i.supplier_code] += 1
            continue
        if i.cert_number is not None and i.cert_number not in cert_map:
            unknown_certs[i.cert_number] += 1
        if i.contract_code is not None and i.contract_code not in contract_map:
            unknown_contracts[i.contract_code] += 1
        valid_inputs.append(i)

    valid_prods: list[DailyProduction] = []
    for p in prods:
        if (p.source_file, p.source_row) in existing_prods:
            skipped_prods_existing += 1
            continue
        if p.prod_date in seen_prod_dates:
            duplicate_prod_dates.append(p.prod_date)
            continue
        seen_prod_dates.add(p.prod_date)
        valid_prods.append(p)

    per_day_input_sum: dict = defaultdict(float)
    for i in valid_inputs:
        per_day_input_sum[i.entry_date] += i.car_kg + i.truck_kg + i.special_kg

    closure_warnings: list[str] = []
    prod_by_date = {p.prod_date: p for p in valid_prods}
    for d, total_in in per_day_input_sum.items():
        prod = prod_by_date.get(d)
        if prod and prod.kg_to_production is not None:
            diff_pct = abs(total_in - prod.kg_to_production) / max(total_in, 1) * 100
            if diff_pct > 5.0:
                closure_warnings.append(
                    f"  {d}: inputs={total_in:.0f}kg vs kg_to_production={prod.kg_to_production:.0f}kg (Δ {diff_pct:.1f}%)"
                )

    return {
        "valid_inputs": valid_inputs,
        "valid_prods": valid_prods,
        "unknown_suppliers": dict(unknown_suppliers),
        "unknown_certs": dict(unknown_certs),
        "unknown_contracts": dict(unknown_contracts),
        "duplicate_input_keys": duplicate_input_keys,
        "duplicate_prod_dates": duplicate_prod_dates,
        "skipped_inputs_existing": skipped_inputs_existing,
        "skipped_prods_existing": skipped_prods_existing,
        "closure_warnings": closure_warnings,
    }


def print_report(parsed_in: int, parsed_pr: int, v: dict) -> None:
    print("\n=== INGEST REPORT ===")
    print(f"parsed:           {parsed_in} inputs, {parsed_pr} production rows")
    print(f"valid:            {len(v['valid_inputs'])} inputs, {len(v['valid_prods'])} production rows")
    print(f"already in db:    {v['skipped_inputs_existing']} inputs, {v['skipped_prods_existing']} prods")
    if v["unknown_suppliers"]:
        print(f"\n!! unknown suppliers ({sum(v['unknown_suppliers'].values())} rows):")
        for k, n in sorted(v["unknown_suppliers"].items()):
            print(f"   {k!r}: {n} rows")
    if v["unknown_certs"]:
        print(f"\n!! unknown certs (warning, kept as NULL):")
        for k, n in sorted(v["unknown_certs"].items()):
            print(f"   {k!r}: {n} rows")
    if v["unknown_contracts"]:
        print(f"\n!! unknown contracts (warning, kept as NULL):")
        for k, n in sorted(v["unknown_contracts"].items()):
            print(f"   {k!r}: {n} rows")
    if v["duplicate_input_keys"]:
        print(f"\n!! duplicate input source_rows: {v['duplicate_input_keys'][:10]} ...")
    if v["duplicate_prod_dates"]:
        print(f"\n!! duplicate prod_dates: {v['duplicate_prod_dates'][:10]} ...")
    if v["closure_warnings"]:
        print(f"\n!! closure mismatches > 5% ({len(v['closure_warnings'])} days):")
        for w in v["closure_warnings"][:10]:
            print(w)
        if len(v["closure_warnings"]) > 10:
            print(f"   ... +{len(v['closure_warnings']) - 10} more")


INSERT_INPUT_SQL = text(
    "INSERT INTO daily_inputs ("
    "  entry_date, entry_time, supplier_id, certificate_id, contract_id,"
    "  ersv_number, car_kg, truck_kg, special_kg,"
    "  theor_veg_pct, manuf_veg_pct, c14_analysis,"
    "  source_file, source_row"
    ") VALUES ("
    "  :entry_date, :entry_time, :supplier_id, :certificate_id, :contract_id,"
    "  :ersv_number, :car_kg, :truck_kg, :special_kg,"
    "  :theor_veg_pct, :manuf_veg_pct, :c14_analysis,"
    "  :source_file, :source_row"
    ")"
)

INSERT_PROD_SQL = text(
    "INSERT INTO daily_production ("
    "  prod_date, kg_to_production, eu_prod_kg, plus_prod_kg,"
    "  carbon_black_kg, metal_scrap_kg, h2o_kg, gas_syngas_kg, losses_kg,"
    "  output_eu_kg, contract_ref, pos_number, source_file, source_row"
    ") VALUES ("
    "  :prod_date, :kg_to_production, :eu_prod_kg, :plus_prod_kg,"
    "  :carbon_black_kg, :metal_scrap_kg, :h2o_kg, :gas_syngas_kg, :losses_kg,"
    "  :output_eu_kg, :contract_ref, :pos_number, :source_file, :source_row"
    ") ON CONFLICT (prod_date) DO NOTHING"
)


async def insert_rows(
    conn,
    valid_inputs: list[DailyInput],
    valid_prods: list[DailyProduction],
    anagrafica: dict[str, dict[str, int]],
) -> tuple[int, int]:
    sup = anagrafica["supplier"]
    cert = anagrafica["cert"]
    contract = anagrafica["contract"]

    if valid_inputs:
        params = [
            {
                "entry_date": i.entry_date,
                "entry_time": i.entry_time,
                "supplier_id": sup[i.supplier_code],
                "certificate_id": cert.get(i.cert_number) if i.cert_number else None,
                "contract_id": contract.get(i.contract_code) if i.contract_code else None,
                "ersv_number": i.ersv_number,
                "car_kg": i.car_kg,
                "truck_kg": i.truck_kg,
                "special_kg": i.special_kg,
                "theor_veg_pct": i.theor_veg_pct,
                "manuf_veg_pct": i.manuf_veg_pct,
                "c14_analysis": i.c14_analysis,
                "source_file": i.source_file,
                "source_row": i.source_row,
            }
            for i in valid_inputs
        ]
        await conn.execute(INSERT_INPUT_SQL, params)

    if valid_prods:
        params = [
            {
                "prod_date": p.prod_date,
                "kg_to_production": p.kg_to_production,
                "eu_prod_kg": p.eu_prod_kg,
                "plus_prod_kg": p.plus_prod_kg,
                "carbon_black_kg": p.carbon_black_kg,
                "metal_scrap_kg": p.metal_scrap_kg,
                "h2o_kg": p.h2o_kg,
                "gas_syngas_kg": p.gas_syngas_kg,
                "losses_kg": p.losses_kg,
                "output_eu_kg": p.output_eu_kg,
                "contract_ref": p.contract_ref,
                "pos_number": p.pos_number,
                "source_file": p.source_file,
                "source_row": p.source_row,
            }
            for p in valid_prods
        ]
        await conn.execute(INSERT_PROD_SQL, params)

    return len(valid_inputs), len(valid_prods)


async def run(path: Path, dry_run: bool) -> int:
    print(f"parsing {path} ...")
    inputs, prods = parse_workbook(path)
    print(f"  parsed: {len(inputs)} inputs, {len(prods)} production rows")

    engine = create_async_engine(DATABASE_URL, echo=False)
    try:
        async with engine.begin() as conn:
            anagrafica = await fetch_anagrafica(conn)
            print(
                f"  anagrafica: {len(anagrafica['supplier'])} suppliers, "
                f"{len(anagrafica['cert'])} certs, "
                f"{len(anagrafica['contract'])} contracts"
            )
            existing_in, existing_pr = await fetch_existing_keys(conn, path.name)

            v = validate(inputs, prods, anagrafica, existing_in, existing_pr)
            print_report(len(inputs), len(prods), v)

            if v["unknown_suppliers"]:
                print("\n!! BLOCKING: unknown suppliers — fix anagrafica or aliases first.")
                return 2

            if dry_run:
                print("\n[DRY-RUN] no rows inserted.")
                return 0

            n_in, n_pr = await insert_rows(conn, v["valid_inputs"], v["valid_prods"], anagrafica)
            print(f"\n[COMMIT] inserted {n_in} inputs, {n_pr} production rows.")
            return 0
    finally:
        await engine.dispose()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    if not args.path.exists():
        print(f"file not found: {args.path}", file=sys.stderr)
        return 1
    return asyncio.run(run(args.path, dry_run=args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
