"""
Operational Intelligence — Evolutionary Software Architecture Platform.

The sensory system of the platform. Observes reality. Does not generate,
compile, verify, or deploy. Produces fitness signals and knowledge
that close the evolutionary feedback loop.

Constitutional constraints:
1. Observe reality; do not generate software.
2. Never modify the ISR.
3. Never modify generated artifacts.
4. Never directly trigger evolution (produce signals; Evolution Engine consumes them).
5. Never import from engine.* (Phase 6 is a signal producer, not an evolution participant).
6. Classify every observation by responsibility.
7. Detect drift between running system and ISR.
8. Produce machine-readable fitness signals for the Evolution Engine.
9. Produce knowledge for the Knowledge Engine (Phase 7).
10. All observations are append-only historical records.
"""

from constitutional_architecture.operations.telemetry_engine import TelemetryEngine
from constitutional_architecture.operations.observation_model import (
    Observation,
    ObservationClassification,
    FitnessSignal,
    DriftReport,
    Anomaly,
    Incident,
    Recommendation,
)

__all__ = [
    "TelemetryEngine",
    "Observation",
    "ObservationClassification",
    "FitnessSignal",
    "DriftReport",
    "Anomaly",
    "Incident",
    "Recommendation",
]
