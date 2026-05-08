"""Admin endpoints — MV refresh, scheduler status. Admin role only."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import AdminUser
from app.services.mv_refresh import refresh_all_mvs

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/refresh-mvs")
async def refresh_mvs(_: AdminUser) -> dict[str, dict[str, str]]:
    results = await refresh_all_mvs()
    return {"refreshed": results}
