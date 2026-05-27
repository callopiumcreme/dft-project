"""Router: byproduct_buyer + byproduct_sale (Plus-oil / carbon black / metal scrap).

A byproduct sale is the system-of-record for one invoice covering a non-EU-oil
output of the Girardot plant. Each POST /byproduct/sales also writes a
companion row into mass_balance_ledger so the warehouse view stays consistent:

  event_type='byproduct_sale', kg_out=sale.kg_net, kg_in=0,
  product_kind=sale.product_kind, ref_table='byproduct_sale', ref_id=sale.id,
  ref_doc_no=sale.invoice_no, event_date=sale.sale_date,
  post_balance_kg = running balance for that product_kind after this row.

DELETE soft-deletes the sale AND writes a reversal ledger row
(event_type='correction', kg_in=original.kg_net, corrects_id=original ledger id).

Auth: viewer+ for reads; operator+ for sale POST/DELETE; admin for buyer DELETE.
Tables / FKs / CHECKs live in alembic 0026_warehouse_inventory.
"""
from __future__ import annotations

import os
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import text as sa_text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (  # noqa: TC001 — Annotated deps used at runtime
    AdminUser,
    OperatorUser,
    ViewerUser,
)
from app.db.session import get_db
from app.schemas.warehouse import (
    ByproductBuyerIn,
    ByproductBuyerOut,
    ByproductBuyerUpdate,
    ByproductSaleIn,
    ByproductSaleOut,
    ProductKind,
    SellableKind,
)

router = APIRouter(prefix="/byproduct", tags=["byproduct"])
DbDep = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# Buyers
# ---------------------------------------------------------------------------


@router.get("/buyers", response_model=list[ByproductBuyerOut])
async def list_buyers(
    _: ViewerUser,
    db: DbDep,
) -> list[ByproductBuyerOut]:
    """List active (non-soft-deleted) byproduct buyers, ordered by name."""
    rows = (
        await db.execute(
            sa_text(
                "SELECT id, name, country, vat, contact, notes, created_at "
                "FROM byproduct_buyer "
                "WHERE deleted_at IS NULL "
                "ORDER BY name"
            )
        )
    ).mappings().all()
    return [ByproductBuyerOut(**dict(r)) for r in rows]


@router.post(
    "/buyers",
    response_model=ByproductBuyerOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_buyer(
    body: ByproductBuyerIn,
    _: OperatorUser,
    db: DbDep,
) -> ByproductBuyerOut:
    """Create a new byproduct buyer. 409 if active name already exists."""
    try:
        result = await db.execute(
            sa_text(
                "INSERT INTO byproduct_buyer (name, country, vat, contact, notes) "
                "VALUES (:name, :country, :vat, :contact, :notes) "
                "RETURNING id, name, country, vat, contact, notes, created_at"
            ),
            body.model_dump(),
        )
        row = result.mappings().one()
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Buyer with this name already exists",
        ) from exc
    return ByproductBuyerOut(**dict(row))


@router.get("/buyers/{buyer_id}", response_model=ByproductBuyerOut)
async def get_buyer(
    buyer_id: int,
    _: ViewerUser,
    db: DbDep,
) -> ByproductBuyerOut:
    """Fetch one active byproduct buyer by id. 404 if absent or soft-deleted."""
    row = (
        await db.execute(
            sa_text(
                "SELECT id, name, country, vat, contact, notes, created_at "
                "FROM byproduct_buyer "
                "WHERE id = :id AND deleted_at IS NULL"
            ),
            {"id": buyer_id},
        )
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Buyer not found"
        )
    return ByproductBuyerOut(**dict(row))


