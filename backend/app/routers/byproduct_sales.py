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


# Virtual-row id offset for Crown commercial invoices projected read-only
# from `consignment_pos_customs`. The customs table is the system-of-record
# for Crown DEV-P100 invoices (they enter via the consignment workflow, not
# via byproduct_sale POST — eu_oil is excluded from the byproduct_sale
# CHECK constraint by design). We surface them here for unified display
# without copying rows: virtual_id = CUSTOMS_VIRTUAL_OFFSET + customs.id.
# Modal/stream PDF detect the offset and re-route to the customs PDF.
CUSTOMS_VIRTUAL_OFFSET = 1_000_000


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

    Result is a UNION of:
    - byproduct_sale rows (canonical store for plus_oil / carbon_black /
      metal_scrap sales — Conquer Trade etc.)
    - consignment_pos_customs rows projected as virtual eu_oil sales
      (Crown Oil DEV-P100 commercial invoices — read-only display only,
      no INSERT, no ledger touch). Virtual id is offset by
      CUSTOMS_VIRTUAL_OFFSET so the modal/stream PDF can detect and
      re-route to the customs file.

    Ordered by sale_date DESC, id DESC.
    """
    # --- byproduct_sale branch (canonical) ---
    byproduct_sql = (
        "SELECT s.id, s.product_kind, s.buyer_id, s.sale_date, s.kg_net, "
        "s.invoice_no, s.price_eur, s.price_amount, s.currency, s.pricing_method, "
        "(s.pdf_ref IS NOT NULL) AS has_pdf, "
        "s.notes, s.created_at, b.name AS buyer_name "
        "FROM byproduct_sale s "
        "LEFT JOIN byproduct_buyer b ON b.id = s.buyer_id "
        "WHERE s.deleted_at IS NULL"
    )
    byproduct_params: dict[str, object] = {}
    if product_kind is not None:
        byproduct_sql += " AND s.product_kind = :product_kind"
        byproduct_params["product_kind"] = product_kind
    if buyer_id is not None:
        byproduct_sql += " AND s.buyer_id = :buyer_id"
        byproduct_params["buyer_id"] = buyer_id
    if from_date is not None:
        byproduct_sql += " AND s.sale_date >= :from_date"
        byproduct_params["from_date"] = from_date
    if to_date is not None:
        byproduct_sql += " AND s.sale_date <= :to_date"
        byproduct_params["to_date"] = to_date

    byproduct_rows = (
        await db.execute(sa_text(byproduct_sql), byproduct_params)
    ).mappings().all()

    out: list[ByproductSaleOut] = [ByproductSaleOut(**dict(r)) for r in byproduct_rows]

    # --- consignment_pos_customs branch (Crown DEV-P100 virtual rows) ---
    # Only emit if the product/buyer filter does not exclude Crown/eu_oil.
    skip_customs = False
    if product_kind is not None and product_kind != "eu_oil":
        skip_customs = True
    if buyer_id is not None:
        crown_buyer_id = (
            await db.execute(
                sa_text(
                    "SELECT id FROM byproduct_buyer "
                    "WHERE name = 'CROWN OIL LTD' AND deleted_at IS NULL"
                )
            )
        ).scalar_one_or_none()
        if crown_buyer_id is None or buyer_id != crown_buyer_id:
            skip_customs = True

    if not skip_customs:
        customs_sql = (
            "SELECT c.id AS customs_id, c.invoice_no, c.net_kg, c.issuing_date, "
            "c.invoice_pdf_ref, c.pos_number, "
            "(p.pdf_ref IS NOT NULL) AS has_pos_pdf, "
            "b.id AS buyer_id, b.name AS buyer_name "
            "FROM consignment_pos_customs c "
            "LEFT JOIN consignment_pos p "
            "  ON p.consignment_id = c.consignment_id "
            " AND p.pos_number = c.pos_number "
            " AND p.deleted_at IS NULL "
            "CROSS JOIN ("
            "  SELECT id, name FROM byproduct_buyer "
            "  WHERE name = 'CROWN OIL LTD' AND deleted_at IS NULL"
            ") b "
            "WHERE c.deleted_at IS NULL AND c.invoice_no IS NOT NULL"
        )
        customs_params: dict[str, object] = {}
        if from_date is not None:
            customs_sql += " AND c.issuing_date >= :from_date"
            customs_params["from_date"] = from_date
        if to_date is not None:
            customs_sql += " AND c.issuing_date <= :to_date"
            customs_params["to_date"] = to_date

        customs_rows = (
            await db.execute(sa_text(customs_sql), customs_params)
        ).mappings().all()

        for r in customs_rows:
            out.append(
                ByproductSaleOut(
                    id=CUSTOMS_VIRTUAL_OFFSET + int(r["customs_id"]),
                    product_kind="eu_oil",
                    buyer_id=int(r["buyer_id"]),
                    buyer_name=r["buyer_name"],
                    sale_date=r["issuing_date"],
                    kg_net=r["net_kg"],
                    invoice_no=r["invoice_no"],
                    price_eur=None,
                    price_amount=None,
                    currency=None,
                    pricing_method=None,
                    has_pdf=bool(r["invoice_pdf_ref"]),
                    pos_no=r["pos_number"],
                    has_pos_pdf=bool(r["has_pos_pdf"]),
                    notes=(
                        "Read-only projection from consignment_pos_customs "
                        "(Crown DEV-P100 commercial invoice)."
                    ),
                    created_at=datetime.now(UTC),
                )
            )

    # Sort UNION by sale_date DESC, id DESC.
    out.sort(key=lambda s: (s.sale_date, s.id), reverse=True)
    return out


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

    Virtual Crown rows (sale_id >= CUSTOMS_VIRTUAL_OFFSET) are read-only
    projections from consignment_pos_customs and cannot be deleted here —
    Crown invoices are managed via the consignment workflow.
    """
    if sale_id >= CUSTOMS_VIRTUAL_OFFSET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Crown DEV-P100 invoices are read-only projections from the "
                "consignment workflow; delete via /consignments instead."
            ),
        )

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
_INVOICES_ROOT = Path(os.environ.get("INVOICES_ROOT", "/data/invoices"))
_POS_DOCUMENTS_ROOT = Path(
    os.environ.get("POS_DOCUMENTS_ROOT", "/data/pos_documents")
)


