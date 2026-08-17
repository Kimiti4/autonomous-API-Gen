"""R2.10.3-J — evolution policy primitive (objectives and protected regions).

J answers two distinct questions:
  1. What is this evolution allowed to optimize?   -> EvolutionObjective
  2. What must this evolution never sacrifice?     -> ProtectedRegion

These are separate concepts and separate genes:

  EvolutionObjective = optimization preference (tradeable)
  ProtectedRegion    = constitutional constraint (NOT tradeable for fitness)

An objective may be traded against another objective. A protected region may
NOT be traded away for fitness. The enforcement boundary is a FEASIBILITY
gate (EvolutionProtectionEvaluator removes violating candidates from the
feasible search space before objective evaluation) — never a fitness
penalty, which a sufficiently large competing fitness could overwhelm.

Objective semantics:
  * objective != fitness. An objective declares WHAT matters; it never
    stores a measured value (structural field guard). The Evaluation Engine
    computes measurements against the objective later.
  * Lexicographic tiers, not weighted sums. ObjectiveTier separates the hard
    CONSTITUTIONAL gate (priority 0, subject-presence is a feasibility
    condition) from OPTIMIZATION preference; priority orders tiers; weight
    orders preferences within a tier. A weighted scalar such as
    ``0.7 * correctness + 0.3 * performance`` is structurally impossible
    here — no weight-arithmetic lives in the ISR.

ProtectedRegion semantics:
  * IMMUTABLE:    candidate_delta ∩ region != {}            -> INFEASIBLE
  * CONSTITUTIONAL: same, unless an external governance authorization
    (constitutional_architecture.governance) covers the change
  * PRESERVATION: change permitted iff every PreservationInvariant holds on
    the parent -> candidate semantic diff (ObligationKind predicates —
    one predicate model across the ISR, shared with F)

Protection is EXPLICITLY DECLARED, never inferred from source structure,
filenames, tests, framework metadata, deployment configuration, or
implementation conventions. J protects semantic identities by reference
(capabilities, requirements, boundaries, testing anchors, reliability
requirements, deployment intents, migrations, temporal constraints,
documentation, behaviors). E stays authoritative for boundaries, H for
anchors — J never re-implements their mechanics, and no ownership transfers.

Mechanism exclusion: optimizer/algorithm/fitness-function/selection
mechanics belong to the Evolution Engine, not the ISR.
EVOLUTION_MECHANISM_TERMS gates the canonical semantic form.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import TYPE_CHECKING, Any

from constitutional_architecture.isr.semantics.projection import canonical_form, canonicalize
from constitutional_architecture.isr.semantics.requirement import ObligationKind

if TYPE_CHECKING:
    from constitutional_architecture.isr.model.isr import ISR


class EvolutionPolicyValidationError(ValueError):
    """An evolution-policy declaration violates its contract."""


@unique
class ObjectiveDimension(str, Enum):
    """WHAT is being optimized — an extensible semantic vocabulary, never
    hard-coded optimizer behavior. The ISR declares the dimension; the
    Evolution Engine determines how it is measured."""

    CORRECTNESS = "CORRECTNESS"
    RELIABILITY = "RELIABILITY"
    PERFORMANCE = "PERFORMANCE"
    COMPLEXITY = "COMPLEXITY"
    COST = "COST"
    SECURITY = "SECURITY"
    MAINTAINABILITY = "MAINTAINABILITY"
    ADAPTABILITY = "ADAPTABILITY"


@unique
class ObjectiveDirection(str, Enum):
    MINIMIZE = "MINIMIZE"
    MAXIMIZE = "MAXIMIZE"


@unique
class ObjectiveTier(str, Enum):
    """Lexicographic structure of the objective stack.

    CONSTITUTIONAL (priority 0) is a HARD feasibility gate: the objective's
    subject_refs must remain present in any feasible candidate — the
    never-sacrifice guarantee closes the gap at the objective level, not
    only the region level. OPTIMIZATION is preference: tier order by
    priority, intra-tier preference by weight.
    """

    CONSTITUTIONAL = "CONSTITUTIONAL"
    OPTIMIZATION = "OPTIMIZATION"


@unique
class ProtectionKind(str, Enum):
    IMMUTABLE = "IMMUTABLE"
    CONSTITUTIONAL = "CONSTITUTIONAL"
    PRESERVATION = "PRESERVATION"


@dataclass(frozen=True)
class EvolutionObjective:
    """An optimization preference: WHAT matters, never a measured value.
    objective != fitness.

    Lexicographic: tier separates the hard gate from preference, priority
    orders tiers, weight orders within a tier. No weight-arithmetic lives in
    the ISR — a weighted scalar is structurally impossible here.
    """

    objective_id: str
    dimension: ObjectiveDimension
    direction: ObjectiveDirection
    tier: ObjectiveTier = ObjectiveTier.OPTIMIZATION
    priority: int = 0
    weight: float = 1.0
    subject_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.objective_id:
            raise EvolutionPolicyValidationError("objective_id is required")
        if self.tier is ObjectiveTier.CONSTITUTIONAL and self.priority != 0:
            raise EvolutionPolicyValidationError(
                "CONSTITUTIONAL objectives are priority 0 (the hard gate tier)"
            )
        if self.weight < 0.0:
            raise EvolutionPolicyValidationError("weight must be non-negative")


@dataclass(frozen=True)
class PreservationInvariant:
    """A preservation predicate reusing F's ObligationKind — one predicate
    model across the ISR. THRESHOLD is the only value-bearing kind (carries
    an explicit bound); the others are structural predicates over the
    parent -> candidate semantic diff."""

    kind: ObligationKind
    subject_refs: tuple[str, ...]
    statement: str
    bound: float | None = None

    def __post_init__(self) -> None:
        if not self.statement:
            raise EvolutionPolicyValidationError("statement is required")
        if self.kind is ObligationKind.THRESHOLD and self.bound is None:
            raise EvolutionPolicyValidationError(
                "THRESHOLD invariants require an explicit bound"
            )
        if self.kind is not ObligationKind.THRESHOLD and self.bound is not None:
            raise EvolutionPolicyValidationError(
                "only THRESHOLD invariants carry a bound"
            )


@dataclass(frozen=True)
class ProtectedRegion:
    """A non-tradeable constitutional constraint protecting semantic
    identities by reference.

    Never re-implements E's boundary or H's anchor mechanics — E stays
    authoritative for boundaries, H for anchors. The region declares that a
    semantic identity PARTICIPATES in the protected evolution policy.
    Protection is explicit: nothing is inferred from implementation.
    """

    region_id: str
    subject_refs: tuple[str, ...]
    protection_kind: ProtectionKind
    invariants: tuple[PreservationInvariant, ...] = ()

    def __post_init__(self) -> None:
        if not self.region_id:
            raise EvolutionPolicyValidationError("region_id is required")
        if not self.subject_refs:
            raise EvolutionPolicyValidationError(
                "subject_refs required: a region must protect something explicit"
            )
        if (
            self.protection_kind is ProtectionKind.PRESERVATION
            and not self.invariants
        ):
            raise EvolutionPolicyValidationError(
                "PRESERVATION requires at least one invariant"
            )
        if (
            self.protection_kind is not ProtectionKind.PRESERVATION
            and self.invariants
        ):
            raise EvolutionPolicyValidationError(
                "invariants apply only to PRESERVATION regions"
            )


@dataclass(frozen=True)
class EvolutionPolicy:
    """The evolution governance declaration: which objectives apply, which
    regions are protected, and semantic selection constraints.

    A policy must declare at least one objective or one protected region —
    governance that declares nothing is a degenerate artifact. Mechanics
    (optimizer, population, mutation, selection algorithms) are linted out:
    selection_constraints are SEMANTIC constraints, never engine
    configuration.
    """

    policy_id: str
    objective_refs: tuple[str, ...] = ()
    protected_region_refs: tuple[str, ...] = ()
    selection_constraints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise EvolutionPolicyValidationError("policy_id is required")


# -- mechanism lint (the dangerous boundary — no engine mechanics) ------------

EVOLUTION_MECHANISM_TERMS: frozenset[str] = frozenset({
    # optimizer / algorithm mechanics
    "optimizer", "algorithm", "fitness_function", "selection_algorithm",
    "mutation_rate", "population_size", "annealing", "tournament",
    "roulette", "genetic_algorithm", "pymoo", "nsga",
    "reinforcement_learning",
})


def evolution_mechanism_hits(policy: EvolutionPolicy) -> tuple[str, ...]:
    """Which engine-mechanism terms (if any) leaked into a policy's semantic form."""
    lowered = canonicalize(policy).lower()
    return tuple(term for term in EVOLUTION_MECHANISM_TERMS if term in lowered)


