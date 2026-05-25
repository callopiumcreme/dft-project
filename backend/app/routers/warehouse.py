"""Router: warehouse stock + ledger-derived movements.

Reads only — operator/admin writes flow through /byproduct (sales),
/consignments (dispatch) and the daily-production ingest that backfills
mass_balance_ledger.

Auth: viewer+ for all endpoints.
Data sources:
  - v_warehouse_stock (per product_kind on-hand + cumulative totals)
  - mass_balance_ledger (active rows only) for the movements feed
  - consignment.total_kg for the eu_oil reserved_kg overlay
"""
from __future__ import annotations

from decimal import Decimal
from typing import Annotated, get_args

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import extract, func, select
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ViewerUser  # noqa: TC001 — Annotated dep used at runtime
from app.db.session import get_db
from app.models.consignment_pos import ConsignmentPos
from app.schemas.warehouse import ProductKind, WarehouseMovement, WarehouseStockRow

router = APIRouter(prefix="/warehouse", tags=["warehouse"])
DbDep = Annotated[AsyncSession, Depends(get_db)]

_PRODUCT_KINDS = frozenset(get_args(ProductKind))
_PRODUCT_KIND_ERROR = (
    "product_kind must be one of: "
    "eu_oil, plus_oil, carbon_black, metal_scrap, syngas, h2o"
)


@router.get("/stock", response_model=list[WarehouseStockRow])
async def list_warehouse_stock(
    _: ViewerUser,
    db: DbDep,
    product_kind: str | None = Query(None),
) -> list[WarehouseStockRow]:
    """Per-product on-hand + cumulative totals, plus reserved_kg for eu_oil.

    reserved_kg = SUM(consignment.total_kg) for active consignments whose
    status is not in ('delivered_uk', 'closed'). Only meaningful for eu_oil;
    every other product_kind reports 0.

    When ``product_kind`` is supplied it must be one of the six allowed
    values (see ``ProductKind``); the result is filtered to that single
    product (possibly an empty list if the view has no row yet).
    """
    if product_kind is not None and product_kind not in _PRODUCT_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_PRODUCT_KIND_ERROR,
        )

    sql = (
        "SELECT product_kind, stock_kg, produced_total_kg, "
        "dispatched_total_kg, produced_ytd_kg, opening_balance_kg, "
        "last_movement_at "
        "FROM v_warehouse_stock"
    )
    params: dict[str, object] = {}
    if product_kind is not None:
        sql += " WHERE product_kind = :product_kind"
        params["product_kind"] = product_kind

    stock_rows = (
        await db.execute(sa_text(sql), params)
    ).mappings().all()

    reserved_result = await db.execute(
        sa_text(
            "SELECT COALESCE(SUM(total_kg), 0) AS reserved_kg "
            "FROM consignment "
            "WHERE status NOT IN ('delivered_uk', 'closed') "
            "AND deleted_at IS NULL"
        )
    )
    reserved_eu_oil = Decimal(reserved_result.scalar_one() or 0)

    pos_issued_result = await db.execute(
        sa_text(
            "SELECT COALESCE(SUM(kg_net), 0) AS pos_issued_kg "
            "FROM consignment_pos "
            "WHERE deleted_at IS NULL"
        )
    )
    pos_issued_eu_oil = Decimal(pos_issued_result.scalar_one() or 0)

    # ORM query (post DFTEN-172): issuance_date is now a Mapped attribute,
    # so no raw SQL workaround is needed. Cast EXTRACT result to int via
    # SQLAlchemy.cast equivalent — using label + manual int conversion in
    # the comprehension keeps the type contract identical to the prior
    # ``::int`` cast.
    year_col = extract("year", ConsignmentPos.issuance_date).label("yr")
    kg_col = func.coalesce(func.sum(ConsignmentPos.kg_net), 0).label("kg")
    pos_issued_by_year_rows = (
        await db.execute(
            select(year_col, kg_col)
            .where(
                ConsignmentPos.deleted_at.is_(None),
                ConsignmentPos.issuance_date.is_not(None),
            )
            .group_by(year_col)
            .order_by(year_col)
        )
    ).mappings().all()
    pos_issued_by_year_eu_oil: dict[str, Decimal] = {
        str(int(r["yr"])): Decimal(r["kg"] or 0) for r in pos_issued_by_year_rows
    }

    at_utb_result = await db.execute(
        sa_text(
            "SELECT COALESCE(SUM(c.total_kg), 0) "
            "- COALESCE(SUM(p_open.kg_net_sum), 0) AS at_utb_kg "
            "FROM consignment c "
            "LEFT JOIN ("
            "  SELECT consignment_id, SUM(kg_net) AS kg_net_sum "
            "  FROM consignment_pos WHERE deleted_at IS NULL "
            "  GROUP BY consignment_id"
            ") p_open ON p_open.consignment_id = c.id "
            "WHERE c.status NOT IN ('delivered_uk', 'closed') "
            "AND c.deleted_at IS NULL"
        )
    )
    at_utb_awaiting_pos_eu_oil = Decimal(at_utb_result.scalar_one() or 0)

    return [
        WarehouseStockRow(
            product_kind=row["product_kind"],
            stock_kg=row["stock_kg"] or Decimal(0),
            produced_total_kg=row["produced_total_kg"] or Decimal(0),
            dispatched_total_kg=row["dispatched_total_kg"] or Decimal(0),
            produced_ytd_kg=row["produced_ytd_kg"] or Decimal(0),
            opening_balance_kg=row["opening_balance_kg"] or Decimal(0),
            reserved_kg=(
                reserved_eu_oil if row["product_kind"] == "eu_oil" else Decimal(0)
            ),
            pos_issued_kg=(
                pos_issued_eu_oil if row["product_kind"] == "eu_oil" else Decimal(0)
            ),
            pos_issued_by_year=(
                pos_issued_by_year_eu_oil
                if row["product_kind"] == "eu_oil"
                else {}
            ),
            at_utb_awaiting_pos_kg=(
                at_utb_awaiting_pos_eu_oil
                if row["product_kind"] == "eu_oil"
                else Decimal(0)
            ),
            last_movement_at=row["last_movement_at"],
        )
        for row in stock_rows
    ]


@router.get("/movements", response_model=list[WarehouseMovement])
async def list_warehouse_movements(
    _: ViewerUser,
    db: DbDep,
    limit: int = Query(100, ge=1, le=1000),
    product_kind: ProductKind | None = Query(None),  # noqa: B008 — FastAPI Query idiom
    event_type: str | None = Query(None),
) -> list[WarehouseMovement]:
    """Recent ledger movements (active rows only).

    Ordered by event_date DESC, id DESC. kg_in / kg_out NULLs in the ledger
    surface as 0 in the response so the frontend can render symmetric
    in/out columns without null-guards.
    """
    sql = (
        "SELECT id, event_date, event_type, product_kind, "
        "COALESCE(kg_in, 0) AS kg_in, COALESCE(kg_out, 0) AS kg_out, "
        "post_balance_kg, ref_doc_no, consignment_id, notes "
        "FROM mass_balance_ledger "
        "WHERE deleted_at IS NULL"
    )
    params: dict[str, object] = {"limit": limit}
    if product_kind is not None:
        sql += " AND product_kind = :product_kind"
        params["product_kind"] = product_kind
    if event_type is not None:
        sql += " AND event_type = :event_type"
        params["event_type"] = event_type
    sql += " ORDER BY event_date DESC, id DESC LIMIT :limit"

    rows = (await db.execute(sa_text(sql), params)).mappings().all()
    return [WarehouseMovement(**dict(r)) for r in rows]
