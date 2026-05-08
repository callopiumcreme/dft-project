"""Parser xlsx Girardot — convert mixed-layout sheet to daily_inputs[] + daily_production[].

Layout per sheet (22 cols A-V):
  R16          : 'LOADING SUMMARY' marker — content starts after.
  Date row     : col A string 'DD MONTH YYYY' (1-2 digit day, English month, year).
                 Optional STOCK marker in cols I/J.
                 Combined form: date + aggregate fields (col K populated).
  Header row   : col A = 'TIME'.
  Transaction  : col A = datetime.time, col B = supplier name.
  TOTAL row    : col E = 'TOTAL'.
  Aggregate row: col A empty, col K populated (kg_to_production).

Sign conventions (xlsx):
  kg_to_production and byproduct kg are negative in xlsx (loss accounting).
  Stored as positive (abs) — DB schema treats as positive quantities.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from pathlib import Path

from openpyxl import load_workbook

MONTH_MAP = {
    "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4,
    "MAY": 5, "JUNE": 6, "JULY": 7, "AUGUST": 8,
    "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12,
}
DATE_RE = re.compile(r"^\s*(\d{1,2})\s+([A-Z]+)\s+(\d{4})\s*$")
SUPPLIER_ALIAS = {
    "≤5 TON": "LE5TON",
    "<=5 TON": "LE5TON",
    "<5 TON": "LE5TON",
}


@dataclass
class DailyInput:
    entry_date: date
    entry_time: time | None
    supplier_code: str
    cert_number: str | None
    contract_code: str | None
    ersv_number: str | None
    car_kg: float
    truck_kg: float
    special_kg: float
    theor_veg_pct: float | None
    manuf_veg_pct: float | None
    c14_analysis: str | None
    source_file: str
    source_row: int


@dataclass
class DailyProduction:
    prod_date: date
    kg_to_production: float | None = None
    eu_prod_kg: float | None = None
    plus_prod_kg: float | None = None
    carbon_black_kg: float | None = None
    metal_scrap_kg: float | None = None
    h2o_kg: float | None = None
    gas_syngas_kg: float | None = None
    losses_kg: float | None = None
    output_eu_kg: float | None = None
    contract_ref: str | None = None
    pos_number: str | None = None
    source_file: str = ""
    source_row: int = 0


def _parse_date(s: str) -> date | None:
    m = DATE_RE.match(s.upper())
    if not m:
        return None
    day, month_name, year = m.groups()
    month = MONTH_MAP.get(month_name)
    if not month:
        return None
    try:
        return date(int(year), month, int(day))
    except ValueError:
        return None


def _norm_supplier(name: str) -> str:
    name = name.strip()
    return SUPPLIER_ALIAS.get(name.upper(), name)


def _f(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _abs_or_none(v) -> float | None:
    f = _f(v)
    return abs(f) if f is not None else None


def _as_time(v) -> time | None:
    if isinstance(v, time):
        return v
    if isinstance(v, datetime):
        return v.time()
    return None


def parse_workbook(path: Path) -> tuple[list[DailyInput], list[DailyProduction]]:
    wb = load_workbook(path, data_only=True)
    inputs: list[DailyInput] = []
    productions: dict[date, DailyProduction] = {}

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        src = f"{path.name}#{sheet_name}"
        current_date: date | None = None
        for r in range(17, ws.max_row + 1):
            row = [ws.cell(r, c).value for c in range(1, 23)]
            if all(v is None or v == "" for v in row):
                continue

            a = row[0]
            e = row[4]
            k = row[10]

            if isinstance(a, str):
                d = _parse_date(a)
                if d:
                    current_date = d
                    if _f(k) is not None:
                        prod = productions.setdefault(
                            d, DailyProduction(prod_date=d, source_file=src, source_row=r)
                        )
                        _merge_production(prod, row, r)
                    continue
                if a.strip().upper() == "TIME":
                    continue

            if isinstance(e, str) and e.strip().upper() == "TOTAL":
                continue

            t = _as_time(a)
            if t is not None:
                if current_date is None:
                    continue
                if not row[1]:
                    continue
                inputs.append(_make_input(current_date, t, row, src, r))
                continue

            if (a is None or a == "") and _f(k) is not None and current_date is not None:
                prod = productions.setdefault(
                    current_date,
                    DailyProduction(prod_date=current_date, source_file=src, source_row=r),
                )
                _merge_production(prod, row, r)
                continue

    return inputs, list(productions.values())


def _make_input(d: date, t: time, row: list, src: str, r: int) -> DailyInput:
    return DailyInput(
        entry_date=d,
        entry_time=t,
        supplier_code=_norm_supplier(str(row[1])),
        cert_number=str(row[2]).strip() if row[2] else None,
        contract_code=str(row[3]).strip() if row[3] else None,
        ersv_number=str(row[4]).strip() if row[4] else None,
        car_kg=_f(row[5]) or 0.0,
        truck_kg=_f(row[6]) or 0.0,
        special_kg=_f(row[7]) or 0.0,
        theor_veg_pct=_f(row[8]),
        manuf_veg_pct=_f(row[9]),
        c14_analysis=str(row[13]).strip() if row[13] else None,
        source_file=src,
        source_row=r,
    )


def _merge_production(prod: DailyProduction, row: list, r: int) -> None:
    if prod.kg_to_production is None:
        prod.kg_to_production = _abs_or_none(row[10])
    if prod.eu_prod_kg is None:
        prod.eu_prod_kg = _abs_or_none(row[11])
    if prod.plus_prod_kg is None:
        prod.plus_prod_kg = _abs_or_none(row[12])
    if prod.carbon_black_kg is None:
        prod.carbon_black_kg = _abs_or_none(row[14])
    if prod.metal_scrap_kg is None:
        prod.metal_scrap_kg = _abs_or_none(row[15])
    if prod.h2o_kg is None:
        prod.h2o_kg = _abs_or_none(row[16])
    if prod.gas_syngas_kg is None:
        prod.gas_syngas_kg = _abs_or_none(row[17])
    if prod.losses_kg is None:
        prod.losses_kg = _abs_or_none(row[18])
    if prod.output_eu_kg is None:
        prod.output_eu_kg = _abs_or_none(row[19])
    if prod.contract_ref is None and row[20]:
        prod.contract_ref = str(row[20]).strip()
    if prod.pos_number is None and row[21]:
        prod.pos_number = str(row[21]).strip()


if __name__ == "__main__":
    import sys

    p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/girardot_enero_2025.xlsx")
    inputs, prods = parse_workbook(p)
    print(f"inputs:      {len(inputs)}")
    print(f"productions: {len(prods)}")
    if inputs:
        print(f"first input:  {asdict(inputs[0])}")
        print(f"last input:   {asdict(inputs[-1])}")
        dates = sorted({i.entry_date for i in inputs})
        print(f"date range:   {dates[0]} -> {dates[-1]}  ({len(dates)} unique days)")
        suppliers = sorted({i.supplier_code for i in inputs})
        print(f"suppliers:    {suppliers}")
        certs = sorted({c for c in (i.cert_number for i in inputs) if c})
        print(f"certs:        {certs}")
        contracts = sorted({c for c in (i.contract_code for i in inputs) if c})
        print(f"contracts:    {contracts}")
    if prods:
        print(f"first prod:   {asdict(prods[0])}")
        n_with_eu = sum(1 for p in prods if p.eu_prod_kg)
        print(f"prods w/ eu_prod: {n_with_eu}/{len(prods)}")
