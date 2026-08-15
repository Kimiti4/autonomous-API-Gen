"""
API routes for autonomous product certification and publishing.
"""

from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel

from .certification import CertificationGateways, ProductCertificationEngine
from .models import ProductCertificationPolicy
from .publishing import PublishingEngine


router = APIRouter(
    prefix="/v1/product-factory/product-certification-publishing",
    tags=["product-certification-publishing"],
)


class CertifyProductRequest(BaseModel):
    product_id: str
    product_version: str
    evidence: Dict = {}
    certified_by: str = "system"


class RevokeCertificationRequest(BaseModel):
    reason: str
    revoked_by: str = "system"


class RequestPublicationRequest(BaseModel):
    product_id: str
    product_version: str
    marketplace_id: str
    publisher_id: str
    certification_report_id: str
    pricing_plan_ref: Optional[str] = None
    approval_ref: Optional[str] = None


class ApprovePublicationRequest(BaseModel):
    approver_id: str
    approval_ref: Optional[str] = None


class RejectPublicationRequest(BaseModel):
    approver_id: str
    reason: str = ""


class PublishRequest(BaseModel):
    approval_ref: Optional[str] = None


class DelistRequest(BaseModel):
    reason: str
    actor_id: str


class GuardrailMetricsRequest(BaseModel):
    metrics: Dict[str, float] = {}


def enable_product_certification_publishing(
    app: FastAPI,
    policy: ProductCertificationPolicy | None = None,
    gateways: CertificationGateways | None = None,
    marketplace_engine=None,
) -> PublishingEngine:
    """Enable product certification and publishing endpoints."""

    certification_policy = policy or ProductCertificationPolicy()

    certification_gateways = gateways or CertificationGateways()

    certification_engine = ProductCertificationEngine(
        policy=certification_policy,
        gateways=certification_gateways,
    )

    publishing_engine = PublishingEngine(
        certification_engine=certification_engine,
        policy=certification_policy,
        marketplace_engine=marketplace_engine,
    )

    app.state.product_certification_engine = certification_engine
    app.state.product_publishing_engine = publishing_engine

    app.include_router(router)

    return publishing_engine


def _certification_engine(request: Request) -> ProductCertificationEngine:
    engine = getattr(request.app.state, "product_certification_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Product certification engine is not configured.",
        )

    return engine


def _publishing_engine(request: Request) -> PublishingEngine:
    engine = getattr(request.app.state, "product_publishing_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Product publishing engine is not configured.",
        )

    return engine


@router.post("/certify", status_code=201)
def certify_product(payload: CertifyProductRequest, request: Request):
    engine = _certification_engine(request)

    return engine.certify_product(
        product_id=payload.product_id,
        product_version=payload.product_version,
        evidence=payload.evidence,
        certified_by=payload.certified_by,
    )


@router.post("/certifications/{report_id}/revoke")
def revoke_certification(
    report_id: str,
    payload: RevokeCertificationRequest,
    request: Request,
):
    engine = _certification_engine(request)

    try:
        return engine.revoke_certification(
            report_id=report_id,
            reason=payload.reason,
            revoked_by=payload.revoked_by,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/publications", status_code=201)
def request_publication(payload: RequestPublicationRequest, request: Request):
    engine = _publishing_engine(request)

    try:
        return engine.request_publication(
            product_id=payload.product_id,
            product_version=payload.product_version,
            marketplace_id=payload.marketplace_id,
            publisher_id=payload.publisher_id,
            certification_report_id=payload.certification_report_id,
            pricing_plan_ref=payload.pricing_plan_ref,
            approval_ref=payload.approval_ref,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/publications/{publication_id}/approve")
def approve_publication(
    publication_id: str,
    payload: ApprovePublicationRequest,
    request: Request,
):
    engine = _publishing_engine(request)

    try:
        return engine.approve_publication(
            publication_id=publication_id,
            approver_id=payload.approver_id,
            approval_ref=payload.approval_ref,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/publications/{publication_id}/reject")
def reject_publication(
    publication_id: str,
    payload: RejectPublicationRequest,
    request: Request,
):
    engine = _publishing_engine(request)

    try:
        return engine.reject_publication(
            publication_id=publication_id,
            approver_id=payload.approver_id,
            reason=payload.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/publications/{publication_id}/publish")
def publish_product(
    publication_id: str,
    payload: PublishRequest,
    request: Request,
):
    engine = _publishing_engine(request)

    try:
        return engine.publish(
            publication_id=publication_id,
            approval_ref=payload.approval_ref,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/publications/{publication_id}/delist")
def delist_product(
    publication_id: str,
    payload: DelistRequest,
    request: Request,
):
    engine = _publishing_engine(request)

    try:
        return engine.delist(
            publication_id=publication_id,
            reason=payload.reason,
            actor_id=payload.actor_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/publications/{publication_id}/guardrails")
def evaluate_guardrails(
    publication_id: str,
    payload: GuardrailMetricsRequest,
    request: Request,
):
    engine = _publishing_engine(request)

    try:
        return engine.evaluate_guardrails(
            publication_id=publication_id,
            metrics=payload.metrics,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
