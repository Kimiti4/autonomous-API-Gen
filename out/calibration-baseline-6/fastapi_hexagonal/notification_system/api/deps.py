from __future__ import annotations

from fastapi import HTTPException, Request

from notification_system.config import AUTH_REQUIRED, Settings


def make_auth_dependency(settings: Settings):
    async def verify_api_key(request: Request) -> None:
        if not AUTH_REQUIRED:
            return None
        if not settings.api_key:
            return None
        provided = request.headers.get("X-API-Key")
        if provided != settings.api_key:
            raise HTTPException(
                status_code=401, detail="Invalid or missing API key"
            )
        return None

    return verify_api_key
