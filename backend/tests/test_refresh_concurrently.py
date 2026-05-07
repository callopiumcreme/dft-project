"""QA gate — fix REFRESH CONCURRENTLY: execution_options on engine before connect().

Root cause: conn.execution_options() returns new object, result discarded → AUTOCOMMIT
never applied → autobegin transaction active → REFRESH CONCURRENTLY raises ProgrammingError.
Fix (5fe7d4f): engine.execution_options(isolation_level='AUTOCOMMIT').connect()
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://dft:testonly@localhost:5432/dft")
os.environ.setdefault("JWT_SECRET", "changeme-dft-secret-key-2026")

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_refresh_calls_execution_options_on_engine_not_conn():
    """execution_options(AUTOCOMMIT) must be set on engine, not on the returned conn."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_engine_with_opts = MagicMock()
    mock_engine_with_opts.connect = MagicMock(return_value=mock_conn)

    mock_engine = MagicMock()
    mock_engine.execution_options = MagicMock(return_value=mock_engine_with_opts)

    with patch("app.routers.mass_balance.engine", mock_engine):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/mass-balance/refresh")

    assert resp.status_code == 200
    assert resp.json() == {"status": "refreshed"}

    # execution_options must be called on engine with AUTOCOMMIT
    mock_engine.execution_options.assert_called_once_with(isolation_level="AUTOCOMMIT")
    # connect() must be called on the result of execution_options(), not on engine directly
    mock_engine_with_opts.connect.assert_called_once()
    # engine.connect() must NOT be called directly (old broken pattern)
    mock_engine.connect.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_returns_refreshed_status():
    """POST /mass-balance/refresh returns 200 + {status: refreshed}."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_engine_with_opts = MagicMock()
    mock_engine_with_opts.connect = MagicMock(return_value=mock_conn)

    mock_engine = MagicMock()
    mock_engine.execution_options = MagicMock(return_value=mock_engine_with_opts)

    with patch("app.routers.mass_balance.engine", mock_engine):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/mass-balance/refresh")

    assert resp.status_code == 200
    assert resp.json()["status"] == "refreshed"


@pytest.mark.asyncio
async def test_old_broken_pattern_would_fail():
    """Regression: if execution_options called on conn (old bug), AUTOCOMMIT not applied."""
    # Simulates old code: conn.execution_options() result discarded
    # The engine.execution_options() would NOT be called in the broken path
    mock_conn = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.execution_options = MagicMock()
    # Simulate broken path: connect() called on engine directly (not on execution_options result)
    mock_engine.connect = MagicMock(return_value=mock_conn)

    # In the broken old code, execution_options was called on conn after connect —
    # here we verify the CURRENT code does NOT call engine.connect() directly.
    with patch("app.routers.mass_balance.engine", mock_engine):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/mass-balance/refresh")

    # Fixed code: engine.execution_options() IS called
    mock_engine.execution_options.assert_called_once()
    # Fixed code: engine.connect() directly is NOT called
    mock_engine.connect.assert_not_called()
