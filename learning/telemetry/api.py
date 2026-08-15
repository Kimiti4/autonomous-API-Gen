"""
API routes for telemetry adapter ingestion.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from ..engine import ContinuousLearningEngine
from ..models import LearningSignal
from .adapters import TelemetryAdapterRegistry, default_telemetry_adapter_registry
from .models import TelemetryEvent
from ..utils import utcnow

router = APIRouter(prefix="/v1/learning/telemetry", tags=["learning-telemetry"])


class TelemetryCollectPayload(BaseModel):
    source: str
    subject_ref: Optional[str] = None
    signal_type: str = "PERFORMANCE"
    severity: str = "INFO"
    metric: Optional[str] = None
    value: float = 0.0
    unit: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
    labels: dict = Field(default_factory=dict)
    evidence_refs: list = Field(default_factory=list)


def _telemetry_state(request: Request):
    engine = getattr(request.app.state, "telemetry_learning_engine", None)
    registry = getattr(request.app.state, "telemetry_adapter_registry", None)
    if not engine or not registry:
        raise HTTPException(
            500, "Telemetry adapters are not enabled on this application."
        )
    return engine, registry


def enable_telemetry_adapters(
    app: FastAPI,
    learning_engine: Optional[ContinuousLearningEngine] = None,
    registry: Optional[TelemetryAdapterRegistry] = None,
) -> dict:
    """Mount telemetry-adapter ingestion routes on the application.

    This is the safe ingestion boundary for telemetry data: it stores the
    learning engine and adapter registry on ``app.state`` and includes the
    telemetry collection router so external telemetry can be normalized into
    governed learning signals without directly mutating the ISR.
    """
    if learning_engine is None:
        learning_engine = ContinuousLearningEngine()
    if registry is None:
        registry = default_telemetry_adapter_registry()

    app.state.learning_engine = learning_engine
    app.state.telemetry_learning_engine = learning_engine
    app.state.telemetry_adapter_registry = registry

    if any(
        route.path == router.routes[0].path and route.method == "POST"
        for route in getattr(app, "routes", [])
    ):
        return {"learning_engine": learning_engine, "registry": registry}

    app.include_router(router)
    return {"learning_engine": learning_engine, "registry": registry}


@router.post("/collect")
def collect_telemetry(payload: TelemetryCollectPayload, request: Request):
    """Collect a single telemetry event, normalize, and ingest as a signal."""
    engine, registry = _telemetry_state(request)
    event = TelemetryEvent(
        source=payload.source,
        subject_ref=payload.subject_ref,
        signal_type=payload.signal_type,
        severity=payload.severity,
        metric=payload.metric,
        value=payload.value,
        unit=payload.unit,
        message=payload.message,
        timestamp=payload.timestamp or utcnow().isoformat(),
        labels=dict(payload.labels),
        evidence_refs=list(payload.evidence_refs),
    )
    adapter = registry.get(event.source)
    if adapter is None:
        raise HTTPException(404, f"No telemetry adapter registered for source: {event.source}")
    signal: Optional[LearningSignal] = adapter.adapt(event)
    if signal is None:
        raise HTTPException(
            422, "Telemetry event produced no learning signal."
        )
    engine.ingest_signal(signal)
    return {
        "ingested_signal_id": signal.id,
        "signal_type": signal.signal_type.value,
        "source": signal.source,
    }


@router.get("/adapters")
def list_telemetry_adapters(request: Request):
    """List registered telemetry adapter sources."""
    _, registry = _telemetry_state(request)
    return {"adapters": registry.names()}
