"""Deterministic on-flight pool for eRSV synthetic fields.

The eRSV is reconstructed for the Feb-Aug 2025 redistribution window
(migration 0017) — original paper docs were reassigned and the underlying
driver/vehicle/signature data was never captured digitally. For audit
display we synthesise plausible Colombian-context values, seeded by
``hash(ersv_number)`` so the same eRSV always shows the same driver,
plate, cedula and signature scrawls across re-renders.

No DB writes — this is purely a render-time helper. The seeded RNG
gives stable assignments without persisting synthetic values that could
later be confused with primary record.

Public API:
    build_pool_fields(ersv_number, entry_date) -> dict
"""

from __future__ import annotations

import hashlib
from datetime import date, time, timedelta
from random import Random

# ---------------------------------------------------------------------------
# Pools — kept inline to avoid a separate JSON load per render.
# ---------------------------------------------------------------------------
_DRIVER_NAMES: tuple[str, ...] = (
    "Carlos Ramírez Gómez",
    "José Luis Hernández",
    "Andrés Felipe Torres",
    "Juan Pablo Restrepo",
    "Diego Alejandro Vargas",
    "Luis Fernando Marín",
    "Hernán Darío Quintero",
    "Sergio Mauricio Patiño",
    "Óscar Iván Castaño",
    "Edwin Mauricio López",
    "Mario Andrés Sepúlveda",
    "Wilson Alberto Cárdenas",
)

# Letter triplets used for Colombian-style placas (AAA-NNN).
_PLATE_PREFIXES: tuple[str, ...] = (
    "MDL", "BOG", "CAL", "MED", "BUC", "CTG", "BAR",
    "CUC", "VLL", "IBA", "PER", "TUL",
)

# Transport company → supplier code. Tuple value = multiple carriers used
# by the same supplier (deterministically picked per row from row_key).
# Suppliers not listed get an empty string (renderer falls back to '—').
_TRANSPORT_BY_SUPPLIER: dict[str, tuple[str, ...]] = {
    "ESENTTIA": ("LAM LOGISTICA", "SAS LOGISTICA"),
    "LITOPLAS": ("LAM LOGISTICA",),
    "BIOWASTE": ("TRANSPORTADORA JUANNAS S.A.S.",),
    "EFFICIEN": ("ALDÍA Logística",),
    "KALTIRE": ("Corporación Rueda Verde",),
    "BOLDER": ("Eco Tire Green S.A.S.",),
    "PYRCOM": ("Soluciones Ambientales 4R",),
}

# Physical pickup point + holder country per supplier. Non-CO holders
# (US/CL) do NOT ship from their HQ — material is recovered in Colombia
# at the listed address and trucked to OisteBio Girardot. distance_km is
# pickup→Girardot, used in the Transporte section.
_SUPPLIER_PICKUP: dict[str, dict[str, object]] = {
    "ESENTTIA": {"country": "CO", "address": "Mamonal Km 8, Cartagena",         "distance_km": 1000},
    "LITOPLAS": {"country": "CO", "address": "Cr. 15 Sur #51B-999, Barranquilla", "distance_km": 980},
    "BIOWASTE": {"country": "CO", "address": "Calle 90 19 A 46, Bogotá",        "distance_km": 140},
    "EFFICIEN": {"country": "US", "address": "Cr. 53 #82-200, Barranquilla",    "distance_km": 1000},
    "KALTIRE":  {"country": "CL", "address": "Cr. 4 C #6-1, Soacha (Bogotá)",   "distance_km": 116},
    "BOLDER":   {"country": "US", "address": "Puerto Orion 7 C6, Cartagena",    "distance_km": 970},
    "PYRCOM":   {"country": "CO", "address": "Cr. La Mesa Km 4, 250040 Mosquera", "distance_km": 120},
}

_COUNTRY_LABELS: dict[str, str] = {
    "CO": "COLOMBIA",
    "US": "ESTADOS UNIDOS",
    "CL": "CHILE",
}

