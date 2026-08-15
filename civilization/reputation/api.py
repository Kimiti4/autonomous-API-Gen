"""
API routes for reputation, trust scoring, and capability certification.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .engine import ReputationEngine, ReputationError
from .models import (
    ReputationEventType,
    ReputationOutcome,
    ReputationSubjectType,
)


router = APIRouter(
    prefix="/v1/civilization/reputation",
    tags=["organizational-reputation"],
)


class RecordReputationEventRequest(BaseModel):
    subject_type: ReputationSubjectType
    subject_id: str

    event_type: ReputationEventType
    outcome: ReputationOutcome

    weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    capability: Optional[str] = None

    task_id: Optional[str] = None
    initiative_id: Optional[str] = None

    evidence_refs: List[str] = Field(default_factory=list)

    metadata: dict = Field(default_factory=dict)


class RecordTaskOutcomeRequest(BaseModel):
    subject_type: ReputationSubjectType
    subject_id: str

    task_id: str
    outcome: ReputationOutcome

    capability: Optional[str] = None
    task_type: Optional[str] = None

    weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    evidence_refs: List[str] = Field(default_factory=list)

    metadata: dict = Field(default_factory=dict)


class ApplyCertificationRequest(BaseModel):
    subject_type: ReputationSubjectType
    subject_id: str

    capability: str

    evidence_refs: List[str] = Field(default_factory=list)


class RevokeCertificationRequest(BaseModel):
    reason: str


def enable_reputation(
    app: FastAPI,
    engine: Optional[ReputationEngine] = None,
) -> ReputationEngine:
    """Enable reputation endpoints."""

    reputation_engine = engine or ReputationEngine()

    app.state.reputation_engine = reputation_engine

    app.include_router(router)

    return reputation_engine


def _engine(request: Request) -> ReputationEngine:
    engine = getattr(request.app.state, "reputation_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Reputation engine is not configured.",
        )

    return engine


@router.post("/events", status_code=201)
def record_event(payload: RecordReputationEventRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.record_event(
            subject_type=payload.subject_type,
            subject_id=payload.subject_id,
            event_type=payload.event_type,
            outcome=payload.outcome,
            weight=payload.weight,
            capability=payload.capability,
            task_id=payload.task_id,
            initiative_id=payload.initiative_id,
            evidence_refs=payload.evidence_refs,
            metadata=payload.metadata,
        )
    except ReputationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/task-outcomes", status_code=201)
def record_task_outcome(payload: RecordTaskOutcomeRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.record_task_outcome(
            subject_type=payload.subject_type,
            subject_id=payload.subject_id,
            task_id=payload.task_id,
            outcome=payload.outcome,
            capability=payload.capability,
            task_type=payload.task_type,
            weight=payload.weight,
            evidence_refs=payload.evidence_refs,
            metadata=payload.metadata,
        )
    except ReputationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/events")
def list_events(
    request: Request,
    subject_type: Optional[ReputationSubjectType] = None,
    subject_id: Optional[str] = None,
    event_type: Optional[ReputationEventType] = None,
    limit: int = Query(default=100, ge=1, le=1000),
):
    engine = _engine(request)

    return engine.list_events(
        subject_type=subject_type,
        subject_id=subject_id,
        event_type=event_type,
        limit=limit,
    )


@router.get("/trust/{subject_type}/{subject_id}")
def trust_report(
    subject_type: ReputationSubjectType,
    subject_id: str,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.trust_report(subject_type, subject_id)
    except ReputationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/certifications/applications", status_code=201)
def apply_certification(
    payload: ApplyCertificationRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        application, certification = engine.apply_certification(
            subject_type=payload.subject_type,
            subject_id=payload.subject_id,
            capability=payload.capability,
            evidence_refs=payload.evidence_refs,
        )

        return {
            "application": application,
            "certification": certification,
        }
    except ReputationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/certifications")
def list_certifications(
    request: Request,
    subject_type: Optional[ReputationSubjectType] = None,
    subject_id: Optional[str] = None,
    capability: Optional[str] = None,
    active_only: bool = Query(default=True),
):
    engine = _engine(request)

    return engine.list_certifications(
        subject_type=subject_type,
        subject_id=subject_id,
        capability=capability,
        active_only=active_only,
    )


@router.post("/certifications/{certification_id}/revoke")
def revoke_certification(
    certification_id: str,
    payload: RevokeCertificationRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.revoke_certification(
            certification_id=certification_id,
            reason=payload.reason,
        )
    except ReputationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/capability-report/{subject_type}/{subject_id}"
)
def capability_report(
    subject_type: ReputationSubjectType,
    subject_id: str,
    request: Request,
    capability: str = Query(...),
):
    engine = _engine(request)

    try:
        return engine.capability_report(
            subject_type=subject_type,
            subject_id=subject_id,
            capability=capability,
        )
    except ReputationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
