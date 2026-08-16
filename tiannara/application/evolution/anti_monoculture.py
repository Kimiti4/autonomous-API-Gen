"""R2.9.4 -- Population diversity / anti-monoculture.

Evidence-first: R2.9.3 observes diversity; R2.9.4 diagnoses monoculture from
the recorded trajectories and applies the MINIMAL intervention to prevent it.

Constitutional constraints honored:
* No single aggregate score: diversity is NEVER collapsed into the
  FitnessVector and NEVER used as a selection objective. It is a
  population-health constraint that operates at the population-management
  level (cull near-duplicates, inject diverse candidates). A diverse-but-
  deceptive candidate is still rejected by the R2.8 boundary -- diversity
  never overrides correctness.
* Each stage independently replaceable: the preservation policy is a
  protocol; R2.9.5 (adaptive operator scheduling) may replace it.
* Evolution on the ISR: diversity is measured on ISR/delta identity, never
  on generated source.
* Evidence-based: the diagnostic analyzes observed trajectories before any
  intervention is applied; thresholds are tuned from R2.9.3 evidence, not
  assumed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Protocol, Sequence

from tiannara.application.evolution.evolution_state import DiversityMetrics
from tiannara.application.evolution.ledger import stable_isr_hash


@dataclass(frozen=True)
class MonocultureThresholds:
    """Detection thresholds. Configurable; tuned from R2.9.3 diagnostic
    evidence (see the R2.9.4 closure record)."""

    entropy_floor: float = 0.5       # genotype_entropy below this => monoculture
    duplicate_ceiling: float = 0.7   # duplicate_rate above this => monoculture


class MonocultureDetector:
    """Per-generation detection from observed DiversityMetrics."""

    def __init__(self, thresholds: Optional[MonocultureThresholds] = None) -> None:
        self._thresholds = thresholds or MonocultureThresholds()

    def is_monoculture(self, metrics: DiversityMetrics) -> bool:
        if metrics.population_size <= 1:
            return False  # a single candidate is small, not monocultural
        return (
            metrics.genotype_entropy < self._thresholds.entropy_floor
            or metrics.duplicate_rate > self._thresholds.duplicate_ceiling
        )


@dataclass(frozen=True)
class MonocultureDiagnostic:
    """Evidence-first analysis of a run's diversity trajectory.

    Reports what R2.9.3's observation recorded. It does NOT intervene.
    """

    monoculture_detected: bool
    first_monoculture_generation: Optional[int]
    min_entropy: float
    max_duplicate_rate: float
    generations_analyzed: int

    @property
    def severity(self) -> str:
        if not self.monoculture_detected:
            return "none"
        if self.min_entropy <= 0.0:
            return "total_collapse"
        return "partial"


class DiversityDiagnostics:
    """Analyzes a completed run's diversity trajectory (the evidence phase)."""

    def __init__(self, detector: Optional[MonocultureDetector] = None) -> None:
        self._detector = detector or MonocultureDetector()

    def diagnose(self, trajectory: Sequence[DiversityMetrics]) -> MonocultureDiagnostic:
        if not trajectory:
            return MonocultureDiagnostic(False, None, 0.0, 0.0, 0)
        first = next(
            (i for i, m in enumerate(trajectory) if self._detector.is_monoculture(m)),
            None,
        )
        return MonocultureDiagnostic(
            monoculture_detected=first is not None,
            first_monoculture_generation=first,
            min_entropy=min(m.genotype_entropy for m in trajectory),
            max_duplicate_rate=max(m.duplicate_rate for m in trajectory),
            generations_analyzed=len(trajectory),
        )


class DiversityPreservationPolicy(Protocol):
    """Pluggable intervention, independently replaceable per constitution.

    Returns a rebalanced population when monoculture is detected; otherwise
    the population unchanged. Must remain deterministic under ``seed``.
    """

    def apply(
        self,
        population: Sequence,
        metrics: DiversityMetrics,
        generate_more: Callable[[int, int], Sequence],
        seed: int,
    ) -> Sequence:
        ...


class DeterministicDiversityInjection:
    """Default policy: cull near-duplicates, inject deterministically-seeded
    diverse candidates when monoculture is detected.

    Injected candidates come from the SAME variation operator with a
    perturbed seed, so they explore a different region of the mutation space.
    They are ISR deltas and are subject to the R2.8 boundary exactly like the
    rest of the population -- there is no separate evaluation route. Diversity
    is managed here; it is NEVER scored as fitness.
    """

    def __init__(
        self,
        detector: Optional[MonocultureDetector] = None,
        injection_count: int = 4,
        seed_perturbation: int = 10_000,
    ) -> None:
        self._detector = detector or MonocultureDetector()
        self._injection_count = injection_count
        self._seed_perturbation = seed_perturbation

    def apply(self, population, metrics, generate_more, seed):
        if not self._detector.is_monoculture(metrics):
            return population
        seen: set[str] = set()
        result = []
        for c in population:
            identity = stable_isr_hash(c.candidate_isr)
            if identity not in seen:
                seen.add(identity)
                result.append(c)
        injected = generate_more(self._injection_count, seed + self._seed_perturbation)
        for c in injected:
            identity = stable_isr_hash(c.candidate_isr)
            if identity not in seen:
                seen.add(identity)
                result.append(c)
        return result