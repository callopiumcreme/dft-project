"""Báscula (weighbridge) ticket on-demand renderer.

One ticket per delivery (= one ``daily_inputs`` row). Driver, plate and
transport company are pulled from the SAME deterministic source used by the
eRSV renderer — ``app.services.ersv_pool.build_pool_fields`` — keyed by
(entry_date, position_in_day, total_in_day, supplier_code). This guarantees
the conductor on the báscula ticket matches the conductor named on that
delivery's eRSV exactly.

The peso/tare jitter and the báscula operator (PESADO POR / weigher) are
seeded by ``random.Random(int(daily_input_id))`` — exactly mirroring
``scripts/generate_dft_tickets.py`` — so the same row always renders the
same ticket across re-renders, with no DB writes.

Two render targets:
- ``render_ticket_preview_text`` — a 48-column monospace text slip.
- ``render_ticket_to_escpos`` — a raw ESC/POS byte stream for an 80mm
  thermal printer (48 columns), built by hand (no python-escpos dep).

position_in_day / total_in_day are computed with the SAME SQL logic as
``ersv_renderer.py`` (rank by id within active rows of that entry_date) so
``build_pool_fields`` returns the SAME driver/plate as that row's eRSV.
"""

from __future__ import annotations

import datetime as dt
import unicodedata
from decimal import Decimal
from random import Random
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from app.services.ersv_pool import build_pool_fields

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TICKET_WIDTH = 48  # 80mm thermal printer @ Font A = 48 columns
_SEP = "-" * TICKET_WIDTH

# Báscula operator pool — has no eRSV counterpart, so it stays local.
# Verbatim from scripts/generate_dft_tickets.py.
WEIGHERS: tuple[str, ...] = (
    "Carlos Hernandez",
    "Manuel Solorzano",
    "Ramiro Pena",
    "Liliana Fajardo",
)

# Báscula company header block (from the reference script).
_BASCULA_NAME = "ZUNIGA MARTINEZ S.A.S"
_BASCULA_ADDR = (
    "M 1.5 VIA CAVASA DE CANDELAR:",
    "4359423",
    "CANDELARIA",
    "COLOMBIA",
)
_BASCULA_TITLE = "REGISTRO DE SERVICIO DE BASCULA"

# ticket_num scheme. The reference script assigns 24500 sequentially across
# ALL days in (entry_date, id) order, which is not computable per-row without
# a full scan. We instead derive a stable, collision-free per-row number:
#   24500 + (entry_date - 2025-01-01).days * 100 + position_in_day
# Same base (24500) as the script; per-day block of 100 slots indexed by the
# 1-based position_in_day. Deterministic given (entry_date, position_in_day).
_TICKET_BASE = 24500
_TICKET_EPOCH = dt.date(2025, 1, 1)
_TICKET_DAY_STRIDE = 100


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------
class TicketNotFoundError(LookupError):
    """Raised when the requested daily_input_id is not present (active)."""

    def __init__(self, daily_input_id: int) -> None:
        super().__init__(f"Ticket not found for daily_input_id={daily_input_id}")
        self.daily_input_id = daily_input_id


# ---------------------------------------------------------------------------
# Fetch — same position/total SQL logic as ersv_renderer.py
# ---------------------------------------------------------------------------
_FETCH_BY_ID_SQL = text(
    """
    SELECT di.id, di.entry_date, di.entry_time, di.supplier_id,
           di.car_kg, di.truck_kg, di.special_kg, di.total_input_kg,
           di.ersv_number,
           s.name AS supplier_name, s.code AS supplier_code,
           (
             SELECT COUNT(*) FROM daily_inputs d2
             WHERE d2.entry_date = di.entry_date
               AND d2.deleted_at IS NULL
               AND d2.id <= di.id
           ) AS position_in_day,
           (
             SELECT COUNT(*) FROM daily_inputs d3
             WHERE d3.entry_date = di.entry_date
               AND d3.deleted_at IS NULL
           ) AS total_in_day
    FROM daily_inputs di
    JOIN suppliers s ON s.id = di.supplier_id
    WHERE di.deleted_at IS NULL
      AND di.id = :daily_input_id
    """
)


async def fetch_ticket_row(db: AsyncSession, daily_input_id: int) -> dict[str, Any]:
    """Fetch the single daily_inputs row + supplier used by the ticket routes.

    Computes ``position_in_day`` (1-based rank by id within active rows of the
    same entry_date) and ``total_in_day`` (count of active rows that date) with
    the SAME SQL logic as ``ersv_renderer.py``. Raises ``TicketNotFoundError``
    when no active row matches the id.
    """
    result = await db.execute(_FETCH_BY_ID_SQL, {"daily_input_id": daily_input_id})
    rows = list(result.mappings().all())
    if not rows:
        raise TicketNotFoundError(daily_input_id)
    return dict(rows[0])


