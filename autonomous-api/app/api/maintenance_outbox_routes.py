"""Read-only, authenticated maintenance-outbox observability for the dashboard."""
from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.middleware.security import require_auth

router = APIRouter(prefix="/maintenance-outbox", tags=["maintenance-observability"])


@lru_cache(maxsize=1)
def _outbox_for_path(database_path: str):
    from app.engine.governed_maintenance_outbox import MaintenanceOutbox

    return MaintenanceOutbox(database_path)


@router.get("")
async def maintenance_outbox_status(
    limit: int = Query(default=20, ge=1, le=100),
    _auth=Depends(require_auth),
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
    try:
        outbox = _outbox_for_path(database_path)
        return {
            "status": "available",
            "summary": outbox.summary(),
            "items": outbox.list_recent(limit=limit),
        }
    except (OSError, ValueError, RuntimeError):
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "code": "MAINTENANCE_OUTBOX_UNAVAILABLE",
                "message": "Maintenance outbox status is temporarily unavailable.",
            },
        )