@router.patch("/buyers/{buyer_id}", response_model=ByproductBuyerOut)
async def update_buyer(
    buyer_id: int,
    body: ByproductBuyerUpdate,
    _: OperatorUser,
    db: DbDep,
) -> ByproductBuyerOut:
    """Partial-update an active buyer. 404 if absent; 409 on name conflict.

    Only fields explicitly supplied in the request body are written
    (Pydantic v2 ``model_dump(exclude_unset=True)``). Empty body = no-op
    UPDATE that still returns the current row so the client can refresh.
    """
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        # No-op: just re-read the row so the client gets the latest state.
        return await get_buyer(buyer_id, _, db)

    set_clause = ", ".join(f"{k} = :{k}" for k in patch)
    params: dict[str, object] = {**patch, "id": buyer_id}
    try:
        row = (
            await db.execute(
                sa_text(
                    f"UPDATE byproduct_buyer SET {set_clause} "  # noqa: S608 — keys come from a fixed Pydantic schema
                    "WHERE id = :id AND deleted_at IS NULL "
                    "RETURNING id, name, country, vat, contact, notes, created_at"
                ),
                params,
            )
        ).mappings().one_or_none()
        if row is None:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Buyer not found"
            )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Buyer with this name already exists",
        ) from exc
    return ByproductBuyerOut(**dict(row))


@router.delete("/buyers/{buyer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_buyer(
    buyer_id: int,
    _: AdminUser,
    db: DbDep,
) -> None:
    """Soft-delete a buyer (deleted_at = NOW). Admin only.

    Existing byproduct_sale rows referencing this buyer remain intact — the
    FK is RESTRICT-on-delete at the SQL layer and the soft-delete only flips
    a flag, so historical sales keep resolving the buyer_name via the JOIN.
    """
    result = await db.execute(
        sa_text(
            "UPDATE byproduct_buyer "
            "SET deleted_at = NOW() "
            "WHERE id = :id AND deleted_at IS NULL "
            "RETURNING id"
        ),
        {"id": buyer_id},
    )
    if result.scalar_one_or_none() is None:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Buyer not found"
        )
    await db.commit()


# ---------------------------------------------------------------------------
# Sales
# ---------------------------------------------------------------------------


@router.get("/sales", response_model=list[ByproductSaleOut])
async def list_sales(
    _: ViewerUser,
    db: DbDep,
    product_kind: SellableKind | None = Query(None),  # noqa: B008 — FastAPI Query idiom
    buyer_id: int | None = Query(None),
    from_date: date | None = Query(None),  # noqa: B008 — FastAPI Query idiom
    to_date: date | None = Query(None),  # noqa: B008 — FastAPI Query idiom
) -> list[ByproductSaleOut]:
    """List active byproduct sales with buyer_name JOINed in.

    Ordered by sale_date DESC, id DESC.
    """
    sql = (
        "SELECT s.id, s.product_kind, s.buyer_id, s.sale_date, s.kg_net, "
        "s.invoice_no, s.price_eur, s.price_amount, s.currency, s.pricing_method, "
        "(s.pdf_ref IS NOT NULL) AS has_pdf, "
        "s.notes, s.created_at, b.name AS buyer_name "
        "FROM byproduct_sale s "
        "LEFT JOIN byproduct_buyer b ON b.id = s.buyer_id "
        "WHERE s.deleted_at IS NULL"
    )
    params: dict[str, object] = {}
    if product_kind is not None:
        sql += " AND s.product_kind = :product_kind"
        params["product_kind"] = product_kind
    if buyer_id is not None:
        sql += " AND s.buyer_id = :buyer_id"
        params["buyer_id"] = buyer_id
    if from_date is not None:
        sql += " AND s.sale_date >= :from_date"
        params["from_date"] = from_date
    if to_date is not None:
        sql += " AND s.sale_date <= :to_date"
        params["to_date"] = to_date
    sql += " ORDER BY s.sale_date DESC, s.id DESC"

    rows = (await db.execute(sa_text(sql), params)).mappings().all()
    return [ByproductSaleOut(**dict(r)) for r in rows]


