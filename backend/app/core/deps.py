"""Shared FastAPI dependencies — auth, role gates, current user."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.models.user import User
from app.routers.auth import CurrentUser


def require_role(*allowed: str):
    """Factory: dep that raises 403 unless current user has one of `allowed` roles."""

    def _check(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role in {allowed}",
            )
        return user

    return _check


AdminUser = Annotated[User, Depends(require_role("admin"))]
OperatorUser = Annotated[User, Depends(require_role("admin", "operator"))]
ViewerUser = Annotated[User, Depends(require_role("admin", "operator", "viewer", "certifier"))]
