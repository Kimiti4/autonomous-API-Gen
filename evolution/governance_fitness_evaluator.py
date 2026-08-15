"""Candidate-scoped governance fitness for the evolution loop.

Plugs the Phase 28 governance-DNS fitness into ``SelfEvolutionEngine``'s
injectable ``fitness_evaluator`` seam, so the live evolution feedback loop
ranks each candidate on ITS OWN expressed ``GovernanceDesignISR`` rather than a
single platform-wide score. This is the evolution-loop analogue of
``constitutional_architecture/engine/bridges/governance_candidate_fitness.py``
(which targets the Phase 21 ``Individual`` genome / chromosome port): this
module adapts the same six-dimension vocabulary to ``evolution``'s
``CandidateArchitecture.isr`` (a plain dict) loop.

Integration contract (dimension-set consistency):
  * every candidate's ``FitnessEvaluation.objectives`` carries the identical
    six governance objective keys (``ALL_OBJECTIVES``). Candidates with no
    expressed governance design score the fail-closed 0.0 vector, preserving
    dimension-set consistency so Pareto dominance/distance math is sound.
  * ``select_pareto`` auto-derives its selection dimensions from the union of
    each ``FitnessEvaluation.objectives`` keys (evolution/pareto.py:250-258),
    so these six are ranked for selection automatically; the per-objective
    ``min_objective_value`` gate enforces fail-closed (0.0 < 0.2 excludes a
    candidate whose governance design is absent or malformed).
  * the base ``FitnessEvaluator.passed`` gate is inherited unchanged (it is
    recomputed by the base class on the architecture objectives only);
    governance objectives feed Pareto selection/ranking, not the binary
    proposal pass/fail gate.

The substantive scoring heuristics and the stable objective vocabulary are
reused directly from ``constitutional_architecture.governance`` (DRY); only the
candidate-isr -> design adapter is new here.
"""
from __future__ import annotations

from typing import Any

from constitutional_architecture.governance.governance_design_fitness import (
    GovernanceDesignFitness,
    design_objectives,
)
from constitutional_architecture.governance.governance_fitness import (
    ALL_OBJECTIVES,
)
from constitutional_architecture.governance.schemas import GovernanceDesignISR

from .fitness import FitnessEvaluator
from .models import (
    CandidateArchitecture,
    FitnessEvaluation,
    SimulationResult,
    VerificationReport,
)


def fail_closed_governance_objectives() -> dict[str, float]:
    """All six governance objectives at least-fit (0.0)."""
    return {name: 0.0 for name in ALL_OBJECTIVES}


def governance_objectives_for(
    isr: dict[str, Any],
    dimension: GovernanceDesignFitness | None = None,
) -> dict[str, float]:
    """Score a candidate's expressed governance design.

    Reuses the platform ``GovernanceDesignFitness`` heuristics (DRY). Absent,
    empty, or malformed ``isr["governance"]`` yields the fail-closed 0.0 vector
    so dimension-set consistency holds for every candidate.
    """
    design_dict = isr.get("governance") if isinstance(isr, dict) else None
    if not isinstance(design_dict, dict) or not design_dict:
        return fail_closed_governance_objectives()
    try:
        design = GovernanceDesignISR(**design_dict)
    except Exception:
        return fail_closed_governance_objectives()
    return design_objectives(design, dimension)


class GovernanceAwareFitnessEvaluator(FitnessEvaluator):
    """FitnessEvaluator that merges candidate-scoped governance dimensions.

    Wraps the base ``FitnessEvaluator``, projects the candidate's expressed
    ``GovernanceDesignISR`` into the six governance fitness objectives, and
    merges them into ``FitnessEvaluation.objectives``. ``FitnessEvaluator`` is a
    pure, stateless strategy (no ``__init__``), so subclassing composes cleanly.
    """

    def __init__(
        self,
        dimension: GovernanceDesignFitness | None = None,
    ) -> None:
        self._dimension = dimension or GovernanceDesignFitness()

    def evaluate(
        self,
        candidate: CandidateArchitecture,
        simulation: SimulationResult,
        verification: VerificationReport,
    ) -> FitnessEvaluation:
        base = super().evaluate(candidate, simulation, verification)
        governance = governance_objectives_for(candidate.isr, self._dimension)
        merged: dict[str, float] = dict(base.objectives)
        for name, value in governance.items():
            merged[name] = float(value)
        return base.model_copy(update={"objectives": merged})
