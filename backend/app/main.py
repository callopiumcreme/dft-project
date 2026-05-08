from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from app.routers import admin, auth
from app.services.mv_refresh import refresh_all_mvs

logger = logging.getLogger(__name__)

MV_REFRESH_INTERVAL_MIN = int(os.environ.get("MV_REFRESH_INTERVAL_MIN", "30"))


@asynccontextmanager
async def lifespan(app: FastAPI):
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


app = FastAPI(title="DFT Mass Balance API", version="0.2.0", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(admin.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.2.0"}