@router.get("/sales/{sale_id}/pdf")
async def stream_sale_pdf(
    sale_id: int,
    _: ViewerUser,
    db: DbDep,
    download: bool = False,
) -> FileResponse:
    """Auth-gated stream of the byproduct-sale invoice PDF.

    Two branches:
    - sale_id < CUSTOMS_VIRTUAL_OFFSET: canonical byproduct_sale lookup,
      resolves ``pdf_ref`` against ``BYPRODUCT_ROOT`` (default
      ``/data/byproduct``).
    - sale_id >= CUSTOMS_VIRTUAL_OFFSET: virtual Crown DEV-P100 row;
      strips the offset and resolves
      ``consignment_pos_customs.invoice_pdf_ref`` against
      ``INVOICES_ROOT`` (default ``/data/invoices``), matching the
      consignments router PDF endpoint.

    Both branches refuse paths that escape their root (path-traversal
    defence). Defaults to ``Content-Disposition: inline``; pass
    ``?download=1`` to force ``attachment``.
    """
    # --- Virtual customs row branch (Crown DEV-P100) ---
    if sale_id >= CUSTOMS_VIRTUAL_OFFSET:
        customs_id = sale_id - CUSTOMS_VIRTUAL_OFFSET
        row = (
            await db.execute(
                sa_text(
                    "SELECT id, invoice_no, invoice_pdf_ref "
                    "FROM consignment_pos_customs "
                    "WHERE id = :id AND deleted_at IS NULL"
                ),
                {"id": customs_id},
            )
        ).mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Sale not found")
        if not row["invoice_pdf_ref"]:
            raise HTTPException(
                status_code=404, detail="No PDF attached to this sale"
            )

        root = _INVOICES_ROOT.resolve()
        candidate = (root / row["invoice_pdf_ref"]).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail="pdf_ref escapes invoices root"
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

    # --- Canonical byproduct_sale branch ---
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


@router.get("/sales/{sale_id}/pos.pdf")
async def stream_sale_pos_pdf(
    sale_id: int,
    _: ViewerUser,
    db: DbDep,
    download: bool = False,
) -> FileResponse:
    """Auth-gated stream of the POS PDF paired with a virtual Crown sale row.

    Only available for sale_id >= CUSTOMS_VIRTUAL_OFFSET (Crown DEV-P100
    customs projections). The matching POS is looked up by
    (consignment_id, pos_number) on ``consignment_pos`` and resolved against
    ``POS_DOCUMENTS_ROOT`` (default ``/data/pos_documents``).

    Canonical byproduct_sale rows (Conquer plus_oil, carbon_black,
    metal_scrap) have no POS counterpart and return 400 here — POS is a
    consignment-workflow artefact, not a byproduct field.
    """
    if sale_id < CUSTOMS_VIRTUAL_OFFSET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="POS is only available for Crown DEV-P100 sales.",
        )

    customs_id = sale_id - CUSTOMS_VIRTUAL_OFFSET
    row = (
        await db.execute(
            sa_text(
                "SELECT p.consignment_id, p.pos_number, p.pdf_ref "
                "FROM consignment_pos_customs c "
                "JOIN consignment_pos p "
                "  ON p.consignment_id = c.consignment_id "
                " AND p.pos_number = c.pos_number "
                " AND p.deleted_at IS NULL "
                "WHERE c.id = :id AND c.deleted_at IS NULL"
            ),
            {"id": customs_id},
        )
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="POS not found for this sale")
    if not row["pdf_ref"]:
        raise HTTPException(status_code=404, detail="No POS PDF on file")

    # ``pdf_ref`` is a legacy Drive-style ref (e.g.
    # ``gdrive:DFT_2025/POS TO CROWN/OutgoingMaterial_Declaration_<pos>.pdf``).
    # Local files live under ``POS_DOCUMENTS_ROOT/c-<consignment_id>/<basename>``
    # — strip any leading ``gdrive:`` scheme + dirname and re-anchor on disk.
    raw_ref = row["pdf_ref"]
    if raw_ref.startswith("gdrive:"):
        raw_ref = raw_ref[len("gdrive:"):]
    basename = os.path.basename(raw_ref)
    if not basename:
        raise HTTPException(status_code=404, detail="POS PDF ref empty")

    root = _POS_DOCUMENTS_ROOT.resolve()
    candidate = (root / f"c-{int(row['consignment_id'])}" / basename).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="pdf_ref escapes pos_documents root"
        ) from exc
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="POS PDF missing on disk")

    filename = f"POS_{row['pos_number']}.pdf"
    return FileResponse(
        path=candidate,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="attachment" if download else "inline",
    )
