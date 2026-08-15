"""
Runtime Learning Models.

Immutable data records for the closed-loop learning system.

Constitutional Alignment:
- Axiom VII (Auditability): every observation, fitness update, and applied
  mutation is an append-only historical record.
- Axiom II (Genome Isolation): learning produces directives over genes only;
  the ISR is never mutated by the learning engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Tuple


@dataclass(frozen=True)
class EndpointObservation:
    """Runtime telemetry for a single API endpoint, keyed by ISR endpoint id."""

    endpoint_id: str
    request_rate: float = 0.0
    error_rate: float = 0.0
    p95_latency_ms: float = 0.0
    availability: float = 1.0


@dataclass(frozen=True)
class RuntimeObservation:
    """A windowed telemetry snapshot attributed to a running genome."""

    genome_id: str
    endpoints: Tuple[EndpointObservation, ...] = ()
    window_seconds: float = 60.0
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class SLOAttainment:
    """Attainment of one projected SLO against observed runtime telemetry."""

    endpoint_id: str
    reliability_target: float
    error_budget: float
    latency_tolerance_ms: float
    observed_availability: float = 1.0
    observed_p95_ms: float = 0.0
    error_rate: float = 0.0
    availability_attainment: float = 1.0
    latency_attainment: float = 1.0
    budget_burn: float = 0.0
    observed: bool = False

    @property
    def met(self) -> bool:
        if not self.observed:
            return False
        return (
            self.observed_availability >= self.reliability_target
            and self.observed_p95_ms <= self.latency_tolerance_ms
        )


@dataclass(frozen=True)
class MutationDirective:
    """A directed gene mutation suggestion produced by the learning engine."""

    gene_id: str
    action: str  # "increase" | "decrease"
    severity: float = 0.5
    rationale: str = ""
    confidence: float = 0.5


@dataclass(frozen=True)
class FitnessUpdate:
    """Output of the Fitness Update Algorithm for one learning window."""

    genome_id: str
    static_fitness: float
    runtime_multiplier: float
    final_fitness: float
    attainment: Tuple[SLOAttainment, ...] = ()
    directives: Tuple[MutationDirective, ...] = ()
    reasoning: str = ""


@dataclass(frozen=True)
class LearningIteration:
    """Append-only record of one closed-loop learning iteration."""

    number: int
    genome_id: str
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    static_fitness: float = 0.0
    runtime_multiplier: float = 1.0
    final_fitness: float = 0.0
    previous_fitness: float = 0.0
    improvement: float = 0.0
    directives: Tuple[MutationDirective, ...] = ()
    reasoning: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
