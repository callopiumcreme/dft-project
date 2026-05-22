"""Pydantic schemas for the báscula (weighbridge) ticket artefact.

The ticket is a per-delivery weighbridge slip re-rendered on demand from a
single ``daily_inputs`` row. It mirrors the eRSV in that driver / plate /
transport company are pulled from the SAME deterministic source
(``app.services.ersv_pool.build_pool_fields``) so the conductor named on the
báscula ticket matches the conductor named on that delivery's eRSV exactly.

``TicketDetail`` is the JSON shape returned by
``GET /tickets/{daily_input_id}``. The ESC/POS route returns raw bytes
(``application/octet-stream``) and is NOT modelled here.
"""

from __future__ import annotations

# Pydantic v2 requires these symbols at runtime to build the model.
from datetime import date  # noqa: TC003
from decimal import Decimal  # noqa: TC003

from pydantic import BaseModel, ConfigDict


class TicketDetail(BaseModel):
    """JSON metadata for a single báscula ticket — drives the print preview."""

    model_config = ConfigDict(from_attributes=True)

    daily_input_id: int
    ersv_number: str | None
    entry_date: date
    supplier_code: str
    supplier_name: str
    prod: str
    total_input_kg: Decimal
    driver_name: str
    driver_cedula: str
    vehicle_plate: str
    transport_company: str
    hora_ent: str
    hora_sal: str
    peso_ent_kg: Decimal
    peso_sal_kg: Decimal
    peso_neto_kg: Decimal
    ticket_num: int
    weigher: str
    preview_text: str
