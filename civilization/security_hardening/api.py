"""
API routes for security, privacy, and audit hardening.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .engine import SecurityHardeningEngine, SecurityHardeningError
from .models import AccessRequest, SecurityHardeningPolicy


router = APIRouter(
    prefix="/v1/civilization/security",
    tags=["security-privacy-audit-hardening"],
)


class RedactPayloadRequest(BaseModel):
    payload: Dict[str, Any] = Field(default_factory=dict)


class ClassifyPayloadRequest(BaseModel):
    payload: Dict[str, Any] = Field(default_factory=dict)


def enable_security_hardening(
    app: FastAPI,
    policy_engine=None,
    oversight_engine=None,
    policy: Optional[SecurityHardeningPolicy] = None,
) -> SecurityHardeningEngine:
    """Enable security hardening endpoints."""

    engine = SecurityHardeningEngine(
        policy=policy,
        policy_engine=policy_engine,
        oversight_engine=oversight_engine,
    )

    app.state.security_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> SecurityHardeningEngine:
    engine = getattr(request.app.state, "security_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Security hardening engine is not configured.",
        )

    return engine


@router.post("/authorize")
def authorize(payload: AccessRequest, request: Request):
    engine = _engine(request)
    return engine.authorize(payload)


@router.post("/redact")
def redact(payload: RedactPayloadRequest, request: Request):
    engine = _engine(request)
    return engine.redact_payload(payload.payload)


@router.post("/classify")
def classify(payload: ClassifyPayloadRequest, request: Request):
    engine = _engine(request)
    return engine.classify_payload(payload.payload)


@router.get("/audit/events")
def audit_events(request: Request):
    engine = _engine(request)
    return engine.audit_events


@router.post("/audit/verify")
def audit_verify(request: Request):
    engine = _engine(request)
    return engine.verify_audit()


@router.get("/alerts")
def alerts(request: Request, status: Optional[str] = None):
    engine = _engine(request)
    return engine.list_alerts(status=status)


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.acknowledge_alert(alert_id)
    except SecurityHardeningError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.resolve_alert(alert_id)
    except SecurityHardeningError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/report")
def report(request: Request):
    engine = _engine(request)
    return engine.report()