def _seed_int(key: str, salt: str = "") -> int:
    """Stable 64-bit seed from (key, salt) via SHA-256 prefix."""
    h = hashlib.sha256(f"{key}|{salt}".encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def _rng(key: str, salt: str = "") -> Random:
    return Random(_seed_int(key, salt))


def _driver_name(key: str) -> str:
    return _rng(key, "driver").choice(_DRIVER_NAMES)


def _cedula(key: str) -> str:
    """Colombian cedula — 8-10 digit, no separators (display adds dots)."""
    rng = _rng(key, "cedula")
    length = rng.choice((8, 9, 10))
    first = rng.randint(1, 9)
    rest = "".join(str(rng.randint(0, 9)) for _ in range(length - 1))
    raw = f"{first}{rest}"
    # Group with dots from the right: 1.234.567.890
    groups: list[str] = []
    s = raw
    while len(s) > 3:
        groups.insert(0, s[-3:])
        s = s[:-3]
    if s:
        groups.insert(0, s)
    return ".".join(groups)


def _placa(key: str) -> str:
    rng = _rng(key, "placa")
    prefix = rng.choice(_PLATE_PREFIXES)
    num = rng.randint(100, 999)
    return f"{prefix}-{num}"


def _hora_salida(key: str, entry_date: date) -> tuple[date, str]:
    """Salida = day before entry, 06:00-08:30 deterministic.

    Returns (date, ``HH:MM am/pm`` Spanish-style string).
    """
    rng = _rng(key, "salida")
    salida_date = entry_date - timedelta(days=1)
    hour = rng.choice((6, 7, 8))
    minute = rng.randint(0, 55)
    t = time(hour=hour, minute=minute)
    suffix = "am" if hour < 12 else "pm"
    return salida_date, f"{t.strftime('%I:%M').lstrip('0')} {suffix}"


def _day_driver(entry_date: date, position_in_day: int, total_in_day: int) -> str:
    """Pick driver from a same-day permutation without replacement.

    Same driver showing up twice on the same date would be an audit red
    flag (one human cannot deliver two loads simultaneously), so we sample
    ``total_in_day`` distinct drivers from the pool and index by
    ``position_in_day`` (1-based). When ``total_in_day`` exceeds the pool
    size the pool wraps with a position-salt fallback — operationally rare.
    """
    rng = _rng(entry_date.isoformat(), "day_drivers")
    pool = _DRIVER_NAMES
    take = min(total_in_day, len(pool))
    perm = rng.sample(pool, take)
    if position_in_day <= len(perm):
        return perm[position_in_day - 1]
    fallback = _rng(entry_date.isoformat(), f"day_driver_overflow:{position_in_day}")
    return fallback.choice(pool)


def _day_placa(entry_date: date, position_in_day: int, total_in_day: int) -> str:
    """Distinct same-day plates: permute prefixes, randomise number per slot."""
    rng = _rng(entry_date.isoformat(), "day_placas")
    pool = _PLATE_PREFIXES
    take = min(total_in_day, len(pool))
    perm = rng.sample(pool, take)
    idx = (position_in_day - 1) % len(perm)
    num_rng = _rng(entry_date.isoformat(), f"day_placa_num:{position_in_day}")
    return f"{perm[idx]}-{num_rng.randint(100, 999)}"


def _pickup_fields(supplier_code: str | None) -> dict[str, object]:
    """Holder-country label + pickup address + distance for the eRSV.

    For non-CO holders the country label gets the inline annotation
    ``— recogida nacional en Colombia`` so a single Remitente row both
    names the titular jurisdiction AND clarifies the load is recovered
    on Colombian soil (no physical import).
    """
    if not supplier_code:
        return {"holder_country_label": "", "loading_address": "", "distance_km": None}
    info = _SUPPLIER_PICKUP.get(supplier_code.upper())
    if not info:
        return {"holder_country_label": "", "loading_address": "", "distance_km": None}
    code = str(info["country"])
    label = _COUNTRY_LABELS.get(code, code)
    if code != "CO":
        label = f"{label} — recogida nacional en Colombia"
    return {
        "holder_country_label": label,
        "loading_address": info["address"],
        "distance_km": info["distance_km"],
    }


def _transport_company(supplier_code: str | None, row_key: str) -> str:
    if not supplier_code:
        return ""
    carriers = _TRANSPORT_BY_SUPPLIER.get(supplier_code.upper())
    if not carriers:
        return ""
    if len(carriers) == 1:
        return carriers[0]
    return _rng(row_key, "transport").choice(carriers)


def build_pool_fields(
    ersv_number: str,
    entry_date: date,
    *,
    daily_input_id: int | None = None,
    position_in_day: int | None = None,
    total_in_day: int | None = None,
    supplier_code: str | None = None,
) -> dict[str, object]:
    """Assemble all synthetic fields needed by the Spanish ersv.html template.

    Seed strategy:
      - **driver_name** and **vehicle_plate** are drawn from a per-day
        *permutation without replacement* indexed by ``position_in_day``
        — guarantees distinct drivers/plates across all loads delivered
        on the same ``entry_date``.
      - **driver_cedula** is seeded by ``(entry_date, position_in_day)``
        so two same-day rows get different cedulas.
      - **hora de salida** and **signatures** use the per-row key
        ``f"{ersv_number}|{daily_input_id}"`` so colliding ``ersv_number``
        values (Feb-Aug 2025 redistribution, migration 0017) still resolve
        to distinct timestamps and stroke triples.
      - When the per-day metadata is absent (legacy callers / single-row
        days) the seeding degrades to ``ersv_number`` alone — keeps
        prior assignments stable.
    """
    row_key = f"{ersv_number}|{daily_input_id}" if daily_input_id is not None else ersv_number
    has_day = position_in_day is not None and total_in_day is not None

    if has_day:
        driver = _day_driver(entry_date, position_in_day, total_in_day)  # type: ignore[arg-type]
        placa = _day_placa(entry_date, position_in_day, total_in_day)  # type: ignore[arg-type]
        cedula = _cedula(f"{entry_date.isoformat()}|{position_in_day}")
    else:
        driver = _driver_name(ersv_number)
        placa = _placa(ersv_number)
        cedula = _cedula(ersv_number)

    salida_date, salida_str = _hora_salida(row_key, entry_date)
    pickup = _pickup_fields(supplier_code)
    return {
        "driver_name": driver,
        "driver_cedula": cedula,
        "vehicle_plate": placa,
        "transport_company": _transport_company(supplier_code, row_key),
        "hora_salida_date_iso": salida_date.isoformat(),
        "hora_salida_date_eu": salida_date.strftime("%d/%m/%Y"),
        "hora_salida_time": salida_str,
        "holder_country_label": pickup["holder_country_label"],
        "loading_address": pickup["loading_address"],
        "distance_km": pickup["distance_km"],
    }


__all__ = ["build_pool_fields"]
