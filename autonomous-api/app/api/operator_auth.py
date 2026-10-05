"""Operator session endpoints for the platform control surface."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.middleware.security import SessionAuthProvider

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
evolution_control_router = APIRouter(prefix="/api/v1/evolution", tags=["evolution-control"])
settings = get_settings()
_session = SessionAuthProvider(
    secret=settings.SECRET_KEY or "test-session-secret-32-chars-minimum",
    cookie_name="esap_operator_session",
    ttl_seconds=3600,
)


@router.post("/login", status_code=204)
async def login(payload: dict, response: Response):
    supplied = payload.get("api_key")
    expected = settings.ADMIN_API_KEY or ("test-admin-key" if settings.ENVIRONMENT != "production" else "")
    if not supplied or not expected or supplied != expected:
        return JSONResponse(status_code=401, content={"detail": "invalid credentials"})
    token, expires_at = _session.issue("admin", now=__import__("time").time())
    response.set_cookie(
        "esap_operator_session",
        token,
        max_age=_session.ttl_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.ENVIRONMENT == "production",
    )
    return response


@router.get("/session")
async def session(request: Request):
    ctx = await _session.authenticate(request)
    if ctx is None:
        return JSONResponse(status_code=401, content={"detail": "unauthenticated"})
    return {"authenticated": True, "subject": ctx.subject}


@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie("esap_operator_session")
    return response


@evolution_control_router.get("/kill-switch")
async def kill_switch(request: Request):
    supplied = request.headers.get(settings.API_KEY_HEADER, "")
    expected = settings.ADMIN_API_KEY or ("test-admin-key" if settings.ENVIRONMENT != "production" else "")
    if not supplied or not expected or supplied != expected:
        return JSONResponse(status_code=403, content={"detail": "control authorization required"})
    return {"enabled": True, "authorized": True}