def assert_evolution_technology_agnostic(policy: EvolutionPolicy) -> None:
    """Gate: no optimizer/algorithm/fitness/selection mechanics may leak into
    the policy. ``maximize reliability`` passes; ``tournament selection with
    population_size 100`` fails. The ISR declares WHAT to optimize and WHAT
    cannot be sacrificed; the Evolution Engine determines HOW to search."""
    hits = evolution_mechanism_hits(policy)
    if hits:
        raise EvolutionPolicyValidationError(
            f"policy '{policy.policy_id}' couples to engine mechanism(s): {hits}"
        )


# -- structural validation (pre-execution) -----------------------------------

def _protected_gene_ids(system: Any) -> set[str]:
    """The evolution-policy identity space: every semantic identity J can
    protect by reference — capabilities, requirements, boundaries, testing
    anchors, reliability requirements, deployment intents, migrations,
    temporal constraints, documentation intents, and behaviors."""
    ids: set[str] = set()
    ids.update(c.capability_id for c in system.business_capabilities)
    ids.update(r.requirement_id for r in system.requirements)
    ids.update(b.boundary_id for b in system.architectural_boundaries)
    ids.update(a.anchor_id for a in system.testing_anchors)
    ids.update(r.requirement_id for r in system.reliability_requirements)
    ids.update(d.deployment_id for d in system.deployment_intents)
    ids.update(d.documentation_id for d in system.documentation_intents)
    for module in system.modules:
        ids.update(m.migration_id for m in module.data_migrations)
        ids.update(t.constraint_id for t in module.temporal_constraints)
        ids.update(w.id for w in module.workflows)
    return ids


