"""Read-only, authenticated maintenance-outbox observability for the dashboard."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sqlite3

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import UnauthenticatedError
from app.middleware.security import get_auth
from app.api.operator_auth import authenticate_operator_session

router = APIRouter(prefix="/maintenance-outbox", tags=["maintenance-observability"])


async def require_dashboard_auth(request: Request):
    """Accept the same-origin operator session or the platform API-key provider."""
    try:
        auth = get_auth()
        context = await auth.authenticate(request)
    except UnauthenticatedError:
        context = None
    if context is None:
        context = await authenticate_operator_session(request)
    if context is None:
        raise UnauthenticatedError("Authentication required")
    return context


@lru_cache(maxsize=1)
def _outbox_for_path(database_path: str):
    from app.engine.governed_maintenance_outbox import MaintenanceOutbox

    return MaintenanceOutbox(database_path)


@router.get("")
async def maintenance_outbox_status(
    limit: int = Query(default=20, ge=1, le=100),
    _auth=Depends(require_dashboard_auth),
):
    """Expose queue counts and bounded metadata; never expose evidence payloads or tokens."""
    database_path = get_settings().MAINTENANCE_OUTBOX_DB_PATH.strip()
    if not database_path:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "code": "MAINTENANCE_OUTBOX_NOT_CONFIGURED",
                "message": "Maintenance outbox storage is not configured.",
            },
        )
    if not Path(database_path).expanduser().is_file():
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "code": "MAINTENANCE_OUTBOX_NOT_INITIALIZED",
                "message": "Maintenance outbox storage has not been initialized by its worker.",
            },
        )
    try:
        outbox = _outbox_for_path(database_path)
        return {
            "status": "available",
            "summary": outbox.summary(),
            "items": outbox.list_recent(limit=limit),
        }
    except (OSError, ValueError, RuntimeError, sqlite3.Error):
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "code": "MAINTENANCE_OUTBOX_UNAVAILABLE",
                "message": "Maintenance outbox status is temporarily unavailable.",
            },
        )
