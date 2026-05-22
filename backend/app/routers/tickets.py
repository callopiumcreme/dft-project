"""Báscula (weighbridge) ticket read-only API.

Two routes, both viewer+ JWT-gated:

- ``GET /tickets/{daily_input_id}`` → JSON metadata + preview text (no audit).
- ``GET /tickets/{daily_input_id}/escpos`` → raw ESC/POS byte stream for an
  80mm thermal printer, with an ``audit_log`` row inserted on every export.

The ticket is re-rendered on demand from a single ``daily_inputs`` row;
driver / plate / transport mirror that delivery's eRSV via the shared
``build_pool_fields`` pool.

Audit policy mirrors ``ersv.py``: only the byte-export route writes to
``audit_log``, using ``action='insert'`` (the CHECK constraint forbids
``export``; ``insert`` is the canonical "create this artefact" action). The
``table_name`` column is free-form Text (only ``action`` is constrained), so
we use ``table_name='ticket'``.

The ``/escpos`` route sets ``Cache-Control: no-store`` because every render
is audited and the artefact must not be served from a shared cache.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ViewerUser  # noqa: TC001 — Annotated dep used at runtime
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.schemas.ticket import TicketDetail
from app.services.ticket_renderer import (
    TicketNotFoundError,
    build_ticket_data,
    fetch_ticket_row,
    render_ticket_preview_text,
    render_ticket_to_escpos,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# JSON metadata + preview (no audit)
# ---------------------------------------------------------------------------
@router.get("/{daily_input_id}", response_model=TicketDetail)
async def get_ticket(
    daily_input_id: int,
    _: ViewerUser,
    db: DbDep,
) -> TicketDetail:
    """Return JSON metadata + 48-col preview text for a single ticket."""
    try:
        row = await fetch_ticket_row(db, daily_input_id)
    except TicketNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket not found for daily_input_id={daily_input_id}",
        ) from exc

    data = build_ticket_data(row, int(row["position_in_day"]), int(row["total_in_day"]))
    preview = render_ticket_preview_text(data)
    return TicketDetail(preview_text=preview, **data)


# ---------------------------------------------------------------------------
# ESC/POS byte stream (audited, no-store)
# ---------------------------------------------------------------------------
@router.get("/{daily_input_id}/escpos")
async def get_ticket_escpos(
    daily_input_id: int,
    user: ViewerUser,
    db: DbDep,
) -> Response:
    """Return a raw ESC/POS byte stream; insert an audit_log row on success."""
    try:
        row = await fetch_ticket_row(db, daily_input_id)
    except TicketNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket not found for daily_input_id={daily_input_id}",
        ) from exc

    data = build_ticket_data(row, int(row["position_in_day"]), int(row["total_in_day"]))
    payload = render_ticket_to_escpos(data)

    audit = AuditLog(
        table_name="ticket",
        record_id=data["daily_input_id"],
        action="insert",
        old_values=None,
        new_values={
            "kind": "TICKET_ESCPOS_EXPORT",
            "ersv_number": data["ersv_number"],
            "ticket_num": data["ticket_num"],
            "size_bytes": len(payload),
        },
        changed_by=user.id,
    )
    db.add(audit)
    await db.commit()

    filename = f"ticket_{data['daily_input_id']}.escpos"
    return Response(
        content=payload,
        media_type="application/octet-stream",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
