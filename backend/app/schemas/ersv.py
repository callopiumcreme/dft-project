"""Pydantic schemas for the eRSV (electronic Receipt of Material) artefact.

The eRSV is a per-supply-event document re-rendered on demand from
``daily_inputs`` for the Feb-Aug 2025 non-LE5TON window (post-migration
0017) and the Jan 2025 frozen numbering space.

``ErsvDetail`` is the JSON shape returned by ``GET /ersv/{ersv_number}``.
The PDF and HTML routes return raw artefacts (``application/pdf`` /
``text/html``) — those responses are NOT modelled here.
"""

from __future__ import annotations

# Pydantic v2 requires these symbols at runtime to build the model.
from datetime import date, datetime, time  # noqa: TC003
from decimal import Decimal  # noqa: TC003

from pydantic import BaseModel, ConfigDict


class ErsvDetail(BaseModel):
    """JSON metadata for a single eRSV — drives UI badges and detail pane."""

    model_config = ConfigDict(from_attributes=True)

    ersv_number: str
    daily_input_id: int
    entry_date: date
    entry_time: time | None
    supplier_id: int
    supplier_code: str
    supplier_name: str
    total_input_kg: Decimal
    car_kg: Decimal
    truck_kg: Decimal
    special_kg: Decimal
    cert_iscc_ref: str | None
    is_regenerated: bool
    rectified_at: datetime | None
    rectification_reason: str | None
    updated_at: datetime