async def _compute_post_balance(
    db: AsyncSession,
    product_kind: ProductKind,
    delta: Decimal,
) -> Decimal:
    """Return the new running balance for ``product_kind`` after applying ``delta``.

    ``delta`` is signed: positive = kg_in net, negative = kg_out net. The
    previous running balance is taken from v_warehouse_stock (which already
    excludes soft-deleted ledger rows).
    """
    result = await db.execute(
        sa_text(
            "SELECT COALESCE(stock_kg, 0) AS stock_kg "
            "FROM v_warehouse_stock "
            "WHERE product_kind = :product_kind"
        ),
        {"product_kind": product_kind},
    )
    prev = Decimal(result.scalar_one_or_none() or 0)
    return prev + delta


@router.post(
    "/sales",
    response_model=ByproductSaleOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_sale(
    body: ByproductSaleIn,
    user: OperatorUser,
    db: DbDep,
) -> ByproductSaleOut:
    """Create a byproduct sale + companion mass_balance_ledger event_type='byproduct_sale'.

    Atomic: both INSERTs run inside ``async with db.begin()``. On any failure
    (FK violation, check constraint, network drop after the first INSERT) the
    surrounding context manager rolls back BOTH writes, so the sale row can
    never survive without its ledger entry. FK violations on buyer_id surface
    as 409.
    """
    try:
        async with db.begin():
            sale_result = await db.execute(
                sa_text(
                    "INSERT INTO byproduct_sale ("
                    "  product_kind, buyer_id, sale_date, kg_net, invoice_no, "
                    "  price_eur, notes"
                    ") VALUES ("
                    "  :product_kind, :buyer_id, :sale_date, :kg_net, :invoice_no, "
                    "  :price_eur, :notes"
                    ") RETURNING id, product_kind, buyer_id, sale_date, kg_net, "
                    "  invoice_no, price_eur, notes, created_at"
                ),
                body.model_dump(),
            )
            sale_row = sale_result.mappings().one()

            post_balance = await _compute_post_balance(
                db, body.product_kind, -body.kg_net
            )

            await db.execute(
                sa_text(
                    "INSERT INTO mass_balance_ledger ("
                    "  event_type, event_date, kg_in, kg_out, ref_table, ref_id, "
                    "  ref_doc_no, product_kind, post_balance_kg, notes, created_by"
                    ") VALUES ("
                    "  'byproduct_sale', :event_date, 0, :kg_out, 'byproduct_sale', "
                    "  :ref_id, :ref_doc_no, :product_kind, :post_balance_kg, "
                    "  :notes, :created_by"
                    ")"
                ),
                {
                    "event_date": body.sale_date,
                    "kg_out": body.kg_net,
                    "ref_id": sale_row["id"],
                    "ref_doc_no": body.invoice_no,
                    "product_kind": body.product_kind,
                    "post_balance_kg": post_balance,
                    "notes": body.notes,
                    "created_by": user.id,
                },
            )

            buyer_name_result = await db.execute(
                sa_text("SELECT name FROM byproduct_buyer WHERE id = :id"),
                {"id": body.buyer_id},
            )
            buyer_name = buyer_name_result.scalar_one_or_none()
        # context manager has committed both INSERTs by this point.
    except IntegrityError as exc:
        # ``async with db.begin()`` already issued the rollback before
        # re-raising. No manual rollback needed here.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sale violates DB constraint (buyer_id FK or check constraint)",
        ) from exc

    return ByproductSaleOut(**dict(sale_row), buyer_name=buyer_name)


