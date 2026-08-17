"""R2.10.1 — ISR capability / expressivity audit (diagnostic only).

Measures, capability by capability, whether the constitutional ISR both
*represents* a capability and can *evolve* it end-to-end (mutate, validate
pre-execution, compile into the artifact, observe, track in the ledger).

Constraints honoured:
  * Diagnostic only — NO new ISR primitives here (that is R2.10.2).
  * Status is always DERIVED from the six-dimension assessment
    (``derive_status``), never asserted independently.
  * Per-gene semantic identity is the enabling mechanism: every gene is
    addressed by a path into the semantic projection and hashed with the
    same canonicalization as ``semantic_content_hash``. If a gene cannot be
    individually addressed/hashed, that itself is a PARTIAL/MISSING finding
    — never a workaround.
  * PROJECTED precedes MISSING: a capability that is not natively represented
    but is sufficiently carried by an existing projection is PROJECTED, not
    MISSING.

The audit result is recorded in the ledger as an ``ISR_CAPABILITY_AUDIT``
event (content-hashed, chain-anchored — the R2.8.14 certification pattern),
so R2.10.2 starts from a signed, attested capability matrix.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any, Protocol, Sequence

from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.semantics.projection import canonicalize

from .ledger import EventType, EvolutionEvent, EvolutionLedger


# -- status -------------------------------------------------------------------

@unique
class CapabilityStatus(str, Enum):
    """Derived status of a capability. Never asserted; always computed."""

    EXPRESSED = "expressed"
    PARTIAL = "partial"
    PROJECTED = "projected"
    MISSING = "missing"


@dataclass(frozen=True)
class CapabilityAssessment:
    """Six-dimension assessment of one capability against the ISR + machinery.

    * represented            — the ISR has a native carrier (field/gene).
    * independently_mutatable — an evolution operator can change this gene
      class alone.
    * independently_validatable — invalid mutations of this gene class are
      rejected before execution.
    * compilable             — compiling the candidate still produces the
      corresponding artifact change.
    * observable             — the gene change is observable in the compiled
      artifact's behavior.
    * lineage_tracked        — mutations of this gene class are attributed
      and chain-anchored in the ledger.
    """

    capability_id: str
    represented: bool
    independently_mutatable: bool
    independently_validatable: bool
    compilable: bool
    observable: bool
    lineage_tracked: bool
    projected_via: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    def dimensions(self) -> dict[str, bool]:
        return {
            "represented": self.represented,
            "independently_mutatable": self.independently_mutatable,
            "independently_validatable": self.independently_validatable,
            "compilable": self.compilable,
            "observable": self.observable,
            "lineage_tracked": self.lineage_tracked,
        }


def derive_status(assessment: CapabilityAssessment) -> CapabilityStatus:
    """THE status rule — the single source of truth, never bypassed.

    * not represented, but sufficiently projected via an existing carrier
      -> PROJECTED
    * not represented, no projection            -> MISSING
    * represented with all six dimensions true  -> EXPRESSED
    * represented, any dimension false          -> PARTIAL
    """
    if not assessment.represented:
        return CapabilityStatus.PROJECTED if assessment.projected_via else CapabilityStatus.MISSING
    if all((
        assessment.independently_mutatable,
        assessment.independently_validatable,
        assessment.compilable,
        assessment.observable,
        assessment.lineage_tracked,
    )):
        return CapabilityStatus.EXPRESSED
    return CapabilityStatus.PARTIAL


# -- capability records -------------------------------------------------------

@dataclass(frozen=True)
class ISRCapability:
    """One assessed capability in the matrix."""

    capability_id: str
    name: str
    description: str
    carrier: str
    gene_paths: tuple[str, ...]
    constitutional_ids: tuple[str, ...]
    machinery: bool
    assessment: CapabilityAssessment

    @property
    def status(self) -> CapabilityStatus:
        """Derived only — status can never be asserted independently."""
        return derive_status(self.assessment)


# -- probes -------------------------------------------------------------------

class CapabilityProbe(Protocol):
    """A probe measures one capability against the ISR + machinery."""

    capability_id: str
    name: str
    description: str
    carrier: str
    gene_paths: tuple[str, ...]
    constitutional_ids: tuple[str, ...]
    machinery: bool

    def assess(self, isr: ISR) -> CapabilityAssessment: ...


@dataclass(frozen=True)
class StaticCapabilityProbe:
    """Declarative probe: fixed six-dimension flags + evidence strings."""

    capability_id: str
    name: str
    description: str
    carrier: str
    represented: bool
    gene_paths: tuple[str, ...] = ()
    constitutional_ids: tuple[str, ...] = ()
    machinery: bool = False
    independently_mutatable: bool = False
    independently_validatable: bool = False
    compilable: bool = False
    observable: bool = False
    lineage_tracked: bool = False
    projected_via: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    instance_facts: tuple[str, ...] = ()

    def assess(self, isr: ISR) -> CapabilityAssessment:
        return CapabilityAssessment(
            capability_id=self.capability_id,
            represented=self.represented,
            independently_mutatable=self.independently_mutatable,
            independently_validatable=self.independently_validatable,
            compilable=self.compilable,
            observable=self.observable,
            lineage_tracked=self.lineage_tracked,
            projected_via=self.projected_via,
            evidence=self.evidence + self._instance_evidence(isr),
        )

    def _instance_evidence(self, isr: ISR) -> tuple[str, ...]:
        if not self.instance_facts:
            return ()
        facts: list[str] = []
        modules = isr.system.modules
        workflows = [wf for m in modules for wf in m.workflows]
        facts.append(f"{len(modules)} module(s), {len(workflows)} workflow(s) in audited ISR")
        facts.append(
            f"{sum(1 for wf in workflows for t in wf.transitions)} transition(s), "
            f"{sum(1 for wf in workflows for s in wf.states)} state(s)"
        )
        facts.append(
            f"{sum(len(m.entities) for m in modules)} entity/entities, "
            f"{sum(len(m.services) for m in modules)} service(s), "
            f"{sum(len(m.policies) for m in modules)} polic(y/ies), "
            f"{sum(len(m.interfaces) for m in modules)} interface(s), "
            f"{sum(len(m.events) for m in modules)} event(s)"
        )
        facts.append(
            f"deployment present: {isr.system.deployment is not None}; "
            f"{len(isr.system.constraints)} system constraint(s)"
        )
        return tuple(facts)


# -- constitutional obligation registry --------------------------------------

@dataclass(frozen=True)
class ConstitutionalObligation:
    """An ISR representation obligation from the Constitution."""

    id: str
    name: str


CONSTITUTIONAL_CAPABILITIES: tuple[ConstitutionalObligation, ...] = (
    ConstitutionalObligation("requirements", "Requirements"),
    ConstitutionalObligation("business_capabilities", "Business capabilities"),
    ConstitutionalObligation("domains", "Domains"),
    ConstitutionalObligation("services", "Services"),
    ConstitutionalObligation("components", "Components"),
    ConstitutionalObligation("apis", "APIs"),
    ConstitutionalObligation("events", "Events"),
    ConstitutionalObligation("data_models", "Data models"),
    ConstitutionalObligation("security", "Security"),
    ConstitutionalObligation("infrastructure", "Infrastructure"),
    ConstitutionalObligation("deployment", "Deployment"),
    ConstitutionalObligation("documentation", "Documentation"),
    ConstitutionalObligation("testing", "Testing"),
    ConstitutionalObligation("operational_policies", "Operational policies"),
)


# -- default probe set (the R2.10.1 capability matrix) ------------------------

DEFAULT_PROBES: tuple[StaticCapabilityProbe, ...] = (
    # -- behavior (the evolved FSM substrate) ---------------------------------
    StaticCapabilityProbe(
        capability_id="behavior_transitions",
        name="Behavior: transitions",
        description="Workflow transition edges (from/to/trigger) and their resolution semantics.",
        carrier="Module.workflows[*].transitions",
        gene_paths=("system.modules[*].workflows[*].transitions[*]",),
        constitutional_ids=("services",),
        machinery=True,
        represented=True,
        independently_mutatable=True,
        independently_validatable=True,
        compilable=True,
        observable=True,
        lineage_tracked=True,
        evidence=(
            "represented: WorkflowTransition(from_state_id, to_state_id, trigger, guard_condition, actions)",
            "mutatable: TransitionRestorationOperator adds the resolving edge; RandomFSMExploration proposes seed-replayable transitions",
            "validatable: CausalGate rejects causally-inert transition additions pre-execution; identity invariants gate awaiting-surface changes",
            "compilable: async_resolution_module emits 'await <coroutine>()' iff a resolving trigger exists",
            "observable: generated async tests surface RuntimeWarning for unresolved coroutines",
            "lineage: R2.8.3 MEASUREMENT events attribute each mutation to its operator; candidate/accept events chain in the ledger",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="behavior_await_surface",
        name="Behavior: awaiting surface",
        description="WorkflowState.metadata['awaits'] coroutine declarations (the FSM naming contract).",
        carrier="WorkflowState.metadata['awaits']",
        gene_paths=("system.modules[*].workflows[*].states[*]",),
        constitutional_ids=("services",),
        machinery=True,
        represented=True,
        independently_mutatable=True,
        independently_validatable=True,
        compilable=True,
        observable=True,
        lineage_tracked=True,
        evidence=(
            "represented: WorkflowState.metadata['awaits'] = <coroutine>",
            "mutatable: repairs add awaiting surfaces; TestDeletionMutation strips them (rejected by the boundary)",
            "validatable: AwaitingSurfaceIntactInvariant refuses drop/rename/re-point of an awaiting surface pre-execution",
            "compilable: async_resolution_module emits 'async def <coroutine>()' per awaiting state",
            "observable: the coroutine naming contract is asserted by the generated async tests",
            "lineage: awaiting-surface changes are attributed to operators and chain-anchored",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="behavior_state_semantics",
        name="Behavior: state semantics",
        description="State types (initial/intermediate/final/error) and entry/exit actions.",
        carrier="WorkflowState.state_type / entry_actions / exit_actions",
        gene_paths=("system.modules[*].workflows[*].states[*]",),
        constitutional_ids=("services",),
        machinery=True,
        represented=True,
        independently_mutatable=False,
        independently_validatable=False,
        compilable=False,
        observable=False,
        lineage_tracked=False,
        evidence=(
            "represented: StateType(INITIAL/INTERMEDIATE/FINAL/ERROR), entry_actions, exit_actions",
            "NOT compilable: state types and entry/exit actions are not lowered by async_resolution_module",
            "NOT mutatable: no operator adds or re-types states",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="behavior_guards_actions",
        name="Behavior: guards and actions",
        description="Transition guard conditions and actions (strings on the transition edge).",
        carrier="WorkflowTransition.guard_condition / actions",
        gene_paths=("system.modules[*].workflows[*].transitions[*]",),
        constitutional_ids=("services",),
        machinery=True,
        represented=True,
        independently_mutatable=True,
        independently_validatable=False,
        compilable=False,
        observable=False,
        lineage_tracked=True,
        evidence=(
            "represented: guard_condition (string) and actions (tuple of strings) on WorkflowTransition",
            "mutatable: GuardRelaxationOperator and ActionInjectionOperator mutate guards/actions",
            "NOT compilable: guards/actions are never lowered into the generated artifact",
            "NOT validatable: guard/action strings carry no validated semantics",
            "lineage: guard/action mutations are operator-attributed in MEASUREMENT events",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="behavior_events_triggers",
        name="Behavior: events and triggers",
        description="Domain events (schema/pattern/guarantee) and transition trigger vocabulary.",
        carrier="Module.events / WorkflowTransition.trigger",
        gene_paths=("system.modules[*].events[*]", "system.modules[*].workflows[*].transitions[*]"),
        constitutional_ids=("events",),
        represented=True,
        independently_mutatable=False,
        independently_validatable=False,
        compilable=False,
        observable=False,
        lineage_tracked=False,
        evidence=(
            "represented: Event(schema, pattern, guarantee, ordering_required, ttl_seconds) and string triggers",
            "NOT mutatable: no operator creates, removes, or edits Module.events",
            "NOT compilable: events are not lowered; triggers are compiled only as await-resolution selectors",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="behavior_error_states",
        name="Behavior: error paths",
        description="Explicit error states in the workflow state machine.",
        carrier="WorkflowState.state_type == StateType.ERROR",
        gene_paths=("system.modules[*].workflows[*].states[*]",),
        constitutional_ids=("services",),
        machinery=True,
        represented=True,
        independently_mutatable=False,
        independently_validatable=False,
        compilable=False,
        observable=False,
        lineage_tracked=False,
        evidence=(
            "represented: StateType.ERROR",
            "NOT mutatable: no operator introduces error states",
            "NOT compilable: state types are not lowered by the backends",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="behavior_temporal_semantics",
        name="Behavior: temporal semantics",
        description="Timing intent on behavior: transition deadlines, state minimum durations, event ordering windows.",
        carrier="Module.temporal_constraints (TemporalConstraint)",
        gene_paths=("system.modules[*].temporal_constraints[*]",),
        constitutional_ids=("services",),
        machinery=True,
        represented=True,
        independently_mutatable=True,
        independently_validatable=True,
        compilable=True,
        observable=True,
        lineage_tracked=True,
        evidence=(
            "represented: TemporalConstraint(constraint_id, kind, target_ref, duration_ms, reference_ref) — R2.10.3-A",
            "mutatable: TemporalConstraintOperator adds/edits/removes constraints without touching transition/state/await genes",
            "validatable: TemporalValidationError at construction; ISR.validate_structure() rejects dangling targets and missing ordering references pre-execution",
            "compilable: project_temporal_semantics lowers timing intent into the backend-independent semantic artifact; async_resolution_module byte-identical",
            "observable: project_temporal_evidence exposes each constraint's intent deterministically",
            "lineage: temporal mutations are operator-attributed MEASUREMENT events, chain-anchored in the ledger",
        ),
    ),
    # -- architecture ----------------------------------------------------------
    StaticCapabilityProbe(
        capability_id="architecture_modules",
        name="Architecture: modules / domains",
        description="Bounded contexts (modules) and their ownership of domain artifacts.",
        carrier="System.modules (Module)",
        gene_paths=("system.modules[*]",),
        constitutional_ids=("domains", "components"),
        represented=True,
        independently_mutatable=False,
        independently_validatable=True,
        compilable=False,
        observable=False,
        lineage_tracked=False,
        evidence=(
            "represented: Module(id, name, description, entities, services, workflows, policies, interfaces, events, dependencies)",
            "validatable: ISR.validate_structure() rejects duplicate module ids / empty module sets pre-execution",
            "NOT mutatable: no operator adds or removes modules",
            "NOT compilable: module structure is not lowered (SystemModel stub is name-only)",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="architecture_components",
        name="Architecture: components / services",
        description="Services with operations, dependencies, and event wiring.",
        carrier="Module.services (Service / Operation)",
        gene_paths=("system.modules[*].services[*]",),
        constitutional_ids=("services",),
        represented=True,
        independently_mutatable=False,
        independently_validatable=False,
        compilable=False,
        observable=False,
        lineage_tracked=False,
        evidence=(
            "represented: Service(operations, dependencies, emitted/consumed events, is_stateless)",
            "NOT mutatable: no operator edits services or operations",
            "NOT compilable: services are not lowered by the backends",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="architecture_interfaces_apis",
        name="Architecture: interfaces / APIs",
        description="API contracts: interface types, endpoints, schemas, rate limits, permissions.",
        carrier="Module.interfaces (Interface / Endpoint)",
        gene_paths=("system.modules[*].interfaces[*]",),
        constitutional_ids=("apis",),
        represented=True,
        independently_mutatable=False,
        independently_validatable=False,
        compilable=False,
        observable=False,
        lineage_tracked=False,
        evidence=(
            "represented: Interface(interface_type, endpoints, secured_by_policy_id); Endpoint(path, method, input/output schema, rate_limit, required_permissions)",
            "NOT mutatable: no operator edits interfaces or endpoints",
            "NOT compilable: the backend emits fixed routes, not ISR-derived interfaces",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="architecture_dependencies",
        name="Architecture: dependencies",
        description="Declared module/service dependency references.",
        carrier="Module.dependencies / ServiceDependency",
        gene_paths=("system.modules[*].dependencies", "system.modules[*].services[*].dependencies"),
        constitutional_ids=("components",),
        represented=True,
        independently_mutatable=False,
        independently_validatable=False,
        compilable=False,
        observable=False,
        lineage_tracked=False,
        evidence=(
            "represented: Module.dependencies (id tuple) and ServiceDependency(target_service_id, dependency_type, is_required)",
            "NOT mutatable: no operator edits dependency declarations",
            "NOT validatable: no evolution-time check that dependency targets exist",
            "NOT compilable: dependencies are not lowered by the backends",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="architecture_boundaries",
        name="Architecture: boundaries",
        description="Semantic constraints on relationships between genes: what may or may not cross a boundary.",
        carrier="System.architectural_boundaries (ArchitecturalBoundary)",
        gene_paths=("system.architectural_boundaries[*]",),
        constitutional_ids=("components",),
        machinery=True,
        represented=True,
        independently_mutatable=True,
        independently_validatable=True,
        compilable=True,
        observable=True,
        lineage_tracked=True,
        evidence=(
            "represented: ArchitecturalBoundary(member_refs, forbidden_dependency_refs, protected, crossing_invariants) — R2.10.3-E",
            "mutatable: BoundaryOperator (add/remove/set_forbidden_refs/generate) with MEASUREMENT lineage; protected-boundary removal rejected as ConstitutionalViolation",
            "validatable: BoundaryValidationError at construction; validate_system_boundary_constraints rejects dangling member/forbidden refs and duplicate ids pre-execution",
            "compilable: project_architectural_boundaries lowers the constraint; no realization leakage (BOUNDARY_MECHANISM_TERMS lint)",
            "observable: boundary gene stays byte-identical while its members' implementations evolve (reference-by-identity)",
            "lineage: boundary mutations are operator-attributed MEASUREMENT events, chain-anchored in the ledger",
        ),
    ),
    # -- deployment ------------------------------------------------------------
    StaticCapabilityProbe(
        capability_id="deployment_topology",
        name="Deployment: topology",
        description="Environment tiers, scaling, networking, storage, secrets, monitoring config.",
        carrier="System.deployment (Deployment)",
        gene_paths=("system.deployment",),
        constitutional_ids=("deployment",),
        represented=True,
        independently_mutatable=False,
        independently_validatable=False,
        compilable=False,
        observable=False,
        lineage_tracked=False,
        evidence=(
            "represented: Deployment(environment, scaling, networking, monitoring, storage, secrets)",
            "NOT mutatable: no operator edits the deployment model",
            "NOT compilable: deployment is not lowered (backend emits fixed Dockerfile/compose templates)",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="deployment_rollout_rollback",
        name="Deployment: rollout / rollback",
        description="Rollout strategies, rollback plans, and canary/staged promotion.",
        carrier="(none)",
        gene_paths=(),
        constitutional_ids=("deployment",),
        represented=False,
        evidence=(
            "NOT represented: no rollout/rollback carrier in Deployment",
        ),
    ),
    # -- data ------------------------------------------------------------------
    StaticCapabilityProbe(
        capability_id="data_entities_schema",
        name="Data: entities and schema",
        description="Entities, fields, relationships, constraints, aggregate/value-object markers.",
        carrier="Module.entities (Entity / Field / Relationship)",
        gene_paths=("system.modules[*].entities[*]",),
        constitutional_ids=("data_models",),
        represented=True,
        independently_mutatable=False,
        independently_validatable=False,
        compilable=False,
        observable=False,
        lineage_tracked=False,
        evidence=(
            "represented: Entity(fields, relationships, constraints, is_aggregate_root, is_value_object)",
            "NOT mutatable: no operator edits entities, fields, or relationships",
            "NOT compilable: the backend lowers a fixed stub data model, not ISR entities",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="data_persistence_consistency",
        name="Data: persistence and consistency",
        description="Persistence requirements, storage, event delivery guarantees, cascade semantics.",
        carrier="Deployment.storage / Event.guarantee / Relationship.cascade_delete",
        gene_paths=("system.deployment.storage", "system.modules[*].events[*]", "system.modules[*].entities[*].relationships[*]"),
        constitutional_ids=("data_models", "infrastructure"),
        represented=True,
        independently_mutatable=False,
        independently_validatable=False,
        compilable=False,
        observable=False,
        lineage_tracked=False,
        evidence=(
            "represented: StorageConfig(persistent_storage_required, backup_enabled, encryption_at_rest); EventGuarantee; cascade_delete",
            "NOT mutatable: no operator edits storage, guarantees, or cascade semantics",
            "NOT compilable: persistence is not lowered by the backends",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="data_migrations",
        name="Data: migrations",
        description="Semantic data-evolution intent: schema evolution, compatibility, preservation, ordering, rollback semantics.",
        carrier="Module.data_migrations (DataMigrationIntent)",
        gene_paths=("system.modules[*].data_migrations[*]",),
        constitutional_ids=("data_models",),
        represented=True,
        independently_mutatable=True,
        independently_validatable=True,
        compilable=True,
        observable=True,
        lineage_tracked=True,
        evidence=(
            "represented: DataMigrationIntent(migration_id, source/target_schema_ref, compatibility_policy, preservation_refs, depends_on, rollback_required, rollback_target_ref, rollback_invariants, postconditions) — R2.10.3-C",
            "intent only: compatibility is declared (never policy), rollback is invariants (never a command), ordering is an explicit acyclic depends_on graph",
            "no mechanism: the construct has no field for SQL/ORM/framework commands; MIGRATION_MECHANISM_TERMS lint gates the semantic form",
            "mutatable: MigrationOperator adds/removes/respecifies intents without touching entity/behavior/capability/temporal genes",
            "validatable: MigrationValidationError at construction; ISR.validate_structure() rejects dangling schema/preservation/dependency refs and circular depends_on pre-execution",
            "compilable: project_data_migrations projects compatibility/preservation/ordering/rollback semantics (backend-independent); async_resolution_module byte-identical",
            "observable: declared intents observable in the semantic projection; mutations attributed in MEASUREMENT events",
            "lineage: migration mutations are operator-attributed MEASUREMENT events, chain-anchored in the ledger",
        ),
    ),
    # -- security --------------------------------------------------------------
    StaticCapabilityProbe(
        capability_id="security_authorization",
        name="Security: authorization",
        description="Authorization policies, permissions (resource/actions/conditions), endpoint requirements.",
        carrier="Policy(PolicyType.AUTHORIZATION) / Permission / Endpoint.required_permissions",
        gene_paths=("system.modules[*].policies[*]", "system.modules[*].interfaces[*].endpoints[*]"),
        constitutional_ids=("security",),
        represented=True,
        independently_mutatable=False,
        independently_validatable=True,
        compilable=False,
        observable=False,
        lineage_tracked=False,
        evidence=(
            "represented: Policy(roles, permissions, rules) and required_permissions",
            "validatable: R2.8.6 security validation rejects invalid authorization pre-execution",
            "NOT mutatable: no operator edits policies or permissions",
            "NOT compilable: the backend hardcodes API-key auth; ISR policies are not lowered",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="security_authentication_trust",
        name="Security: authentication / trust",
        description="Authentication posture, TLS, encryption, secrets rotation.",
        carrier="Policy(PolicyType.AUTHENTICATION) / NetworkingConfig.tls_required / SecretsConfig",
        gene_paths=("system.modules[*].policies[*]", "system.deployment.networking", "system.deployment.secrets"),
        constitutional_ids=("security",),
        represented=True,
        independently_mutatable=False,
        independently_validatable=True,
        compilable=False,
        observable=False,
        lineage_tracked=False,
        evidence=(
            "represented: authentication policies, tls_required, encryption_in_transit, rotation_policy_days",
            "validatable: R2.8.6 security validation rejects invalid authentication pre-execution",
            "NOT mutatable: no operator edits authentication posture",
            "NOT compilable: the backend's auth middleware is fixed, not ISR-derived",
        ),
    ),
    # -- requirements ----------------------------------------------------------
    StaticCapabilityProbe(
        capability_id="requirements_constraints",
        name="Requirements: constraints",
        description="Hard architectural rules and boundaries as constraints.",
        carrier="System.constraints (Constraint)",
        gene_paths=("system.constraints[*]",),
        constitutional_ids=("requirements",),
        represented=True,
        independently_mutatable=False,
        independently_validatable=False,
        compilable=False,
        observable=False,
        lineage_tracked=False,
        evidence=(
            "represented: Constraint(scope, severity, rule_type, parameters, target_node_ids)",
            "NOT validatable: constraint semantics are free-form strings; no evolution-time constraint checking",
            "NOT mutatable: no operator edits constraints",
            "NOT compilable: constraints are not lowered",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="requirements_acceptance_traceability",
        name="Requirements: acceptance / traceability",
        description="Functional/NFR/acceptance criteria and requirement-to-gene traceability.",
        carrier="System.requirements (Requirement) + System.acceptance_criteria (AcceptanceCriterion)",
        gene_paths=("system.requirements[*]", "system.acceptance_criteria[*]"),
        constitutional_ids=("requirements",),
        represented=True,
        independently_mutatable=True,
        independently_validatable=True,
        compilable=True,
        observable=True,
        lineage_tracked=True,
        evidence=(
            "represented: Requirement(statement, target_refs, acceptance_refs, constraint_refs)",
            "represented: AcceptanceCriterion(obligation, kind, subject_refs) — the middle layer",
            "mutatable: RequirementOperator (add/remove/set_statement/add_criterion/assign_criterion/link_capability)",
            "validatable: validate_system_requirement_constraints — duplicate ids, dangling target/acceptance/constraint/subject refs",
            "compilable: requirement is a semantic obligation, never an implementation task",
            "observable: project_requirements / project_acceptance_criteria projections",
            "lineage: MEASUREMENT events per mutation with before/after hashes",
            "RESERVATION ACTIVATED: BusinessCapability.requirement_refs now resolve against System.requirements",
            "acceptance criterion declares obligation + kind + subjects; no is_satisfied(), no verdict, no test reference",
        ),
    ),
    # -- reliability / performance / observability -----------------------------
    StaticCapabilityProbe(
        capability_id="reliability_resilience",
        name="Reliability: resilience",
        description="Required system behavior under failure: what must survive, what degradation is acceptable, what recovery is required.",
        carrier="System.reliability_requirements (ReliabilityRequirement)",
        gene_paths=("system.reliability_requirements[*]",),
        constitutional_ids=("infrastructure",),
        represented=True,
        independently_mutatable=True,
        independently_validatable=True,
        compilable=True,
        observable=True,
        lineage_tracked=True,
        evidence=(
            "represented: ReliabilityRequirement(failure_modes, recovery_objectives, degradation_policy, preservation_invariants, dependency_constraints)",
            "mutatable: ReliabilityOperator (add/remove/set_policy/add_recovery_objective/generate) with MEASUREMENT lineage",
            "validatable: validate_system_reliability_constraints (dangling targets, undeclared/contradictory recovery objectives)",
            "compilable: project_reliability_requirements lowers the gene; no mechanism leakage (RELIABILITY_MECHANISM_TERMS lint)",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="performance_scalability",
        name="Performance: scalability",
        description="Scaling strategy and latency/throughput SLOs.",
        carrier="Deployment.scaling (ScalingConfig)",
        gene_paths=("system.deployment.scaling",),
        constitutional_ids=("infrastructure",),
        represented=True,
        independently_mutatable=False,
        independently_validatable=False,
        compilable=False,
        observable=False,
        lineage_tracked=False,
        evidence=(
            "represented: ScalingConfig(strategy, min/max_instances, target_cpu/memory_percent)",
            "NOT represented: latency/throughput SLOs have no carrier",
            "NOT mutatable / NOT compilable: scaling is not operator-driven or lowered",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="observability",
        name="Observability",
        description="Health/readiness checks, metrics, tracing, structured logging, alert rules.",
        carrier="Deployment.monitoring (MonitoringConfig)",
        gene_paths=("system.deployment.monitoring",),
        constitutional_ids=("infrastructure",),
        represented=True,
        independently_mutatable=False,
        independently_validatable=False,
        compilable=False,
        observable=False,
        lineage_tracked=False,
        evidence=(
            "represented: MonitoringConfig(health_check_path, readiness_check_path, metrics_enabled, tracing_enabled, structured_logging, alert_rules)",
            "NOT compilable: the backend emits a fixed logging_config.py, not ISR-derived monitoring",
            "NOT mutatable: no operator edits the monitoring model",
        ),
    ),
    # -- operations / documentation / testing -----------------------------------
    StaticCapabilityProbe(
        capability_id="operational_policies",
        name="Operations: operational policies",
        description="Operational rule sets (rate limiting, audit, data retention, compliance).",
        carrier="Policy(PolicyType.OPERATIONAL / RATE_LIMITING / AUDIT / DATA_RETENTION / COMPLIANCE)",
        gene_paths=("system.modules[*].policies[*]",),
        constitutional_ids=("operational_policies",),
        represented=True,
        independently_mutatable=False,
        independently_validatable=False,
        compilable=False,
        observable=False,
        lineage_tracked=False,
        evidence=(
            "represented: PolicyType.OPERATIONAL / RATE_LIMITING / AUDIT / DATA_RETENTION / COMPLIANCE",
            "NOT mutatable / NOT compilable: operational policies are neither operator-driven nor lowered",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="documentation",
        name="Documentation",
        description="Documentation as an ISR-represented capability.",
        carrier="(none)",
        gene_paths=(),
        constitutional_ids=("documentation",),
        represented=False,
        evidence=(
            "NOT represented: README is a fixed backend template, not ISR-derived",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="testing_anchoring",
        name="Testing: anchoring",
        description="Protected / holdout test identity as an ISR-represented capability.",
        carrier="(none)",
        gene_paths=(),
        constitutional_ids=("testing",),
        represented=False,
        evidence=(
            "NOT represented in the ISR: protected/holdout test identity is external, anchored via R2.8.14 ANCHOR events",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="business_capabilities",
        name="Business capabilities",
        description="First-class capability declarations: WHAT the system can do, referencing behaviors/interfaces/constraints by identity.",
        carrier="System.business_capabilities (BusinessCapability)",
        gene_paths=("system.business_capabilities[*]",),
        constitutional_ids=("business_capabilities",),
        represented=True,
        independently_mutatable=True,
        independently_validatable=True,
        compilable=True,
        observable=True,
        lineage_tracked=True,
        evidence=(
            "represented: BusinessCapability(capability_id, intent, behavior_refs, interface_refs, constraint_refs, requirement_refs) — R2.10.3-B",
            "first-class: capabilities are DECLARED, never inferred from workflows/modules; references are by identity, never by content",
            "mutatable: CapabilityOperator adds/removes/respecifies intents/membership without touching behavior/interface/constraint genes",
            "validatable: CapabilityValidationError at construction; ISR.validate_structure() rejects duplicate ids and dangling references pre-execution",
            "compilable: project_business_capabilities projects intent + reference identities (backend-independent); async_resolution_module byte-identical",
            "observable: declared capabilities observable in the semantic projection; mutations attributed in MEASUREMENT events",
            "lineage: capability mutations are operator-attributed MEASUREMENT events, chain-anchored in the ledger",
        ),
    ),
    # -- evolution machinery ----------------------------------------------------
    StaticCapabilityProbe(
        capability_id="evolution_lineage_provenance",
        name="Evolution: lineage / provenance",
        description="Per-version provenance and parent linkage inside the ISR.",
        carrier="ISR.provenance (ISRProvenance)",
        gene_paths=("provenance",),
        constitutional_ids=(),
        machinery=True,
        represented=True,
        independently_mutatable=True,
        independently_validatable=False,
        compilable=False,
        observable=False,
        lineage_tracked=True,
        evidence=(
            "represented: ISRProvenance(parent_hash, mutation_description, evolution_run_id, generation)",
            "mutatable: ISR.with_system() stamps fresh provenance on every mutation (immutability path)",
            "lineage: the ledger chain records every version transition",
            "NOT compilable: provenance never affects the artifact",
        ),
    ),
    StaticCapabilityProbe(
        capability_id="evolution_objectives_protected_regions",
        name="Evolution: objectives / protected regions",
        description="Declared mutation points, protected regions, and evolution objectives in the ISR.",
        carrier="(none)",
        gene_paths=(),
        constitutional_ids=(),
        machinery=True,
        represented=False,
        evidence=(
            "NOT represented: no mutation-point / protected-region / objective carrier in the ISR",
            "objectives live in the scheduler/policy layer, not in the ISR",
        ),
    ),
)


# -- per-gene semantic identity ------------------------------------------------

def _gene_hash(value: Any) -> str:
    """Hash one gene subtree with the SAME canonicalization as content_hash."""
    return hashlib.sha256(canonicalize(value).encode("utf-8")).hexdigest()


def gene_index(isr: ISR) -> dict[str, str]:
    """Address every gene of the ISR by its projection path and hash it.

    Node-level granularity: each dataclass instance (module, entity, service,
    workflow, state, transition, policy, interface, endpoint, event, constraint,
    temporal constraint, business capability, data migration, deployment
    sub-config, reliability requirement, architectural boundary, requirement,
    acceptance criterion) is one gene. ``canonicalize`` is the shared single
    source of truth, so gene hashes compose with the ISR's content hash.
    """
    idx: dict[str, str] = {}
    system = isr.system
    idx["system"] = _gene_hash((system.id, system.name, system.description, system.metadata, system.global_policies))
    for ci, constraint in enumerate(system.constraints):
        idx[f"system.constraints[{ci}]"] = _gene_hash(constraint)
    for gi, policy in enumerate(system.global_policies):
        idx[f"system.global_policies[{gi}]"] = _gene_hash(policy)
    if system.deployment is not None:
        deployment = system.deployment
        idx["system.deployment"] = _gene_hash((deployment.id, deployment.name, deployment.description, deployment.environment, deployment.metadata))
        idx["system.deployment.scaling"] = _gene_hash(deployment.scaling)
        idx["system.deployment.networking"] = _gene_hash(deployment.networking)
        idx["system.deployment.monitoring"] = _gene_hash(deployment.monitoring)
        idx["system.deployment.storage"] = _gene_hash(deployment.storage)
        idx["system.deployment.secrets"] = _gene_hash(deployment.secrets)
    for ci, capability in enumerate(system.business_capabilities):
        idx[f"system.business_capabilities[{ci}]"] = _gene_hash(capability)
    for ri, requirement in enumerate(system.reliability_requirements):
        idx[f"system.reliability_requirements[{ri}]"] = _gene_hash(requirement)
    for bi, boundary in enumerate(system.architectural_boundaries):
        idx[f"system.architectural_boundaries[{bi}]"] = _gene_hash(boundary)
    for ri, requirement in enumerate(system.requirements):
        idx[f"system.requirements[{ri}]"] = _gene_hash(requirement)
    for ci, criterion in enumerate(system.acceptance_criteria):
        idx[f"system.acceptance_criteria[{ci}]"] = _gene_hash(criterion)
    for mi, module in enumerate(system.modules):
        base = f"system.modules[{mi}]"
        idx[base] = _gene_hash((module.id, module.name, module.description, module.metadata))
        idx[f"{base}.dependencies"] = _gene_hash(module.dependencies)
        for ei, entity in enumerate(module.entities):
            idx[f"{base}.entities[{ei}]"] = _gene_hash(entity)
        for si, service in enumerate(module.services):
            idx[f"{base}.services[{si}]"] = _gene_hash(service)
        for wi, workflow in enumerate(module.workflows):
            wbase = f"{base}.workflows[{wi}]"
            idx[wbase] = _gene_hash((workflow.id, workflow.name, workflow.description, workflow.metadata))
            for sti, state in enumerate(workflow.states):
                idx[f"{wbase}.states[{sti}]"] = _gene_hash(state)
            for ti, transition in enumerate(workflow.transitions):
                idx[f"{wbase}.transitions[{ti}]"] = _gene_hash(transition)
        for pi, policy in enumerate(module.policies):
            idx[f"{base}.policies[{pi}]"] = _gene_hash(policy)
        for ii, interface in enumerate(module.interfaces):
            idx[f"{base}.interfaces[{ii}]"] = _gene_hash(interface)
            for ei, endpoint in enumerate(interface.endpoints):
                idx[f"{base}.interfaces[{ii}].endpoints[{ei}]"] = _gene_hash(endpoint)
        for evi, event in enumerate(module.events):
            idx[f"{base}.events[{evi}]"] = _gene_hash(event)
        for tci, constraint in enumerate(module.temporal_constraints):
            idx[f"{base}.temporal_constraints[{tci}]"] = _gene_hash(constraint)
        for mi_i, migration in enumerate(module.data_migrations):
            idx[f"{base}.data_migrations[{mi_i}]"] = _gene_hash(migration)
    return idx


@dataclass(frozen=True)
class LocalityResult:
    """Outcome of one mutation-locality probe on one gene."""

    gene_path: str
    before_hash: str
    after_hash: str
    target_gene_changed: bool
    unintended_changes: tuple[str, ...]

    @property
    def locality_holds(self) -> bool:
        return self.target_gene_changed and not self.unintended_changes


class MutationLocalityProbe:
    """Per-gene mutation locality: only the addressed gene may change.

    A mutation that alters any other gene (or fails to alter its target) is
    a locality violation — the R2.10.1 enabling check for gene-level mutation.
    """

    def probe(self, before: ISR, after: ISR, gene_path: str) -> LocalityResult:
        idx_before = gene_index(before)
        idx_after = gene_index(after)
        before_hash = idx_before.get(gene_path, "")
        after_hash = idx_after.get(gene_path, "")
        target_changed = (
            (before_hash != after_hash)
            or (gene_path not in idx_before)
            or (gene_path not in idx_after)
        )
        unintended = sorted(
            path
            for path in set(idx_before) | set(idx_after)
            if path != gene_path and idx_before.get(path) != idx_after.get(path)
        )
        return LocalityResult(
            gene_path=gene_path,
            before_hash=before_hash,
            after_hash=after_hash,
            target_gene_changed=target_changed,
            unintended_changes=tuple(unintended),
        )


# -- audit runner -------------------------------------------------------------

@dataclass(frozen=True)
class ISRCapabilityAuditResult:
    """The signed capability matrix for one audited ISR."""

    isr_hash: str
    capabilities: tuple[ISRCapability, ...]

    @property
    def by_status(self) -> dict[CapabilityStatus, tuple[ISRCapability, ...]]:
        out: dict[CapabilityStatus, list[ISRCapability]] = {s: [] for s in CapabilityStatus}
        for capability in self.capabilities:
            out[capability.status].append(capability)
        return {s: tuple(sorted(caps, key=lambda c: c.capability_id)) for s, caps in out.items()}

    @property
    def unclassified(self) -> tuple[str, ...]:
        """Constitutional obligations without a covering probe + orphan probes."""
        covered = {cid for c in self.capabilities for cid in c.constitutional_ids}
        uncovered = tuple(
            obligation.id
            for obligation in CONSTITUTIONAL_CAPABILITIES
            if obligation.id not in covered
        )
        orphans = tuple(
            c.capability_id
            for c in self.capabilities
            if not c.constitutional_ids and not c.machinery
        )
        return uncovered + orphans

    @property
    def integrity(self) -> bool:
        return not self.unclassified

    def content_hash(self) -> str:
        """H(canonical(matrix)) — the tamper-evident identity anchored in the ledger."""
        return hashlib.sha256(canonicalize({
            "isr_hash": self.isr_hash,
            "capabilities": [
                {
                    "capability_id": c.capability_id,
                    "name": c.name,
                    "carrier": c.carrier,
                    "gene_paths": c.gene_paths,
                    "constitutional_ids": c.constitutional_ids,
                    "machinery": c.machinery,
                    "status": c.status.value,
                    "assessment": c.assessment.dimensions(),
                    "projected_via": c.assessment.projected_via,
                }
                for c in self.capabilities
            ],
        }).encode("utf-8")).hexdigest()

    def summary(self) -> dict[str, int]:
        return {s.value: len(caps) for s, caps in self.by_status.items()}


class ISRCapabilityAudit:
    """Runs the probe set over an ISR and records the signed matrix."""

    def __init__(self, probes: Sequence[CapabilityProbe] = DEFAULT_PROBES) -> None:
        self._probes = tuple(probes)
        self._mutation_locality = MutationLocalityProbe()

    @property
    def mutation_locality(self) -> MutationLocalityProbe:
        return self._mutation_locality

    def run(self, isr: ISR) -> ISRCapabilityAuditResult:
        capabilities = tuple(
            ISRCapability(
                capability_id=probe.capability_id,
                name=probe.name,
                description=probe.description,
                carrier=probe.carrier,
                gene_paths=probe.gene_paths,
                constitutional_ids=probe.constitutional_ids,
                machinery=probe.machinery,
                assessment=probe.assess(isr),
            )
            for probe in self._probes
        )
        return ISRCapabilityAuditResult(isr_hash=isr.content_hash, capabilities=capabilities)

    def record(
        self,
        result: ISRCapabilityAuditResult,
        ledger: EvolutionLedger,
        *,
        evolution_id: str = "r2.10.1",
    ) -> str:
        """Anchor the signed capability matrix as an ISR_CAPABILITY_AUDIT event.

        Content-hashed and chain-anchored exactly like the R2.8.14
        certification artifact — tampering any assessment breaks the chain.
        """
        event = EvolutionEvent(
            event_id="",
            evolution_id=evolution_id,
            sequence=0,
            event_type=EventType.ISR_CAPABILITY_AUDIT,
            subject_id=result.content_hash()[:32],
            isr_hash=result.isr_hash,
            payload={
                "audit_content_hash": result.content_hash(),
                "integrity": result.integrity,
                "unclassified": list(result.unclassified),
                "by_status": {
                    status.value: [c.capability_id for c in caps]
                    for status, caps in result.by_status.items()
                },
                "summary": result.summary(),
                "constitutional_obligations": [o.id for o in CONSTITUTIONAL_CAPABILITIES],
            },
        )
        return ledger.append_event(event, evolution_id=evolution_id)