from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator  # noqa: TC003 — used in runtime annotation
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from app.routers import (
    admin,
    anagrafica,
    auth,
    byproduct_sales,
    consignments,
    daily_inputs,
    daily_production,
    ersv,
    off_takers,
    reports,
    shipments,
    tickets,
    warehouse,
)
from app.services.mv_refresh import refresh_all_mvs

logger = logging.getLogger(__name__)

MV_REFRESH_INTERVAL_MIN = int(os.environ.get("MV_REFRESH_INTERVAL_MIN", "30"))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        refresh_all_mvs,
        "interval",
        minutes=MV_REFRESH_INTERVAL_MIN,
        id="mv_refresh",
        replace_existing=True,
        next_run_time=None,
    )
    scheduler.start()
    logger.info("MV refresh scheduler started (every %d min)", MV_REFRESH_INTERVAL_MIN)
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


_DOCS_KWARGS = (
    {} if os.environ.get("ENABLE_DOCS") == "1"
    else {"docs_url": None, "redoc_url": None, "openapi_url": None}
)
app = FastAPI(title="DFT Mass Balance API", version="0.2.0", lifespan=lifespan, **_DOCS_KWARGS)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(admin.users_router)
app.include_router(anagrafica.suppliers_router)
app.include_router(anagrafica.certificates_router)
app.include_router(anagrafica.contracts_router)
app.include_router(daily_inputs.router)
app.include_router(ersv.router)
app.include_router(tickets.router)
app.include_router(daily_production.router)
app.include_router(reports.router)
app.include_router(off_takers.router)
app.include_router(consignments.router)
app.include_router(shipments.router)
app.include_router(warehouse.router)
app.include_router(byproduct_sales.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.2.0"}