@router.delete("/sales/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_sale(
    sale_id: int,
    user: OperatorUser,
    db: DbDep,
) -> None:
    """Soft-delete a sale and post a correction ledger row reversing the kg_out.

    Audit trail: the original ledger row stays visible (kg_out preserved); the
    correction row has kg_in = kg_net + corrects_id = original ledger id, so
    v_warehouse_stock restores stock exactly to pre-sale level (net 0) while
    keeping both events in the ledger history.
    """
    # Fetch the sale + companion ledger row in one go (must exist together).
    sale_row = (
        await db.execute(
            sa_text(
                "SELECT id, product_kind, sale_date, kg_net, invoice_no, notes "
                "FROM byproduct_sale "
                "WHERE id = :id AND deleted_at IS NULL"
            ),
            {"id": sale_id},
        )
    ).mappings().one_or_none()
    if sale_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found"
        )

    original_ledger = (
        await db.execute(
            sa_text(
                "SELECT id FROM mass_balance_ledger "
                "WHERE ref_table = 'byproduct_sale' AND ref_id = :ref_id "
                "AND event_type = 'byproduct_sale' AND deleted_at IS NULL"
            ),
            {"ref_id": sale_id},
        )
    ).scalar_one_or_none()

    now = datetime.now(UTC)

    # Soft-delete sale.
    await db.execute(
        sa_text(
            "UPDATE byproduct_sale SET deleted_at = :now WHERE id = :id"
        ),
        {"now": now, "id": sale_id},
    )

    # Keep original ledger row visible (kg_out stays); correction below reverses
    # via kg_in = kg_net so v_warehouse_stock nets to pre-sale level.

    post_balance = await _compute_post_balance(
        db, sale_row["product_kind"], Decimal(0)
    )
    await db.execute(
        sa_text(
            "INSERT INTO mass_balance_ledger ("
            "  event_type, event_date, kg_in, kg_out, ref_table, ref_id, "
            "  ref_doc_no, product_kind, post_balance_kg, corrects_id, notes, "
            "  created_by"
            ") VALUES ("
            "  'correction', :event_date, :kg_in, 0, 'byproduct_sale', "
            "  :ref_id, :ref_doc_no, :product_kind, :post_balance_kg, "
            "  :corrects_id, :notes, :created_by"
            ")"
        ),
        {
            "event_date": sale_row["sale_date"],
            "kg_in": sale_row["kg_net"],
            "ref_id": sale_id,
            "ref_doc_no": sale_row["invoice_no"],
            "product_kind": sale_row["product_kind"],
            "post_balance_kg": post_balance,
            "corrects_id": original_ledger,
            "notes": (
                f"Reversal of byproduct_sale id={sale_id}"
                + (f" — {sale_row['notes']}" if sale_row["notes"] else "")
            ),
            "created_by": user.id,
        },
    )

    await db.commit()


# ---------------------------------------------------------------------------
# Sale invoice PDF — auth-gated streaming
# ---------------------------------------------------------------------------


_BYPRODUCT_ROOT = Path(os.environ.get("BYPRODUCT_ROOT", "/data/byproduct"))


@router.get("/sales/{sale_id}/pdf")
async def stream_sale_pdf(
    sale_id: int,
    _: ViewerUser,
    db: DbDep,
    download: bool = False,
) -> FileResponse:
    """Auth-gated stream of the byproduct-sale invoice PDF.

    Looks up the sale by id and resolves ``pdf_ref`` against
    ``BYPRODUCT_ROOT`` (default ``/data/byproduct``). Refuses any
    resolved path that escapes the byproduct root — defence against
    tampered ``pdf_ref`` values.

    Defaults to ``Content-Disposition: inline`` so the popup iframe can
    render the PDF in-place. Pass ``?download=1`` to force
    ``attachment`` (used by the modal's Download button).
    """
    row = (
        await db.execute(
            sa_text(
                "SELECT id, invoice_no, pdf_ref FROM byproduct_sale "
                "WHERE id = :id AND deleted_at IS NULL"
            ),
            {"id": sale_id},
        )
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Sale not found")
    if not row["pdf_ref"]:
        raise HTTPException(
            status_code=404, detail="No PDF attached to this sale"
        )

    root = _BYPRODUCT_ROOT.resolve()
    candidate = (root / row["pdf_ref"]).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="pdf_ref escapes byproduct root"
        ) from exc
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="PDF missing on disk")

    filename = f"{row['invoice_no'] or f'sale-{sale_id}'}.pdf"
    return FileResponse(
        path=candidate,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="attachment" if download else "inline",
    )