def validate_system_evolution_policy_constraints(system: Any) -> tuple[str, ...]:
    """Structural validation for one system's evolution policy carriers.

    Rejects, pre-execution: duplicate ids (objectives / regions / policies),
    dangling policy refs, dangling subject refs (objectives, regions,
    invariants), and policies that govern nothing. Empty tuple means valid.
    """
    errors: list[str] = []
    protected_ids = _protected_gene_ids(system)
    objective_ids = {o.objective_id for o in system.evolution_objectives}
    region_ids = {r.region_id for r in system.protected_regions}
    seen_objectives: set[str] = set()
    seen_regions: set[str] = set()
    seen_policies: set[str] = set()
    for objective in system.evolution_objectives:
        if objective.objective_id in seen_objectives:
            errors.append(f"duplicate objective id '{objective.objective_id}'")
        seen_objectives.add(objective.objective_id)
        for subject_ref in objective.subject_refs:
            if subject_ref not in protected_ids:
                errors.append(
                    f"objective '{objective.objective_id}' references unknown "
                    f"gene '{subject_ref}'"
                )
    for region in system.protected_regions:
        if region.region_id in seen_regions:
            errors.append(f"duplicate region id '{region.region_id}'")
        seen_regions.add(region.region_id)
        for subject_ref in region.subject_refs:
            if subject_ref not in protected_ids:
                errors.append(
                    f"region '{region.region_id}' protects unknown gene "
                    f"'{subject_ref}'"
                )
        for invariant in region.invariants:
            for subject_ref in invariant.subject_refs:
                if subject_ref not in protected_ids:
                    errors.append(
                        f"region '{region.region_id}' invariant references "
                        f"unknown gene '{subject_ref}'"
                    )
    for policy in system.evolution_policies:
        if policy.policy_id in seen_policies:
            errors.append(f"duplicate policy id '{policy.policy_id}'")
        seen_policies.add(policy.policy_id)
        if not policy.objective_refs and not policy.protected_region_refs:
            errors.append(
                f"policy '{policy.policy_id}' governs nothing: no objective "
                f"or protected region referenced"
            )
        for objective_ref in policy.objective_refs:
            if objective_ref not in objective_ids:
                errors.append(
                    f"policy '{policy.policy_id}' references unknown "
                    f"objective '{objective_ref}'"
                )
        for region_ref in policy.protected_region_refs:
            if region_ref not in region_ids:
                errors.append(
                    f"policy '{policy.policy_id}' references unknown "
                    f"protected region '{region_ref}'"
                )
    return tuple(errors)


# -- projection (semantics only, never a scalar) ------------------------------

def project_evolution_policy(isr: Any) -> dict[str, Any]:
    """Backend-independent semantic projection of the evolution policy.

    Returns PER-OBJECTIVE declarations (dimension, direction, tier,
    priority, weight, subjects) and PER-REGION declarations (kind,
    invariants, subjects). There is deliberately NO combined artifact: no
    weighted scalar, no aggregate fitness, no scalarization of any kind.
    Objectives stay lexicographic; the Evolution Engine may compile them
    into Pareto or weighted selection strategies downstream.
    """
    return {
        "objectives": tuple(
            canonical_form(o) for o in getattr(isr.system, "evolution_objectives", ())
        ),
        "protected_regions": tuple(
            canonical_form(r) for r in getattr(isr.system, "protected_regions", ())
        ),
        "policies": tuple(
            canonical_form(p) for p in getattr(isr.system, "evolution_policies", ())
        ),
    }


_SCALAR_KEYS = ("fitness", "scalar", "aggregate", "combined", "weighted_total")


def evolution_policy_has_no_scalar_aggregation(projection: dict[str, Any]) -> bool:
    """The no-scalarization guard: the projection contains per-objective
    declarations only — no key that could hold a combined objective artifact,
    and no sum/mean over weights anywhere in the projected structure."""
    text = str(projection).lower()
    if any(key in text for key in _SCALAR_KEYS):
        return False
    weights = [
        o.get("weight")
        for o in projection.get("objectives", ())
        if isinstance(o, dict)
    ]
    if weights and len(weights) > 1:
        import math

        if math.isclose(sum(w for w in weights if isinstance(w, (int, float))), 1.0):
            return False  # a normalized weighting scheme is scalarization
    return True