"""R2.10.2 — ISR Primitive Design & Dependency Ordering (contract suite).

Design-and-contract slice: specifies the ten MISSING primitives, derives
their dependency graph mechanically, defines the ISR extension contract and
the compatibility contract, and assigns each primitive an evolution-readiness
progression. NO ISR schema changes here — the primitives land in R2.10.3+.

Artifacts produced:

  1. Primitive specification   — ten fields per primitive (meaning, ownership,
     dependencies, constraints, mutation/validation/compiler/evidence
     projections, lineage requirements) + intended type signatures.
  2. Dependency graph          — derived mechanically from the declared
     reference categories (structural / mutation / validation / projection),
     asserted acyclic, topologically sorted.
  3. ISR extension contract    — rules every new primitive must satisfy
     (projection rule, probe rule, locality rule, tech-agnostic rule).
  4. Compatibility contract    — old ISR -> same semantic hash -> same
     artifact -> same evolution behavior (Option A: omit-empty projection,
     so empty optional primitives are hash-neutral).
  5. Evolution-readiness matrix — MISSING -> REPRESENTED -> VALIDATED ->
     MUTATABLE -> COMPILABLE -> OBSERVABLE -> LINEAGE_TRACKED -> EXPRESSED,
     with EXPRESSED gated on the R2.10.1 mutation-locality proof.

The contract is attested and chain-anchored in the ledger as a
``PRIMITIVE_CONTRACT`` event (R2.8.14 certification pattern), like the
R2.10.1 capability matrix.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any, Mapping, Sequence

from constitutional_architecture.isr.semantics.projection import canonicalize

from .ledger import EventType, EvolutionEvent, EvolutionLedger


# -- 1. technology-agnostic lint (Refinement 2) --------------------------------

TECHNOLOGY_COUPLING_TERMS: frozenset[str] = frozenset({
    # frameworks
    "fastapi", "spring", "django", "flask", "phoenix", "nest", "axum", "fiber",
    "react", "vue", "angular", "flutter",
    # datastores
    "postgres", "postgresql", "mysql", "mongo", "mongodb", "redis", "neo4j",
    "sqlite", "elasticsearch", "alembic", "sqlalchemy",
    # messaging
    "kafka", "rabbitmq", "nats", "sqs", "kinesis", "celery",
    # infrastructure
    "docker", "kubernetes", "k8s", "terraform", "pulumi", "nomad",
    "gunicorn", "uvicorn", "nginx", "s3",
    # security mechanisms (intent, not mechanism)
    "oauth", "oidc", "jwt",
    # observability vendors
    "prometheus", "grafana", "datadog",
})


class TechnologyCouplingError(ValueError):
    """A primitive field or specification couples the ISR to a technology."""


def _text_surfaces(spec: "PrimitiveSpec") -> tuple[str, ...]:
    surfaces: list[str] = [
        spec.semantic_meaning,
        spec.ownership,
        spec.primitive_id,
    ]
    for attr in (
        "constraints", "mutation_surface", "validation_surface",
        "compiler_projection", "evidence_projection", "lineage_requirements",
    ):
        surfaces.extend(getattr(spec, attr))
    for name, signature in spec.type_signature.items():
        surfaces.append(name)
        surfaces.append(signature)
    return tuple(surfaces)


def assert_technology_agnostic(spec: "PrimitiveSpec") -> None:
    """A primitive may express INTENT, never a specific technology.

    'persistence_semantics' is valid; 'postgresql_config' is not.
    'deployment_intent' is valid; 'kubernetes_manifest' is not.
    'authentication_requirement' is valid; 'jwt_scheme' is not.
    """
    for surface in _text_surfaces(spec):
        lowered = surface.lower()
        hit = next((t for t in TECHNOLOGY_COUPLING_TERMS if t in lowered), None)
        if hit is not None:
            raise TechnologyCouplingError(
                f"{spec.primitive_id} couples to '{hit}' in: {surface!r}"
            )


# -- 2. readiness progression (Refinement 3) ------------------------------------

@unique
class ReadinessStage(str, Enum):
    MISSING = "missing"
    REPRESENTED = "represented"
    VALIDATED = "validated"
    MUTATABLE = "mutatable"
    COMPILABLE = "compilable"
    OBSERVABLE = "observable"
    LINEAGE_TRACKED = "lineage_tracked"
    EXPRESSED = "expressed"


READINESS_ORDER: tuple[ReadinessStage, ...] = (
    ReadinessStage.MISSING,
    ReadinessStage.REPRESENTED,
    ReadinessStage.VALIDATED,
    ReadinessStage.MUTATABLE,
    ReadinessStage.COMPILABLE,
    ReadinessStage.OBSERVABLE,
    ReadinessStage.LINEAGE_TRACKED,
    ReadinessStage.EXPRESSED,
)


# -- 3. primitive specification ---------------------------------------------------

@dataclass(frozen=True)
class PrimitiveSpec:
    """Full specification of one MISSING ISR primitive (ten required fields)."""

    primitive_id: str
    capability_id: str                     # the R2.10.1 MISSING row it closes
    semantic_meaning: str                  # what the primitive MEANS (intent)
    ownership: str                         # where it lives (system/module scope)
    dependencies: tuple[str, ...]          # declared primitive dependencies
    constraints: tuple[str, ...]           # invariants the primitive must satisfy
    mutation_surface: tuple[str, ...]      # intended gene paths / operators
    validation_surface: tuple[str, ...]    # intended pre-execution checks
    compiler_projection: tuple[str, ...]   # intended technology-neutral lowering
    evidence_projection: tuple[str, ...]   # intended evidence/observability mapping
    lineage_requirements: tuple[str, ...]  # ledger/attribution requirements

    # -- mechanical derivation inputs ------------------------------------------
    type_signature: dict[str, str] = field(default_factory=dict)
    type_references: tuple[str, ...] = ()       # structural edges (type -> type)
    mutation_requires: tuple[str, ...] = ()     # mutation edges (needs gene present)
    validation_references: tuple[str, ...] = ()  # validation edges (checks other primitive)
    projection_requires: tuple[str, ...] = ()   # projection edges (derives from other)
    readiness_targets: dict[ReadinessStage, tuple[str, ...]] = field(default_factory=dict)
    locality_required: bool = True              # EXPRESSED requires R2.10.1 locality proof

    @property
    def derived_dependencies(self) -> frozenset[str]:
        edges = set(self.dependencies)
        edges |= set(self.type_references)
        edges |= set(self.mutation_requires)
        edges |= set(self.validation_references)
        edges |= set(self.projection_requires)
        edges.discard(self.primitive_id)
        return frozenset(edges)


# -- the ten MISSING primitives ---------------------------------------------------

PRIMITIVES: tuple[PrimitiveSpec, ...] = (
    PrimitiveSpec(
        primitive_id="business_capabilities",
        capability_id="business_capabilities",
        semantic_meaning="Declarations of the business capabilities the system realizes, and which modules realize each.",
        ownership="system scope (cross-module registry)",
        dependencies=(),
        constraints=(
            "capability ids are unique",
            "realized_by references existing module ids",
            "a capability may be realized by one or more modules",
        ),
        mutation_surface=(
            "system.capabilities[*] (add/remove/rename capability gene)",
            "system.capabilities[*].realized_by (re-point realization)",
        ),
        validation_surface=(
            "realized_by targets must exist among system.modules",
            "duplicate capability ids rejected pre-execution",
        ),
        compiler_projection=(
            "capability -> module realization map (no technology terms)",
        ),
        evidence_projection=(
            "capability ids in acceptance/verification evidence",
        ),
        lineage_requirements=(
            "capability gene mutations operator-attributed in MEASUREMENT events",
        ),
        type_signature={
            "capabilities": "tuple[BusinessCapability{id, name, description, realized_by: module_ids}]",
        },
        type_references=(),
        mutation_requires=(),
        validation_references=(),
        projection_requires=(),
        readiness_targets={
            ReadinessStage.REPRESENTED: ("ISR carrier: system.capabilities",),
            ReadinessStage.VALIDATED: ("realized_by existence check in validator",),
            ReadinessStage.MUTATABLE: ("gene-level operators for capability registry",),
            ReadinessStage.COMPILABLE: ("capability registry projected into generated docs/skeleton",),
            ReadinessStage.OBSERVABLE: ("capability realization observable in artifact structure",),
            ReadinessStage.LINEAGE_TRACKED: ("capability gene mutations in ledger with attribution",),
            ReadinessStage.EXPRESSED: ("all six audit dimensions true + mutation-locality proof",),
        },
    ),
    PrimitiveSpec(
        primitive_id="requirements_acceptance_traceability",
        capability_id="requirements_acceptance_traceability",
        semantic_meaning="Requirement references, acceptance criteria, and trace links from requirements to the capabilities they realize.",
        ownership="system scope (requirement registry)",
        dependencies=("business_capabilities",),
        constraints=(
            "requirement refs are unique",
            "capability_ref targets must exist in business_capabilities",
            "acceptance criteria attach to exactly one requirement ref",
        ),
        mutation_surface=(
            "system.requirement_refs[*] (add/remove requirement gene)",
            "system.acceptance_criteria[*] (add/edit criterion gene)",
            "trace links re-point capability_ref",
        ),
        validation_surface=(
            "capability_ref existence validated pre-execution",
            "criteria verifiable_by must name an anchored verification surface",
        ),
        compiler_projection=(
            "requirement -> capability trace table (no technology terms)",
        ),
        evidence_projection=(
            "acceptance criteria linked to verification evidence records",
        ),
        lineage_requirements=(
            "trace-link changes attributed and chain-anchored",
        ),
        type_signature={
            "requirement_refs": "tuple[RequirementRef{id, capability_ref, source, priority}]",
            "acceptance_criteria": "tuple[AcceptanceCriterion{id, requirement_ref, verifiable_by}]",
        },
        type_references=("business_capabilities",),
        mutation_requires=(),
        validation_references=("business_capabilities",),
        projection_requires=("business_capabilities",),
        readiness_targets={
            ReadinessStage.REPRESENTED: ("ISR carrier: system.requirement_refs / acceptance_criteria",),
            ReadinessStage.VALIDATED: ("capability_ref + verifiable_by existence checks",),
            ReadinessStage.MUTATABLE: ("gene-level operators for requirement/criterion registry",),
            ReadinessStage.COMPILABLE: ("trace table lowered into generated documentation",),
            ReadinessStage.OBSERVABLE: ("acceptance criteria observable against evidence",),
            ReadinessStage.LINEAGE_TRACKED: ("trace-link mutations attributed in ledger",),
            ReadinessStage.EXPRESSED: ("all six audit dimensions true + mutation-locality proof",),
        },
    ),
    PrimitiveSpec(
        primitive_id="architecture_boundaries",
        capability_id="architecture_boundaries",
        semantic_meaning="Dependency direction, layering, and coupling limits between modules — the enforceable boundary model.",
        ownership="system scope (boundary rule registry)",
        dependencies=("business_capabilities",),
        constraints=(
            "boundary scope references an existing module or capability",
            "direction enum: inward/outward/peer",
            "coupling_limit is a non-negative integer",
            "boundary rules are technology-neutral (no backend terms)",
        ),
        mutation_surface=(
            "system.boundary_rules[*] (add/remove rule gene)",
            "system.boundary_rules[*].allowed_targets (re-point gene)",
            "system.boundary_rules[*].coupling_limit (numeric gene)",
        ),
        validation_surface=(
            "scope + allowed_targets existence validated pre-execution",
            "direction is a closed enum (invalid values rejected)",
            "boundary violations rejected before compilation",
        ),
        compiler_projection=(
            "boundary rules projected into dependency-direction lint (no technology terms)",
        ),
        evidence_projection=(
            "boundary checks reported as verification evidence",
        ),
        lineage_requirements=(
            "boundary rule mutations operator-attributed and chain-anchored",
        ),
        type_signature={
            "boundary_rules": "tuple[BoundaryRule{scope, direction, allowed_targets, coupling_limit, capability_scope}]",
        },
        type_references=("business_capabilities",),
        mutation_requires=("business_capabilities",),
        validation_references=(),
        projection_requires=(),
        readiness_targets={
            ReadinessStage.REPRESENTED: ("ISR carrier: system.boundary_rules",),
            ReadinessStage.VALIDATED: ("scope/target existence + direction enum checks",),
            ReadinessStage.MUTATABLE: ("gene-level operators for boundary rules",),
            ReadinessStage.COMPILABLE: ("boundary lint lowered from ISR rules",),
            ReadinessStage.OBSERVABLE: ("violations observable in verification output",),
            ReadinessStage.LINEAGE_TRACKED: ("boundary mutations attributed in ledger",),
            ReadinessStage.EXPRESSED: ("all six audit dimensions true + mutation-locality proof",),
        },
    ),
    PrimitiveSpec(
        primitive_id="behavior_temporal_semantics",
        capability_id="behavior_temporal_semantics",
        semantic_meaning="Retry, timeout, and backoff semantics for operations and workflow transitions.",
        ownership="module scope (per operation / per transition)",
        dependencies=(),
        constraints=(
            "max_attempts is a positive integer",
            "backoff semantics is a closed vocabulary (fixed/exponential/jittered)",
            "timeout semantics applies to an existing operation or transition",
        ),
        mutation_surface=(
            "operation.retry_policy[*] (add/edit policy gene)",
            "transition.timeout_policy[*] (add/edit policy gene)",
        ),
        validation_surface=(
            "max_attempts bounds validated pre-execution",
            "target operation/transition existence validated",
        ),
        compiler_projection=(
            "retry/timeout semantics lowered as generic execution semantics (no scheduler/queue names)",
        ),
        evidence_projection=(
            "retry/timeout behavior observable in execution evidence",
        ),
        lineage_requirements=(
            "policy mutations operator-attributed and chain-anchored",
        ),
        type_signature={
            "retry_policies": "tuple[RetryPolicy{max_attempts, backoff_semantics}]",
            "timeout_policies": "tuple[TimeoutPolicy{duration_semantics}]",
        },
        type_references=(),
        mutation_requires=(),
        validation_references=(),
        projection_requires=(),
        readiness_targets={
            ReadinessStage.REPRESENTED: ("ISR carriers: operation.retry_policy / transition.timeout_policy",),
            ReadinessStage.VALIDATED: ("bounds + target existence checks",),
            ReadinessStage.MUTATABLE: ("gene-level operators for temporal policies",),
            ReadinessStage.COMPILABLE: ("temporal semantics lowered as generic execution semantics",),
            ReadinessStage.OBSERVABLE: ("retry/timeout behavior in execution evidence",),
            ReadinessStage.LINEAGE_TRACKED: ("policy mutations attributed in ledger",),
            ReadinessStage.EXPRESSED: ("all six audit dimensions true + mutation-locality proof",),
        },
    ),
    PrimitiveSpec(
        primitive_id="data_migrations",
        capability_id="data_migrations",
        semantic_meaning="Schema migration semantics: versioned transitions of the data model with reversibility.",
        ownership="system scope (migration registry)",
        dependencies=(),
        constraints=(
            "migration versions are unique and monotonic",
            "semantic_effect describes intent, not implementation",
            "reversible migrations declare an inverse semantics",
        ),
        mutation_surface=(
            "system.migrations[*] (add/remove migration gene)",
            "system.migrations[*].semantic_effect (edit gene)",
            "system.migrations[*].reversible (flip gene)",
        ),
        validation_surface=(
            "version monotonicity validated pre-execution",
            "reversibility contract validated (inverse declared when reversible)",
        ),
        compiler_projection=(
            "migration intent lowered as generic schema-version semantics (no migration-framework names)",
        ),
        evidence_projection=(
            "migration application/reversal observable in deployment evidence",
        ),
        lineage_requirements=(
            "migration gene mutations operator-attributed and chain-anchored",
        ),
        type_signature={
            "migrations": "tuple[DataMigration{from_version, to_version, semantic_effect, reversible}]",
        },
        type_references=(),
        mutation_requires=(),
        validation_references=(),
        projection_requires=(),
        readiness_targets={
            ReadinessStage.REPRESENTED: ("ISR carrier: system.migrations",),
            ReadinessStage.VALIDATED: ("version monotonicity + reversibility checks",),
            ReadinessStage.MUTATABLE: ("gene-level operators for migration registry",),
            ReadinessStage.COMPILABLE: ("migration intent lowered as generic schema-version semantics",),
            ReadinessStage.OBSERVABLE: ("migration application observable in deployment evidence",),
            ReadinessStage.LINEAGE_TRACKED: ("migration mutations attributed in ledger",),
            ReadinessStage.EXPRESSED: ("all six audit dimensions true + mutation-locality proof",),
        },
    ),
    PrimitiveSpec(
        primitive_id="reliability_resilience",
        capability_id="reliability_resilience",
        semantic_meaning="Fallback and degradation semantics for services — what happens when a dependency fails.",
        ownership="module scope (per service)",
        dependencies=("behavior_temporal_semantics",),
        constraints=(
            "fallback policy references an existing service or operation",
            "circuit-breaker window semantics reference temporal semantics",
            "degradation policy declares intent, not implementation",
        ),
        mutation_surface=(
            "service.fallback_policies[*] (add/edit policy gene)",
            "service.circuit_breaker_policies[*] (add/edit policy gene)",
        ),
        validation_surface=(
            "fallback target existence validated pre-execution",
            "window semantics validated against temporal vocabulary",
        ),
        compiler_projection=(
            "fallback/degradation intent lowered as generic resilience semantics (no client-library names)",
        ),
        evidence_projection=(
            "fallback activations observable in execution evidence",
        ),
        lineage_requirements=(
            "resilience policy mutations operator-attributed and chain-anchored",
        ),
        type_signature={
            "fallback_policies": "tuple[FallbackPolicy{degradation_semantics}]",
            "circuit_breaker_policies": "tuple[CircuitBreakerPolicy{window_semantics}]",
        },
        type_references=("behavior_temporal_semantics",),
        mutation_requires=(),
        validation_references=("behavior_temporal_semantics",),
        projection_requires=(),
        readiness_targets={
            ReadinessStage.REPRESENTED: ("ISR carriers: service.fallback_policies / circuit_breaker_policies",),
            ReadinessStage.VALIDATED: ("fallback target + window semantics checks",),
            ReadinessStage.MUTATABLE: ("gene-level operators for resilience policies",),
            ReadinessStage.COMPILABLE: ("resilience intent lowered as generic semantics",),
            ReadinessStage.OBSERVABLE: ("fallback activations in execution evidence",),
            ReadinessStage.LINEAGE_TRACKED: ("resilience mutations attributed in ledger",),
            ReadinessStage.EXPRESSED: ("all six audit dimensions true + mutation-locality proof",),
        },
    ),
    PrimitiveSpec(
        primitive_id="deployment_rollout_rollback",
        capability_id="deployment_rollout_rollback",
        semantic_meaning="Rollout and rollback semantics: promotion stages and reversal triggers — intent, not infrastructure.",
        ownership="system scope (deployment semantics registry)",
        dependencies=("data_migrations", "reliability_resilience"),
        constraints=(
            "rollout strategy is a closed vocabulary (canary/blue_green/gradual)",
            "rollback plans name a trigger semantic and a reversal target",
            "promotion stages are ordered",
        ),
        mutation_surface=(
            "system.rollout_strategies[*] (add/edit strategy gene)",
            "system.rollback_plans[*] (add/edit plan gene)",
        ),
        validation_surface=(
            "rollback trigger references an existing reliability or migration semantic",
            "promotion order validated pre-execution",
        ),
        compiler_projection=(
            "rollout/rollback intent lowered as generic promotion semantics (no orchestration-tool names)",
        ),
        evidence_projection=(
            "rollout stages and rollback activations observable in deployment evidence",
        ),
        lineage_requirements=(
            "rollout/rollback gene mutations operator-attributed and chain-anchored",
        ),
        type_signature={
            "rollout_strategies": "tuple[RolloutStrategy{promotion_semantics}]",
            "rollback_plans": "tuple[RollbackPlan{trigger_semantics, reversal_target}]",
        },
        type_references=("data_migrations", "reliability_resilience"),
        mutation_requires=(),
        validation_references=("data_migrations", "reliability_resilience"),
        projection_requires=(),
        readiness_targets={
            ReadinessStage.REPRESENTED: ("ISR carriers: system.rollout_strategies / rollback_plans",),
            ReadinessStage.VALIDATED: ("promotion order + trigger reference checks",),
            ReadinessStage.MUTATABLE: ("gene-level operators for rollout/rollback registry",),
            ReadinessStage.COMPILABLE: ("promotion intent lowered as generic semantics",),
            ReadinessStage.OBSERVABLE: ("rollout/rollback observable in deployment evidence",),
            ReadinessStage.LINEAGE_TRACKED: ("rollout mutations attributed in ledger",),
            ReadinessStage.EXPRESSED: ("all six audit dimensions true + mutation-locality proof",),
        },
    ),
    PrimitiveSpec(
        primitive_id="testing_anchoring",
        capability_id="testing_anchoring",
        semantic_meaning="Protected and holdout test sets anchored to ISR genes — the evaluation surface the boundary enforces.",
        ownership="system scope (anchor registry)",
        dependencies=("requirements_acceptance_traceability",),
        constraints=(
            "anchor targets reference existing ISR genes",
            "holdout selection rules are deterministic",
            "anchors declare an intent contract, not a test framework",
        ),
        mutation_surface=(
            "system.protected_test_sets[*] (add/remove anchor gene)",
            "system.holdout_sets[*] (add/edit selection rule gene)",
        ),
        validation_surface=(
            "anchor target existence validated pre-execution",
            "holdout rules validated as deterministic",
        ),
        compiler_projection=(
            "anchoring intent lowered as generic verification-surface semantics (no test-runner names)",
        ),
        evidence_projection=(
            "anchor integrity reported in verification evidence",
        ),
        lineage_requirements=(
            "anchor mutations operator-attributed and chain-anchored",
        ),
        type_signature={
            "protected_test_sets": "tuple[ProtectedTestSet{anchor_contract}]",
            "holdout_sets": "tuple[HoldoutSet{selection_rule}]",
        },
        type_references=("requirements_acceptance_traceability",),
        mutation_requires=(),
        validation_references=("requirements_acceptance_traceability",),
        projection_requires=(),
        readiness_targets={
            ReadinessStage.REPRESENTED: ("ISR carriers: system.protected_test_sets / holdout_sets",),
            ReadinessStage.VALIDATED: ("anchor target + determinism checks",),
            ReadinessStage.MUTATABLE: ("gene-level operators for anchor registry",),
            ReadinessStage.COMPILABLE: ("anchoring lowered as generic verification semantics",),
            ReadinessStage.OBSERVABLE: ("anchor integrity in verification evidence",),
            ReadinessStage.LINEAGE_TRACKED: ("anchor mutations attributed in ledger",),
            ReadinessStage.EXPRESSED: ("all six audit dimensions true + mutation-locality proof",),
        },
    ),
    PrimitiveSpec(
        primitive_id="documentation",
        capability_id="documentation",
        semantic_meaning="Documentation intent: which sections exist and what they derive from.",
        ownership="system scope (documentation registry)",
        dependencies=(
            "business_capabilities", "requirements_acceptance_traceability",
            "architecture_boundaries", "data_migrations",
            "behavior_temporal_semantics", "reliability_resilience",
            "testing_anchoring", "deployment_rollout_rollback",
        ),
        constraints=(
            "each section declares derived_from targets among ISR genes",
            "sections express intent, not prose templates",
        ),
        mutation_surface=(
            "system.documentation_sections[*] (add/remove section gene)",
            "system.documentation_sections[*].derived_from (re-point gene)",
        ),
        validation_surface=(
            "derived_from targets must exist pre-execution",
        ),
        compiler_projection=(
            "documentation intent lowered as generated documentation (no template names)",
        ),
        evidence_projection=(
            "section coverage reported in documentation evidence",
        ),
        lineage_requirements=(
            "documentation gene mutations operator-attributed and chain-anchored",
        ),
        type_signature={
            "documentation_sections": "tuple[DocumentationSection{derived_from, format_semantics}]",
        },
        type_references=(
            "business_capabilities", "requirements_acceptance_traceability",
            "architecture_boundaries", "data_migrations",
            "behavior_temporal_semantics", "reliability_resilience",
            "testing_anchoring", "deployment_rollout_rollback",
        ),
        mutation_requires=(),
        validation_references=(),
        projection_requires=("business_capabilities",),
        readiness_targets={
            ReadinessStage.REPRESENTED: ("ISR carrier: system.documentation_sections",),
            ReadinessStage.VALIDATED: ("derived_from existence checks",),
            ReadinessStage.MUTATABLE: ("gene-level operators for documentation registry",),
            ReadinessStage.COMPILABLE: ("documentation intent lowered from ISR genes",),
            ReadinessStage.OBSERVABLE: ("section coverage in documentation evidence",),
            ReadinessStage.LINEAGE_TRACKED: ("documentation mutations attributed in ledger",),
            ReadinessStage.EXPRESSED: ("all six audit dimensions true + mutation-locality proof",),
        },
    ),
    PrimitiveSpec(
        primitive_id="evolution_objectives_protected_regions",
        capability_id="evolution_objectives_protected_regions",
        semantic_meaning="Evolution objectives and protected regions: what the engine may change, what it must not, and toward what.",
        ownership="system scope (evolution contract registry)",
        dependencies=(
            "business_capabilities", "requirements_acceptance_traceability",
            "architecture_boundaries", "behavior_temporal_semantics",
            "data_migrations", "reliability_resilience",
            "deployment_rollout_rollback", "testing_anchoring", "documentation",
        ),
        constraints=(
            "objective targets reference existing genes",
            "protected regions reference genes that must exist (depend on all primitives)",
            "objectives connect to the R2.8 authorization model",
        ),
        mutation_surface=(
            "system.objectives[*] (add/edit objective gene)",
            "system.protected_regions[*] (add/remove region gene)",
        ),
        validation_surface=(
            "target gene paths validated against the gene index pre-execution",
            "objectives validated against the authorization model",
        ),
        compiler_projection=(
            "objectives/protected regions projected as engine constraints (never into artifacts)",
        ),
        evidence_projection=(
            "objective progress reported in evolution evidence",
        ),
        lineage_requirements=(
            "objective/region mutations operator-attributed and chain-anchored",
        ),
        type_signature={
            "objectives": "tuple[EvolutionObjective{target_gene_paths, direction}]",
            "protected_regions": "tuple[ProtectedRegion{gene_paths, grant, policy_ref}]",
        },
        type_references=(
            "business_capabilities", "requirements_acceptance_traceability",
            "architecture_boundaries", "behavior_temporal_semantics",
            "data_migrations", "reliability_resilience",
            "deployment_rollout_rollback", "testing_anchoring", "documentation",
        ),
        mutation_requires=(
            "business_capabilities", "requirements_acceptance_traceability",
            "architecture_boundaries", "behavior_temporal_semantics",
            "data_migrations", "reliability_resilience",
            "deployment_rollout_rollback", "testing_anchoring", "documentation",
        ),
        validation_references=(),
        projection_requires=(),
        readiness_targets={
            ReadinessStage.REPRESENTED: ("ISR carriers: system.objectives / protected_regions",),
            ReadinessStage.VALIDATED: ("target gene-path existence + authorization checks",),
            ReadinessStage.MUTATABLE: ("gene-level operators for objective/region registry",),
            ReadinessStage.COMPILABLE: ("objectives projected as engine constraints (never artifacts)",),
            ReadinessStage.OBSERVABLE: ("objective progress in evolution evidence",),
            ReadinessStage.LINEAGE_TRACKED: ("objective mutations attributed in ledger",),
            ReadinessStage.EXPRESSED: ("all six audit dimensions true + mutation-locality proof",),
        },
    ),
)

PRIMITIVE_BY_ID: dict[str, PrimitiveSpec] = {p.primitive_id: p for p in PRIMITIVES}


# -- 4. dependency graph (mechanical derivation, Refinement 1) -------------------

def derive_dependency_graph(
    specs: Sequence[PrimitiveSpec] = PRIMITIVES,
) -> dict[str, frozenset[str]]:
    """Directed edges: A depends on B iff any declared category references B.

    Categories: declared ``dependencies``, structural ``type_references``,
    ``mutation_requires``, ``validation_references``, ``projection_requires``.
    """
    graph: dict[str, frozenset[str]] = {}
    known = {s.primitive_id for s in specs}
    for spec in specs:
        edges = spec.derived_dependencies
        unknown = edges - known
        if unknown:
            raise ValueError(
                f"{spec.primitive_id} references unknown primitive(s): {sorted(unknown)}"
            )
        graph[spec.primitive_id] = edges
    return graph


def assert_acyclic(graph: Mapping[str, frozenset[str]]) -> tuple[str, ...]:
    """DFS cycle detection; returns a valid topological order (Kahn)."""
    visited: dict[str, int] = {}  # 0=visiting, 1=done

    def visit(node: str) -> None:
        state = visited.get(node, -1)
        if state == 0:
            raise ValueError(f"dependency cycle detected involving {node}")
        if state == 1:
            return
        visited[node] = 0
        for dep in sorted(graph.get(node, ())):
            visit(dep)
        visited[node] = 1

    for node in sorted(graph):
        visit(node)
    order: list[str] = []
    indegree = {n: len(graph.get(n, ())) for n in graph}
    ready = sorted(n for n, d in indegree.items() if d == 0)
    while ready:
        node = ready.pop(0)
        order.append(node)
        for n in sorted(graph):
            if node in graph.get(n, ()):
                indegree[n] -= 1
                if indegree[n] == 0:
                    ready.append(n)
    if len(order) != len(graph):
        raise ValueError("topological sort incomplete: cycle present")
    return tuple(order)


def derived_implementation_order(graph: Mapping[str, frozenset[str]] | None = None) -> tuple[str, ...]:
    graph = graph or derive_dependency_graph()
    return assert_acyclic(graph)


# -- 5. extension contract ---------------------------------------------------------

EXTENSION_CONTRACT: tuple[str, ...] = (
    "projection rule (Option A): every new primitive MUST be canonicalizable by "
    "semantic_content_hash; empty optional carriers are hash-neutral, non-empty "
    "carriers are hash-sensitive (change-detection preserved)",
    "probe rule: every new primitive MUST gain a capability probe and gene_index "
    "entries in the R2.10.1 audit before it may be classified beyond MISSING",
    "locality rule: a primitive is EXPRESSED only after its mutation-locality "
    "proof holds (mutating its gene changes no other gene's semantic hash)",
    "tech-agnostic rule: every new primitive MUST pass assert_technology_agnostic "
    "(intent, never technology)",
    "compatibility rule: old ISRs keep the same semantic hash (post-migration "
    "recomputation), the same compiler artifact, and the same evolution behavior",
    "readiness rule: every primitive MUST declare readiness_targets for all "
    "stages of READINESS_ORDER before implementation begins",
)


# -- 6. readiness matrix -------------------------------------------------------------

def readiness_matrix() -> dict[str, dict[ReadinessStage, tuple[str, ...]]]:
    return {p.primitive_id: dict(p.readiness_targets) for p in PRIMITIVES}


def assert_readiness_complete() -> None:
    """Every primitive declares non-empty targets for every stage, in order."""
    for spec in PRIMITIVES:
        for stage in READINESS_ORDER:
            if stage is ReadinessStage.MISSING:
                continue
            targets = spec.readiness_targets.get(stage, ())
            if not targets:
                raise ValueError(f"{spec.primitive_id} lacks readiness targets for {stage.value}")
        expressed = spec.readiness_targets.get(ReadinessStage.EXPRESSED, ())
        if spec.locality_required and not any("locality" in t for t in expressed):
            raise ValueError(f"{spec.primitive_id} EXPRESSED stage does not require locality proof")


# -- 7. contract validation + ledger attestation ----------------------------------------

@dataclass(frozen=True)
class PrimitiveContract:
    """The attested R2.10.2 contract suite (five artifacts in one record)."""

    primitives: tuple[PrimitiveSpec, ...] = PRIMITIVES
    extension_contract: tuple[str, ...] = EXTENSION_CONTRACT
    technology_coupling_terms: frozenset[str] = TECHNOLOGY_COUPLING_TERMS

    def validate(self) -> None:
        known = {p.primitive_id for p in self.primitives}
        if len(known) != len(self.primitives):
            raise ValueError("duplicate primitive ids")
        for spec in self.primitives:
            if spec.capability_id not in known and spec.capability_id != spec.primitive_id:
                raise ValueError(f"{spec.primitive_id} closes unknown capability {spec.capability_id}")
            assert_technology_agnostic(spec)
        assert_readiness_complete()
        assert_acyclic(derive_dependency_graph(self.primitives))

    @property
    def dependency_graph(self) -> dict[str, frozenset[str]]:
        return derive_dependency_graph(self.primitives)

    @property
    def implementation_order(self) -> tuple[str, ...]:
        return derived_implementation_order(self.dependency_graph)

    def content_hash(self) -> str:
        """H(canonical(contract)) — the tamper-evident identity for the ledger."""
        return hashlib.sha256(canonicalize({
            "primitives": [
                {
                    "primitive_id": p.primitive_id,
                    "capability_id": p.capability_id,
                    "semantic_meaning": p.semantic_meaning,
                    "ownership": p.ownership,
                    "dependencies": sorted(p.derived_dependencies),
                    "constraints": p.constraints,
                    "mutation_surface": p.mutation_surface,
                    "validation_surface": p.validation_surface,
                    "compiler_projection": p.compiler_projection,
                    "evidence_projection": p.evidence_projection,
                    "lineage_requirements": p.lineage_requirements,
                    "type_signature": p.type_signature,
                    "readiness_targets": {
                        s.value: list(t) for s, t in p.readiness_targets.items()
                    },
                    "locality_required": p.locality_required,
                }
                for p in self.primitives
            ],
            "implementation_order": list(self.implementation_order),
            "dependency_graph": {
                n: sorted(edges) for n, edges in self.dependency_graph.items()
            },
            "extension_contract": self.extension_contract,
        }).encode("utf-8")).hexdigest()

    def record(
        self,
        ledger: EvolutionLedger,
        *,
        evolution_id: str = "r2.10.2",
    ) -> str:
        """Anchor the contract as a PRIMITIVE_CONTRACT event (chain-anchored)."""
        self.validate()
        event = EvolutionEvent(
            event_id="",
            evolution_id=evolution_id,
            sequence=0,
            event_type=EventType.PRIMITIVE_CONTRACT,
            subject_id=self.content_hash()[:32],
            payload={
                "contract_content_hash": self.content_hash(),
                "primitive_ids": [p.primitive_id for p in self.primitives],
                "implementation_order": list(self.implementation_order),
                "dependency_acyclic": True,
                "technology_lint_passed": True,
                "readiness_rows": len(self.primitives) * (len(READINESS_ORDER) - 1),
                "extension_contract": list(self.extension_contract),
            },
        )
        return ledger.append_event(event, evolution_id=evolution_id)