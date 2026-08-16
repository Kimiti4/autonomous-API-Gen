"""R2.9.6 -- Multiple simultaneous and interacting defects.

Reuses the R2.9.2-R2.9.5 machinery; adds only the multi-defect observation
model, joint evaluation, subset-dominance selection, and cumulative regression
tracking. No new architectural authority: the R2.8 boundary and R2.6 Pareto
remain the decision-makers.

Constitutional constraints honored:
* Defect isolation: each observation retains its own identity.
* No single aggregate score: partial repair is compared by subset dominance on
  a per-defect profile, never collapsed to one number.
* Interaction detection through execution: every candidate is re-evaluated
  against EVERY defect through the R2.8 boundary; no special-case interaction
  rules. If repairing A changes how B manifests, re-running B against the
  repaired-A candidate reveals it.
* Regression preservation: a cumulative resolution tracker grows
  monotonically; a candidate that un-resolves a previously resolved defect is
  rejected as a regression, never re-litigated. This is the anti-oscillation
  guarantee (fix A -> repair B -> A stays fixed).
* ``_resolves_observation`` (the boundary's target_failure gate) is the
  canonical resolution signal -- no second truth oracle.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping, Optional, Protocol, Sequence, Tuple

from constitutional_architecture.isr.model import ISR

from tiannara.application.evolution.competitive_evolution import (
    DeterministicComplexityPreference,
    ScoredCandidate,
    SelectionStrategy,
    pareto_frontier,
)
from tiannara.application.evolution.mutation_operators import MutationCandidate
from tiannara.application.evolution.evolution_state import TerminationReason
from tiannara.domain.models.observation import FailureObservation


# -- observation model --------------------------------------------------------

@dataclass(frozen=True)
class DefectSet:
    """Multiple simultaneous defect observations, each retaining its identity.

    Observation identity: ``evidence_hash`` -- the content-address over the
    observation's normalized inputs, the canonical observation identity the
    ledger and ``derive_evolution_id`` already key on (the model has no
    separate ``observation_id`` field).
    """

    observations: tuple

    @property
    def observation_ids(self) -> tuple[str, ...]:
        return tuple(o.evidence_hash for o in self.observations)

    def for_observation(self, observation_id: str) -> FailureObservation:
        for obs in self.observations:
            if obs.evidence_hash == observation_id:
                return obs
        raise KeyError(observation_id)

    def __len__(self) -> int:
        return len(self.observations)


# -- per-defect resolution profile --------------------------------------------

@dataclass(frozen=True)
class DefectResolutionProfile:
    """Per-defect resolution status for one candidate, determined by execution.

    Preserves defect isolation (each observation identified) while enabling
    joint evaluation (every candidate checked against every defect).
    """

    resolutions: Mapping[str, bool]   # observation_id -> resolved

    def resolved_set(self) -> frozenset[str]:
        return frozenset(oid for oid, ok in self.resolutions.items() if ok)

    def dominates(self, other: "DefectResolutionProfile") -> bool:
        """Strict-superset dominance: resolves everything other does, plus more."""
        return self.resolved_set() > other.resolved_set()

    @property
    def all_resolved(self) -> bool:
        return bool(self.resolutions) and all(self.resolutions.values())

    @property
    def resolution_fraction(self) -> float:
        if not self.resolutions:
            return 1.0
        return sum(self.resolutions.values()) / len(self.resolutions)


class CumulativeResolutionTracker:
    """Monotonically-growing set of resolved defects (anti-oscillation).

    Once a selected candidate resolves a defect, it stays resolved. A later
    candidate that un-resolves it is a regression, not a re-opened question.
    Search-process state: lives on the coordinator, never in the ISR.
    """

    def __init__(self) -> None:
        self._resolved: set[str] = set()

    def accept(self, profile: DefectResolutionProfile) -> None:
        self._resolved |= profile.resolved_set()

    def regressed_by(self, profile: DefectResolutionProfile) -> frozenset[str]:
        """Defects previously resolved that this candidate no longer resolves."""
        return frozenset(self._resolved - profile.resolved_set())

    @property
    def resolved(self) -> frozenset[str]:
        return frozenset(self._resolved)


# -- joint evaluation ---------------------------------------------------------

@dataclass(frozen=True)
class MultiDefectScore:
    """One candidate's joint verdict across every defect observation."""

    candidate: MutationCandidate
    profile: DefectResolutionProfile
    acceptances: Mapping[str, bool]                       # obs_id -> boundary accept
    tiebreak: Optional[ScoredCandidate] = None            # first accepted obs's R2.6 score

    @property
    def eligible(self) -> bool:
        """The R2.8 boundary accepted the candidate for at least one
        observation -- the candidate is architecturally legitimate."""
        return any(self.acceptances.values())