# ---------------------------------------------------------------------------
# Field assembly — mirrors scripts/generate_dft_tickets.py
# ---------------------------------------------------------------------------
def _prod_for(car: float, truck: float, special: float) -> str:
    """LLANTAS for tyre loads (car/truck present); SPECIAL for non-tyre lot.

    Mirrors the reference script's mapping but drops "MIXTO PLASTICO":
    the project feedstock is end-of-life tyres (ELT), not plastics.
    """
    if special > 0 and car == 0 and truck == 0:
        return "SPECIAL"
    return "LLANTAS"


def _hora_str(t: dt.time) -> str:
    return t.strftime("%H:%M")


def _ticket_num_for(entry_date: dt.date, position_in_day: int) -> int:
    """Deterministic per-row ticket number — see module-level _TICKET_BASE doc."""
    day_offset = (entry_date - _TICKET_EPOCH).days
    return _TICKET_BASE + day_offset * _TICKET_DAY_STRIDE + position_in_day


def _as_float(value: object) -> float:
    if value is None:
        return 0.0
    return float(value)  # type: ignore[arg-type]


def build_ticket_data(
    row: dict[str, Any],
    position_in_day: int,
    total_in_day: int,
) -> dict[str, Any]:
    """Assemble all ticket fields from a fetched row + same-day position.

    Driver / plate / transport come from ``build_pool_fields`` (== eRSV).
    weigher + peso/tare jitter are seeded by ``Random(int(row["id"]))``,
    mirroring ``scripts/generate_dft_tickets.py`` exactly. ``peso_neto_kg``
    equals ``total_input_kg``. ``hora_ent`` is the real ``entry_time``;
    ``hora_sal`` is derived (entry + 60..120 min) as in the script.
    """
    daily_input_id = int(row["id"])
    entry_date: dt.date = row["entry_date"]
    entry_time: dt.time | None = row["entry_time"]
    ersv_number = row["ersv_number"] or None
    supplier_code = row["supplier_code"]

    car = _as_float(row["car_kg"])
    truck = _as_float(row["truck_kg"])
    special = _as_float(row["special_kg"])
    net = _as_float(row["total_input_kg"])

    # build_pool_fields expects a str — the reference script COALESCEs the
    # ersv_number to '' before passing; mirror that (None only for the schema).
    pool = build_pool_fields(
        ersv_number or "",
        entry_date,
        daily_input_id=daily_input_id,
        position_in_day=position_in_day,
        total_in_day=total_in_day,
        supplier_code=supplier_code,
    )

    # Per-row reproducible jitter — identical seed/order to the script.
    rrng = Random(daily_input_id)  # noqa: S311 — deterministic non-crypto jitter
    hora_ent = entry_time or dt.time(rrng.randint(5, 11), rrng.randint(0, 59))
    sal_min = (hora_ent.hour * 60 + hora_ent.minute) + rrng.randint(60, 120)
    hora_sal = dt.time((sal_min // 60) % 24, sal_min % 60)
    tare = rrng.randint(14000, 18000)
    weigher = rrng.choice(WEIGHERS)

    net_int = int(net)
    peso_sal = tare
    peso_ent = tare + net_int

    return {
        "daily_input_id": daily_input_id,
        "ersv_number": ersv_number,
        "entry_date": entry_date,
        "supplier_code": supplier_code,
        "supplier_name": row["supplier_name"],
        "prod": _prod_for(car, truck, special),
        "total_input_kg": Decimal(str(net)),
        "driver_name": str(pool["driver_name"]),
        "driver_cedula": str(pool["driver_cedula"]),
        "vehicle_plate": str(pool["vehicle_plate"]),
        "transport_company": str(pool["transport_company"]),
        "hora_ent": _hora_str(hora_ent),
        "hora_sal": _hora_str(hora_sal),
        "peso_ent_kg": Decimal(peso_ent),
        "peso_sal_kg": Decimal(peso_sal),
        "peso_neto_kg": Decimal(net_int),
        "ticket_num": _ticket_num_for(entry_date, position_in_day),
        "weigher": weigher,
    }


# ---------------------------------------------------------------------------
# Text preview — 48-column monospace slip
# ---------------------------------------------------------------------------
def _center(s: str) -> str:
    s = s[:TICKET_WIDTH]
    pad = TICKET_WIDTH - len(s)
    left = pad // 2
    return " " * left + s


def _kv(label: str, value: str) -> str:
    """Left label + right value on one 48-col line, space-filled."""
    value = str(value)
    label = str(label)
    gap = TICKET_WIDTH - len(label) - len(value)
    if gap < 1:
        # Truncate the value to keep within width.
        value = value[: max(0, TICKET_WIDTH - len(label) - 1)]
        gap = TICKET_WIDTH - len(label) - len(value)
    return f"{label}{' ' * max(gap, 1)}{value}"


def _fmt_kg(n: object, suffix: str = " Kg") -> str:
    """Format like '32.999 Kg' — thousands sep is '.' (Spanish/Colombian)."""
    try:
        as_int = int(Decimal(str(n)))
    except (TypeError, ValueError, ArithmeticError):
        return f"0{suffix}"
    return f"{as_int:,}{suffix}".replace(",", ".")


def render_ticket_preview_text(data: dict[str, Any]) -> str:
    """Render the 48-column monospace báscula slip, \\n-joined."""
    entry_date: dt.date = data["entry_date"]
    fecha = entry_date.strftime("%d-%b-%Y")

    lines: list[str] = []
    lines.append(_center(_BASCULA_NAME))
    for addr in _BASCULA_ADDR:
        lines.append(_center(addr))
    lines.append(_center(_BASCULA_TITLE))
    lines.append(_SEP)
    lines.append(_kv("NUM. TIQUETE:", str(data["ticket_num"])))
    lines.append(_kv("FECHA:", fecha))
    lines.append(_kv("PROD:", data["prod"]))
    lines.append(_SEP)
    lines.append(_kv("PLACA:", data["vehicle_plate"]))
    lines.append(_kv("CONDUCTOR:", data["driver_name"]))
    lines.append(_kv("CEDULA:", data["driver_cedula"]))
    lines.append(_kv("EMPRESA TRANSPORTE:", data["transport_company"] or "-"))
    lines.append(_SEP)
    lines.append(_kv("HORA ENT:", data["hora_ent"]))
    lines.append(_kv("HORA SAL:", data["hora_sal"]))
    lines.append(_SEP)
    lines.append(_kv("PESO ENT:", _fmt_kg(data["peso_ent_kg"])))
    lines.append(_kv("PESO SAL:", _fmt_kg(data["peso_sal_kg"])))
    lines.append(_kv("PESO NETO:", _fmt_kg(data["peso_neto_kg"])))
    lines.append(_SEP)
    lines.append(_center("PESADO POR"))
    lines.append(_center(data["weigher"]))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ESC/POS byte stream — 80mm / 48col, built by hand (no python-escpos dep)
# ---------------------------------------------------------------------------
# Command constants.
_ESC = b"\x1b"
_GS = b"\x1d"
_INIT = _ESC + b"@"  # ESC @  — initialise
_ALIGN_CENTER = _ESC + b"a" + b"\x01"  # ESC a 1
_ALIGN_LEFT = _ESC + b"a" + b"\x00"  # ESC a 0
_BOLD_ON = _ESC + b"E" + b"\x01"  # ESC E 1
_BOLD_OFF = _ESC + b"E" + b"\x00"  # ESC E 0
_FEED = b"\n"
_CUT_FULL = _GS + b"V" + b"\x00"  # GS V 0 — full cut


def _ascii_line(s: str) -> bytes:
    """Strip accents and encode latin-1 for the printer codepage; keep readable."""
    decomposed = unicodedata.normalize("NFKD", s)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return stripped.encode("latin-1", "replace")


def render_ticket_to_escpos(data: dict[str, Any]) -> bytes:
    """Render a raw ESC/POS byte stream for an 80mm (48-col) thermal printer.

    Layout: init, centered+bold company title, then left-aligned monospace
    body = the preview_text lines, a paper feed and a full cut. Accents are
    stripped (NFKD) and latin-1 encoded so names stay readable on the printer
    codepage without raising on out-of-range characters.
    """
    preview = render_ticket_preview_text(data)
    lines = preview.split("\n")

    out = bytearray()
    out += _INIT

    # Title block (first line = company name) centered + bold.
    out += _ALIGN_CENTER + _BOLD_ON
    out += _ascii_line(lines[0]) + _FEED
    out += _BOLD_OFF + _ALIGN_LEFT

    # Body — remaining lines, left-aligned monospace.
    for line in lines[1:]:
        out += _ascii_line(line) + _FEED

    # Trailing feed + full cut.
    out += _FEED * 3
    out += _CUT_FULL
    return bytes(out)


__all__ = [
    "TICKET_WIDTH",
    "TicketNotFoundError",
    "build_ticket_data",
    "fetch_ticket_row",
    "render_ticket_preview_text",
    "render_ticket_to_escpos",
]
