"""
API routes for the Marketplace & Plugin Ecosystem.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel

from .engine import PluginEcosystemEngine
from .models import PluginManifestISR, PublisherIdentityISR


router = APIRouter(
    prefix="/v1/marketplace/plugins",
    tags=["marketplace-plugin-ecosystem"],
)


def enable_plugin_ecosystem(app: FastAPI) -> PluginEcosystemEngine:
    """Enable plugin ecosystem routes."""

    engine = PluginEcosystemEngine()

    app.state.plugin_ecosystem_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> PluginEcosystemEngine:
    engine = getattr(request.app.state, "plugin_ecosystem_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Plugin ecosystem engine is not configured.",
        )

    return engine


class PublishPluginRequest(BaseModel):
    manifest: PluginManifestISR


class ApprovePluginRequest(BaseModel):
    approver_id: str


class RevokePluginRequest(BaseModel):
    reason: str
    revoked_by: str


class RegisterPublisherRequest(BaseModel):
    publisher: PublisherIdentityISR


@router.post("/publishers", status_code=201)
def register_publisher(payload: RegisterPublisherRequest, request: Request):
    engine = _engine(request)

    return engine.register_publisher(payload.publisher)


@router.post("/publish", status_code=201)
def publish_plugin(payload: PublishPluginRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.publish_plugin(payload.manifest)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/listings/{listing_id}/approve")
def approve_plugin(
    listing_id: str,
    payload: ApprovePluginRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.approve_plugin(listing_id, payload.approver_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/listings/{listing_id}/install")
def install_plugin(listing_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.install_plugin(listing_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/listings/{listing_id}/execute")
def execute_plugin(listing_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.execute_plugin(listing_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/listings/{listing_id}/revoke")
def revoke_plugin(
    listing_id: str,
    payload: RevokePluginRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.revoke_plugin(
            listing_id,
            payload.reason,
            payload.revoked_by,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/listings")
def list_listings(request: Request):
    engine = _engine(request)

    return engine.list_listings()


@router.get("/revocations")
def list_revocations(request: Request):
    engine = _engine(request)

    return engine.list_revocations()