class MultiDefectEvaluator:
    """Evaluates a candidate against EVERY defect through the R2.8 boundary.

    This is the interaction-detection mechanism: every candidate is
    re-evaluated against every defect observation through execution, with no
    special-case rules. The ``score_one`` callback is the boundary itself
    (``score_candidate`` bound to one observation); the resolution signal is
    the boundary's own target_failure verdict (``_resolves_observation``).
    """

    def __init__(
        self,
        score_one: Callable[[MutationCandidate, FailureObservation], "tuple[ScoredCandidate, bool]"],
    ) -> None:
        self._score_one = score_one

    def evaluate(self, candidate: MutationCandidate, defect_set: DefectSet) -> MultiDefectScore:
        resolutions: dict[str, bool] = {}
        acceptances: dict[str, bool] = {}
        tiebreak: Optional[ScoredCandidate] = None
        for obs in defect_set.observations:
            obs_id = obs.evidence_hash
            scored, resolved = self._score_one(candidate, obs)
            resolutions[obs_id] = resolved
            acceptances[obs_id] = scored.verdict.accept
            if tiebreak is None and scored.verdict.accept:
                tiebreak = scored
        return MultiDefectScore(
            candidate,
            DefectResolutionProfile(resolutions),
            acceptances,
            tiebreak,
        )


# -- selection -----------------------------------------------------------------

class MultiDefectSelector:
    """Selects among candidates using subset dominance on resolution profiles,
    with the existing R2.6 FitnessVector Pareto as the secondary comparison.

    Hard constraint first: a candidate that regresses a cumulatively-resolved
    defect is rejected outright -- this is what prevents fix-A/break-A
    oscillation. Partial repair is legitimate (fixing A only is a step
    forward); it is distinguished from full repair by strict-superset
    dominance, never by a scalar count.
    """

    def __init__(self, pareto_selector: Optional[SelectionStrategy] = None) -> None:
        self._pareto = pareto_selector or DeterministicComplexityPreference()

    def select(
        self,
        scores: Sequence[MultiDefectScore],
        tracker: CumulativeResolutionTracker,
    ) -> Optional[MultiDefectScore]:
        viable = [
            s for s in scores
            if s.eligible and not tracker.regressed_by(s.profile)
        ]
        if not viable:
            return None
        non_dominated = [
            s for s in viable
            if not any(
                other.profile.dominates(s.profile)
                for other in viable if other is not s
            )
        ]
        # Delegate the remaining tie-break to the existing Pareto machinery.
        with_tiebreak = [s for s in non_dominated if s.tiebreak is not None]
        if with_tiebreak:
            frontier = pareto_frontier([s.tiebreak for s in with_tiebreak])
            chosen = self._pareto.select(frontier)
            if chosen is not None:
                return next(
                    s for s in with_tiebreak if s.tiebreak is chosen
                )
        return sorted(
            non_dominated,
            key=lambda s: (
                s.candidate.candidate_id if s.candidate is not None else "",
                s.profile.resolution_fraction,
            ),
        )[0]


# -- generation / run state -----------------------------------------------------

@dataclass(frozen=True)
class MultiDefectGeneration:
    generation_id: str
    generation_index: int
    parent_generation_id: Optional[str]
    parent_isr_hash: str
    selected_candidate_id: Optional[str]
    selected_operator_id: Optional[str]
    profile: DefectResolutionProfile          # the selected candidate's per-defect status
    resolved_defects: frozenset[str]          # CUMULATIVE tracker snapshot (monotonic)
    evaluated_count: int
    eligible_count: int
    regression_rejections: tuple = field(default_factory=tuple)  # (candidate_id, frozenset)

    @property
    def all_resolved(self) -> bool:
        return self.profile.all_resolved


@dataclass(frozen=True)
class MultiDefectRunResult:
    evolution_id: str
    initial_isr_hash: str
    defect_ids: tuple
    generations: tuple
    termination_reason: TerminationReason
    final_isr_hash: str
    deceptive_rejected: bool = False
    total_joint_evaluations: int = 0

    @property
    def succeeded(self) -> bool:
        return self.termination_reason is TerminationReason.SUCCESS

    @property
    def repair_stability(self) -> float:
        """P(a resolved defect stays resolved across subsequent generations),
        per-defect, averaged. The tracker rejects regressions, so a clean run
        scores 1.0; the per-generation ``resolved_defects`` ledger evidence is
        what R2.9.8 certification attests against."""
        by_defect: dict[str, list[int]] = {}
        for gen in self.generations:
            for oid in gen.resolved_defects:
                by_defect.setdefault(oid, []).append(gen.generation_index)
        if not by_defect:
            return 1.0
        stabilities = []
        for oid, gens in by_defect.items():
            if len(gens) < 2:
                stabilities.append(1.0)
                continue
            stays = sum(
                1 for a, b in zip(gens, gens[1:]) if b == a + 1
            )
            stabilities.append(stays / (len(gens) - 1))
        return sum(stabilities) / len(stabilities)


# -- substrate adapter ---------------------------------------------------------

class ObservationBoundarySandbox:
    """Per-observation boundary sandbox: compiles normally, but runs THE
    observation's test against every artifact. This is how the R2.8 boundary
    is exercised independently per defect -- execution is the oracle."""

    def __init__(self, inner, observation: FailureObservation) -> None:
        self._inner = inner
        self._observation = observation

    def build(self, isr: ISR, workspace: Optional[str] = None):
        return self._inner.build(isr, workspace)

    def run_tests(self, artifact) -> "TestRunResult":
        return self._inner.run_tests(artifact, self._observation)


# -- variation port -------------------------------------------------------------

class MultiDefectVariation(Protocol):
    """A population generator for a defect SET (R2.9.6). Deterministic under
    (current_isr, defect_set, seed)."""

    def generate(
        self,
        current_isr: ISR,
        defect_set: DefectSet,
        population_size: int,
        seed: int,
    ) -> Sequence[MutationCandidate]:
        ...
