"""
API routes for operational resilience.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .engine import ResilienceEngine, ResilienceError
from .models import DegradationMode, FailureSeverity


router = APIRouter(
    prefix="/v1/civilization/resilience",
    tags=["operational-resilience"],
)


class RecordFailurePayload(BaseModel):
    component: str
    operation: str

    error: str = ""

    severity: FailureSeverity = FailureSeverity.MEDIUM

    context: dict = Field(default_factory=dict)


class RecordSuccessPayload(BaseModel):
    component: str
    operation: str


class CheckRequestPayload(BaseModel):
    component: str
    operation: str

    action_category: str = "READ"

    high_impact: bool = False


class DegradationModePayload(BaseModel):
    mode: DegradationMode
    reason: str

    actor_id: str = "api"


class QuorumPayload(BaseModel):
    group_id: str

    total_weight: float
    participating_weight: float

    required_ratio: float = Field(default=0.5, ge=0.0, le=1.0)


class RetryPayload(BaseModel):
    operation: str

    attempt: int = Field(default=0, ge=0)

    error_class: str = "TRANSIENT"


class ChaosDrillPayload(BaseModel):
    name: str
    scenario: str
    target_component: str

    expected_safe_state: str = "OPEN"

    failure_count: Optional[int] = None


def enable_resilience(
    app: FastAPI,
    oversight_engine=None,
) -> ResilienceEngine:
    """Enable resilience endpoints."""

    engine = ResilienceEngine(oversight_engine=oversight_engine)

    app.state.resilience_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> ResilienceEngine:
    engine = getattr(request.app.state, "resilience_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Resilience engine is not configured.",
        )

    return engine


@router.post("/failures", status_code=201)
def record_failure(payload: RecordFailurePayload, request: Request):
    engine = _engine(request)

    try:
        return engine.record_failure(
            component=payload.component,
            operation=payload.operation,
            error=payload.error,
            severity=payload.severity,
            context=payload.context,
        )
    except ResilienceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/success")
def record_success(payload: RecordSuccessPayload, request: Request):
    engine = _engine(request)

    try:
        return engine.record_success(
            component=payload.component,
            operation=payload.operation,
        )
    except ResilienceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/check")
def check(payload: CheckRequestPayload, request: Request):
    engine = _engine(request)

    return engine.allow_request(
        component=payload.component,
        operation=payload.operation,
        action_category=payload.action_category,
        high_impact=payload.high_impact,
    )


@router.get("/circuits")
def circuits(request: Request):
    engine = _engine(request)
    return list(engine.circuits.values())


@router.post("/degradation-mode")
def set_degradation_mode(payload: DegradationModePayload, request: Request):
    engine = _engine(request)

    return engine.set_degradation_mode(
        mode=payload.mode,
        reason=payload.reason,
        actor_id=payload.actor_id,
    )


@router.get("/degradation-mode")
def get_degradation_mode(request: Request):
    engine = _engine(request)
    return {"mode": engine.mode}


@router.post("/quorum/evaluate")
def evaluate_quorum(payload: QuorumPayload, request: Request):
    engine = _engine(request)

    return engine.evaluate_quorum(
        group_id=payload.group_id,
        total_weight=payload.total_weight,
        participating_weight=payload.participating_weight,
        required_ratio=payload.required_ratio,
    )


@router.post("/retry-decision")
def retry_decision(payload: RetryPayload, request: Request):
    engine = _engine(request)

    return engine.retry_decision(
        operation=payload.operation,
        attempt=payload.attempt,
        error_class=payload.error_class,
    )


@router.post("/chaos/drill", status_code=201)
def chaos_drill(payload: ChaosDrillPayload, request: Request):
    engine = _engine(request)

    try:
        return engine.run_chaos_drill(
            name=payload.name,
            scenario=payload.scenario,
            target_component=payload.target_component,
            expected_safe_state=payload.expected_safe_state,
            failure_count=payload.failure_count,
        )
    except ResilienceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/report")
def report(request: Request):
    engine = _engine(request)
    return engine.report()
