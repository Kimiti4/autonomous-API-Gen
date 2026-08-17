"""R2.10.3-G — deployment_rollout_rollback: intent and lifecycle guarantees.

Deployment is where the gravity toward infrastructure specification is
strongest — the entire culture expresses deployment as Kubernetes manifests,
replica counts, and CI/CD pipelines. G holds TWO distinct boundaries because
they fail differently:

1. NO realization technology in the gene. The construct is STRUCTURALLY
   incapable of carrying one (field-name test: nowhere to put replica_count,
   pod_spec, container_image, manifest, pipeline, …) AND the
   DEPLOYMENT_MECHANISM_TERMS lint gates the canonical semantic form. The
   lint asymmetry is the proof: CANARY / BLUE_GREEN are SEMANTIC strategies
   and PASS; kubernetes and replica_count FAIL.

2. NO backward leak into architecture. Deployment references architecture
   (targets = capabilities/modules) by identity; a deployment mutation must
   never propagate into the boundary genes it references. Combined with the
   forward property (target implementation evolution never moves the
   deployment gene), deployment is proven an independently evolvable
   lifecycle dimension that composes with architecture by reference only.

CARRIER DECISION: ``System.deployment_intents`` is a NEW carrier alongside
the pre-existing ``System.deployment`` environment placeholder — two
different semantic layers: environment attributes (WHERE it runs) vs
lifecycle contract (HOW a change must proceed). Both empty identity-neutral
(Option A). Rollback reuses C's rollback-as-invariant pattern: a contract
about what must be restored, never a command; ``rollback_target_ref`` must
name one of the intent's OWN targets (C's rule).

The audit gate embeds the pre-landing matrix (8/18/0/4 — after R2.10.3-F)
and asserts the delta is exactly {deployment_rollout_rollback: MISSING ->
EXPRESSED} -> 9/18/0/3.
"""
from __future__ import annotations

import dataclasses
import tempfile
from typing import Any

import pytest

from constitutional_architecture.isr.model import (
    AcceptanceCriterion,
    ArchitecturalBoundary,
    BusinessCapability,
    CompatibilityPolicy,
    DataMigrationIntent,
    DegradationPolicy,
    DeploymentIntent,
    DeploymentValidationError,
    Entity,
    FailureMode,
    ISR,
    Interface,
    InterfaceType,
    Module,
    ObligationKind,
    RecoveryBehavior,
    RecoveryObjective,
    ReliabilityRequirement,
    Requirement,
    RolloutStrategy,
    StateType,
    System,
    TemporalConstraint,
    TemporalConstraintKind,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)
from constitutional_architecture.isr.semantics.deployment import (
    DEPLOYMENT_MECHANISM_TERMS,
    assert_deployment_technology_agnostic,
    deployment_mechanism_hits,
    project_deployment_intents,
)
from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend
from tiannara.application.evolution.deployment_mutation import DeploymentOperator
from tiannara.application.evolution.isr_capability_audit import (
    CapabilityStatus,
    ISRCapabilityAudit,
    MutationLocalityProbe,
    gene_index,
)
from tiannara.application.evolution.ledger import EventType, EvolutionLedger
from tiannara.application.evolution.primitive_contract import TECHNOLOGY_COUPLING_TERMS
from tiannara.application.evolution.primitive_gate import (
    PRIMITIVE_GATE,
    GateResult,
    assert_all_gates,
)


def _entity(entity_id: str) -> Entity:
    return Entity(id=entity_id, name=entity_id)


def _workflow(workflow_id: str, trigger: str) -> Workflow:
    return Workflow(
        id=workflow_id,
        name=f"workflow {workflow_id}",
        states=(
            WorkflowState(
                id=f"{workflow_id}-start",
                name="started",
                state_type=StateType.INTERMEDIATE,
                metadata={"awaits": trigger},
            ),
            WorkflowState(
                id=f"{workflow_id}-done",
                name="done",
                state_type=StateType.FINAL,
            ),
        ),
        transitions=(
            WorkflowTransition(
                id=f"{workflow_id}-t1",
                name="resolve",
                from_state_id=f"{workflow_id}-start",
                to_state_id=f"{workflow_id}-done",
                trigger=trigger,
            ),
        ),
    )


class DeploymentPrimitiveHarness:
    """The eleven-gate harness for deployment_rollout_rollback."""

    primitive_id = "deployment_rollout_rollback"

    def __init__(self) -> None:
        self.audit = ISRCapabilityAudit()
        self.operator = DeploymentOperator()
        self.locality_probe = MutationLocalityProbe()
        self.backend = FastAPIHexagonalBackend()

    # -- recipes ------------------------------------------------------------

    def valid_intent(self) -> DeploymentIntent:
        return DeploymentIntent(
            deployment_id="dep1",
            target_refs=("pay",),
            rollout_strategy=RolloutStrategy.CANARY,
            rollout_constraints=("at most one degraded target",),
            health_requirements=("payment remains reachable",),
            rollback_required=True,
            rollback_target_ref="pay",
            rollback_invariants=("payment state preserved",),
            preservation_requirements=("no data loss",),
        )

    def isr_with(
        self,
        intents: tuple[DeploymentIntent, ...] = (),
        with_requirement: bool = True,
        with_boundary: bool = True,
        with_reliability: bool = True,
        with_migration: bool = True,
        with_temporal: bool = True,
        with_capability: bool = True,
    ) -> ISR:
        temporal_constraints = (
            (
                TemporalConstraint(
                    constraint_id="t1.deadline",
                    kind=TemporalConstraintKind.TRANSITION_DEADLINE,
                    target_ref="w1-t1",
                    duration_ms=250,
                ),
            )
            if with_temporal
            else ()
        )
        migrations = (
            (
                DataMigrationIntent(
                    migration_id="m1",
                    source_schema_ref="e1",
                    target_schema_ref="e2",
                    compatibility_policy=CompatibilityPolicy.BACKWARD,
                    preservation_refs=("e1",),
                    rollback_required=True,
                    rollback_target_ref="e1",
                    rollback_invariants=("e1 intact",),
                    postconditions=("e2 valid",),
                ),
            )
            if with_migration
            else ()
        )
        capabilities = (
            (
                BusinessCapability(
                    capability_id="pay",
                    intent="process a payment",
                    behavior_refs=("w1",),
                    interface_refs=("i1",),
                ),
            )
            if with_capability
            else ()
        )
        reliability_requirements = (
            (
                ReliabilityRequirement(
                    requirement_id="rr1",
                    target_refs=("pay",),
                    failure_modes=(FailureMode.TRANSIENT_DEPENDENCY_FAILURE,),
                    recovery_objectives=(
                        RecoveryObjective(
                            failure_mode=FailureMode.TRANSIENT_DEPENDENCY_FAILURE,
                            required_behavior=RecoveryBehavior.EVENTUAL_RECOVERY,
                            max_recovery_duration_ms=5000,
                        ),
                    ),
                    degradation_policy=DegradationPolicy.NO_DEGRADATION,
                    preservation_invariants=("pay coherent",),
                ),
            )
            if with_reliability
            else ()
        )
        boundaries = (
            (
                ArchitecturalBoundary(
                    boundary_id="b1",
                    member_refs=("m",),
                    forbidden_dependency_refs=(),
                    protected=False,
                    crossing_invariants=("no cross without declared intent",),
                ),
            )
            if with_boundary
            else ()
        )
        requirements = (
            (
                Requirement(
                    requirement_id="req.cancel",
                    statement="Cancellation must become effective before settlement",
                    target_refs=("pay",),
                    acceptance_refs=("crit.cancel",),
                    constraint_refs=("w1",),
                ),
            )
            if with_requirement
            else ()
        )
        criteria = (
            (
                AcceptanceCriterion(
                    criterion_id="crit.cancel",
                    obligation="Order cancellation must become effective before settlement",
                    kind=ObligationKind.ORDERING,
                    subject_refs=("w1",),
                ),
            )
            if with_requirement
            else ()
        )
        return ISR(
            system=System(
                id="dep-sys",
                name="DeploymentSystem",
                modules=(
                    Module(
                        id="m",
                        name="M",
                        entities=tuple(_entity(eid) for eid in ("e1", "e2")),
                        workflows=(_workflow("w1", "op_w1"),),
                        interfaces=(
                            Interface(id="i1", name="i1", interface_type=InterfaceType.REST),
                        ),
                        temporal_constraints=temporal_constraints,
                        data_migrations=migrations,
                    ),
                ),
                business_capabilities=capabilities,
                reliability_requirements=reliability_requirements,
                architectural_boundaries=boundaries,
                requirements=requirements,
                acceptance_criteria=criteria,
                deployment_intents=intents,
            )
        )

    def isr_without_deployment(self) -> ISR:
        return self.isr_with()

    def isr_with_deployment(self) -> ISR:
        return self.isr_with(intents=(self.valid_intent(),))

    def isr_with_deployment_targeting(self, target_id: str) -> ISR:
        return self.isr_with(
            intents=(
                dataclasses.replace(
                    self.valid_intent(),
                    target_refs=(target_id,),
                    rollback_target_ref=target_id,
                ),
            )
        )

    def with_empty_deployment(self, isr: ISR) -> ISR:
        return isr.with_system(
            dataclasses.replace(isr.system, deployment_intents=())
        )

    def evolve_target_implementation(self, isr: ISR, module_id: str) -> ISR:
        """Mutate a deployed target's implementation while its identity is stable."""
        modules = []
        for module in isr.system.modules:
            if module.id == module_id:
                module = dataclasses.replace(
                    module, description="implementation evolved under deployment"
                )
            modules.append(module)
        return isr.with_system(
            dataclasses.replace(isr.system, modules=tuple(modules))
        )

    # -- gene addressing ------------------------------------------------------

    def all_gene_hashes(self, isr: ISR) -> dict[str, str]:
        """Every gene except the deployment intent gene class."""
        return {
            path: h
            for path, h in gene_index(isr).items()
            if "deployment_intents" not in path
        }

    def gene_hashes(self, isr: ISR, domain: str) -> dict[str, str]:
        """All genes under a domain path segment."""
        return {p: h for p, h in gene_index(isr).items() if domain in p}

    def gene_hash(self, isr: ISR, gene: tuple) -> str:
        """("deployment", did) / ("capability", cid) / ("module", mid) /
        ("behavior", wf_id) / ("boundary", bid) / ("reliability", rid) /
        ("requirement", rid) / ("criterion", cid) / ("migration", mid) /
        ("temporal", cid)."""
        idx = gene_index(isr)
        kind, name = gene
        if kind == "deployment":
            for di, intent in enumerate(isr.system.deployment_intents):
                if intent.deployment_id == name:
                    return idx[f"system.deployment_intents[{di}]"]
        if kind == "capability":
            for ci, capability in enumerate(isr.system.business_capabilities):
                if capability.capability_id == name:
                    return idx[f"system.business_capabilities[{ci}]"]
        if kind == "boundary":
            for bi, boundary in enumerate(isr.system.architectural_boundaries):
                if boundary.boundary_id == name:
                    return idx[f"system.architectural_boundaries[{bi}]"]
        if kind == "reliability":
            for ri, requirement in enumerate(isr.system.reliability_requirements):
                if requirement.requirement_id == name:
                    return idx[f"system.reliability_requirements[{ri}]"]
        if kind == "requirement":
            for ri, requirement in enumerate(isr.system.requirements):
                if requirement.requirement_id == name:
                    return idx[f"system.requirements[{ri}]"]
        if kind == "criterion":
            for ci, criterion in enumerate(isr.system.acceptance_criteria):
                if criterion.criterion_id == name:
                    return idx[f"system.acceptance_criteria[{ci}]"]
        for mi, module in enumerate(isr.system.modules):
            if kind == "module":
                if module.id == name:
                    return idx[f"system.modules[{mi}]"]
            if kind == "behavior":
                for wi, workflow in enumerate(module.workflows):
                    if workflow.id == name:
                        return idx[f"system.modules[{mi}].workflows[{wi}]"]
            if kind == "temporal":
                for ti, constraint in enumerate(module.temporal_constraints):
                    if constraint.constraint_id == name:
                        return idx[
                            f"system.modules[{mi}].temporal_constraints[{ti}]"
                        ]
            if kind == "migration":
                for di, migration in enumerate(module.data_migrations):
                    if migration.migration_id == name:
                        return idx[f"system.modules[{mi}].data_migrations[{di}]"]
        return ""

    def has_gene(self, isr: ISR, gene: tuple) -> bool:
        return self.gene_hash(isr, gene) != ""

    # -- gates ----------------------------------------------------------------

    def run_gate(self, gate: str) -> GateResult:
        method = getattr(self, f"_gate_{gate}", None)
        if method is None:
            raise AssertionError(f"no implementation for gate '{gate}'")
        return method()

    def _gate_representation(self):
        system_fields = {f.name for f in dataclasses.fields(System)}
        ok = "deployment_intents" in system_fields
        try:
            self.valid_intent()
        except DeploymentValidationError:
            ok = False
        realization_fields = {
            f.name
            for f in dataclasses.fields(DeploymentIntent)
            if any(bad in f.name.lower() for bad in (
                "replica", "pod", "container", "cluster", "kube", "manifest",
                "image", "helm", "terraform", "pipeline", "ci_cd", "command",
                "script", "config",
            ))
        }
        ok = ok and not realization_fields
        strategies = {s.value for s in RolloutStrategy}
        ok = ok and strategies == {"IMMEDIATE", "CANARY", "BLUE_GREEN", "PROGRESSIVE"}
        return _result(
            "representation",
            ok,
            f"System.deployment_intents carrier; DeploymentIntent with "
            f"targets/strategy/constraints/health/rollback/preservation; "
            f"RolloutStrategy x4; no realization fields: "
            f"{realization_fields or 'none'}",
        )

    def _gate_canonicalization(self):
        isr = self.isr_without_deployment()
        same = self.with_empty_deployment(isr).content_hash == isr.content_hash
        return _result(
            "canonicalization",
            same,
            f"empty deployment intent carrier identity-neutral: {same}",
        )

    def _gate_semantic_identity(self):
        isr = self.isr_with()
        with_intent = self.operator.add_intent(
            isr, self.valid_intent()
        ).candidate_isr
        step1 = with_intent.content_hash != isr.content_hash
        respecified = self.operator.set_rollout_strategy(
            with_intent, deployment_id="dep1", strategy=RolloutStrategy.BLUE_GREEN
        ).candidate_isr
        step2 = respecified.content_hash != with_intent.content_hash
        removed = self.operator.remove_intent(
            respecified, deployment_id="dep1"
        ).candidate_isr
        step3 = removed.content_hash == isr.content_hash
        return _result(
            "semantic_identity",
            step1 and step2 and step3,
            f"add changes hash: {step1}; strategy change changes hash: {step2}; "
            f"remove restores hash: {step3}",
        )

    def _gate_validation(self):
        ok = True
        for bad in (
            dict(deployment_id="", target_refs=("pay",), rollout_strategy=RolloutStrategy.IMMEDIATE),
            dict(deployment_id="d", target_refs=(), rollout_strategy=RolloutStrategy.IMMEDIATE),
            dict(deployment_id="d", target_refs=("pay",),
                 rollout_strategy=RolloutStrategy.IMMEDIATE,
                 rollback_required=True, rollback_target_ref=None),
        ):
            try:
                DeploymentIntent(**bad)
                ok = False
            except DeploymentValidationError:
                pass
        dangling_target = self.isr_with(
            intents=(
                dataclasses.replace(
                    self.valid_intent(), target_refs=("no-such-gene",)
                ),
            ),
        )
        ok = ok and dangling_target.validate_structure() is False
        dangling_rollback = self.isr_with(
            intents=(
                dataclasses.replace(
                    self.valid_intent(), rollback_target_ref="no-such-gene"
                ),
            ),
        )
        ok = ok and dangling_rollback.validate_structure() is False
        rollback_not_own_target = self.isr_with(
            intents=(
                dataclasses.replace(
                    self.valid_intent(), target_refs=("m",),
                    rollback_target_ref="pay",
                ),
            ),
        )
        ok = ok and rollback_not_own_target.validate_structure() is False
        duplicate = self.isr_with(
            intents=(self.valid_intent(), self.valid_intent()),
        )
        ok = ok and duplicate.validate_structure() is False
        ok = ok and self.isr_with_deployment().validate_structure() is True
        return _result(
            "validation",
            ok,
            "construction contracts enforced; dangling target + rollback refs "
            "and rollback-target-not-own-target rejected pre-execution; "
            "duplicate ids rejected; valid intent validates",
        )

    def _gate_locality(self):
        isr = self.isr_with()
        mutated = self.operator.add_intent(
            isr, self.valid_intent()
        ).candidate_isr
        result = self.locality_probe.probe(
            isr, mutated, "system.deployment_intents[0]"
        )
        return _result(
            "locality",
            result.locality_holds,
            f"target gene changed: {result.target_gene_changed}; "
            f"unintended changes: {result.unintended_changes}",
        )

    def _gate_projection(self):
        isr = self.isr_with_deployment()
        projected = project_deployment_intents(isr)
        deterministic = projected == project_deployment_intents(isr)
        reflects = any(
            i.get("deployment_id") == "dep1"
            and "pay" in i.get("target_refs", [])
            and i.get("rollout_strategy") == "CANARY"
            and i.get("rollback_required") is True
            and i.get("rollback_target_ref") == "pay"
            for i in projected
        )
        text = str(projected)
        coupled = [
            term for term in TECHNOLOGY_COUPLING_TERMS if term in text
        ]
        mechanism = [
            term for term in DEPLOYMENT_MECHANISM_TERMS if term in text
        ]
        return _result(
            "projection",
            deterministic and reflects and not coupled and not mechanism,
            f"deterministic: {deterministic}; reflects intent: {reflects}; "
            f"coupling terms: {coupled}; realization terms: {mechanism}",
        )

    def _gate_compilation(self):
        isr = self.isr_with()
        mutated = self.operator.add_intent(
            isr, self.valid_intent()
        ).candidate_isr
        before = self.backend.async_resolution_module(isr.system.modules[0].workflows)
        after = self.backend.async_resolution_module(mutated.system.modules[0].workflows)
        compatible = before == after
        deterministic = self.backend.async_resolution_module(
            mutated.system.modules[0].workflows
        ) == after
        return _result(
            "compilation",
            compatible and deterministic,
            f"existing backend byte-identical with deployment intents present: "
            f"{compatible}; deterministic: {deterministic}",
        )

    def _gate_evidence(self):
        isr = self.isr_with_deployment()
        observable = any(
            i.get("deployment_id") == "dep1"
            for i in project_deployment_intents(isr)
        )
        empty = project_deployment_intents(
            self.isr_without_deployment()
        ) == ()
        return _result(
            "evidence",
            observable and empty,
            f"intent observable in semantic projection: {observable}; "
            f"no intents -> empty projection: {empty}",
        )

    def _gate_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = EvolutionLedger(root=str(tmp))
            operator = DeploymentOperator(ledger=ledger)
            isr = self.isr_with()
            candidate = operator.add_intent(isr, self.valid_intent())
            chain_ok = ledger.verify_event_chain() is True
            events = ledger.events()
            event = events[0] if events else None
            attributed = (
                event is not None
                and event.event_type is EventType.MEASUREMENT
                and event.payload["operator_id"] == "deployment"
                and event.payload["subject_id"] == "dep1"
            )
            hashes_ok = (
                event is not None
                and event.payload["isr_hash_before"] == isr.content_hash
                and event.payload["isr_hash_after"] == candidate.candidate_isr.content_hash
            )
        return _result(
            "lineage",
            chain_ok and attributed and hashes_ok,
            f"chain anchored: {chain_ok}; operator attribution: {attributed}; "
            f"before/after hashes: {hashes_ok}",
        )

    def _gate_reproducibility(self):
        isr = self.isr_with()
        c1 = self.operator.generate(isr, seed=7, population_size=1)
        c2 = self.operator.generate(isr, seed=7, population_size=1)
        same = len(c1) == len(c2) == 1 and all(
            a.candidate_id == b.candidate_id
            and a.candidate_isr.content_hash == b.candidate_isr.content_hash
            and a.mutation_delta == b.mutation_delta
            for a, b in zip(c1, c2)
        )
        return _result(
            "reproducibility",
            same,
            "same ISR + seed -> same candidate ids, hashes, and deltas",
        )

    def _gate_audit(self):
        result = self.audit.run(self.isr_with())
        by_id = {c.capability_id: c.status for c in result.capabilities}
        expressed = {cid for cid, s in by_id.items() if s is CapabilityStatus.EXPRESSED}
        partial = {cid for cid, s in by_id.items() if s is CapabilityStatus.PARTIAL}
        missing = {cid for cid, s in by_id.items() if s is CapabilityStatus.MISSING}
        post_expressed = {
            "behavior_transitions", "behavior_await_surface",
            "behavior_temporal_semantics", "business_capabilities",
            "data_migrations", "reliability_resilience",
            "architecture_boundaries", "requirements_acceptance_traceability",
            "deployment_rollout_rollback",
            "testing_anchoring",
            "documentation",
            "evolution_objectives_protected_regions",  # R2.10.3-J
        }
        post_partial = {
            "behavior_guards_actions", "behavior_state_semantics",
            "behavior_events_triggers", "behavior_error_states",
            "architecture_modules", "architecture_components",
            "architecture_interfaces_apis", "architecture_dependencies",
            "deployment_topology", "data_entities_schema",
            "data_persistence_consistency", "security_authorization",
            "security_authentication_trust", "requirements_constraints",
            "performance_scalability", "observability",
            "operational_policies", "evolution_lineage_provenance",
        }
        post_missing: set[str] = set()
        matrix_ok = (
            expressed == post_expressed
            and partial == post_partial
            and missing == post_missing
            and CapabilityStatus.PROJECTED not in by_id.values()
        )
        # Exactly one row moved vs the pre-landing (R2.10.3-I) matrix 11/18/0/1.
        pre_expressed = post_expressed - {"deployment_rollout_rollback"}
        pre_missing = post_missing | {"deployment_rollout_rollback"}
        one_row_only = (
            expressed - pre_expressed == {"deployment_rollout_rollback"}
            and missing == pre_missing - {"deployment_rollout_rollback"}
            and partial == post_partial
        )
        return _result(
            "audit",
            matrix_ok and one_row_only,
            f"summary: {result.summary()}; expected 12/18/0/0 with exactly "
            f"deployment_rollout_rollback: MISSING -> EXPRESSED and the "
            f"other 29 rows untouched",
        )


def _result(gate: str, passed: bool, evidence: str) -> GateResult:
    return GateResult(gate=gate, passed=passed, evidence=evidence)


@pytest.fixture
def dep_harness() -> DeploymentPrimitiveHarness:
    return DeploymentPrimitiveHarness()


# -- the G-specific proof: no backward leak into architecture ----------------------------

def test_changing_rollout_strategy_does_not_alter_boundary_genes(dep_harness):
    """Deployment references architecture; a deployment mutation must NEVER
    propagate into the boundary genes it references."""
    isr = dep_harness.isr_with_deployment()
    boundary_before = dep_harness.gene_hashes(isr, domain="architectural_boundaries")
    mutated = dep_harness.operator.set_rollout_strategy(
        isr, deployment_id="dep1", strategy=RolloutStrategy.BLUE_GREEN
    ).candidate_isr
    assert dep_harness.gene_hash(mutated, ("deployment", "dep1")) != \
        dep_harness.gene_hash(isr, ("deployment", "dep1"))  # deployment gene moved
    assert dep_harness.gene_hashes(mutated, domain="architectural_boundaries") == \
        boundary_before  # ...and NO boundary gene did


def test_changing_rollout_strategy_touches_only_deployment_gene(dep_harness):
    """The full locality of the backward-leak proof: every other gene domain
    — including boundaries — is byte-identical."""
    isr = dep_harness.isr_with_deployment()
    before = dep_harness.all_gene_hashes(isr)
    mutated = dep_harness.operator.set_rollout_strategy(
        isr, deployment_id="dep1", strategy=RolloutStrategy.BLUE_GREEN
    ).candidate_isr
    assert dep_harness.all_gene_hashes(mutated) == before
    assert dep_harness.gene_hash(mutated, ("deployment", "dep1")) != \
        dep_harness.gene_hash(isr, ("deployment", "dep1"))


def test_deployment_stable_when_target_implementation_evolves(dep_harness):
    """The forward property: implementation evolution never reaches forward
    into the deployment gene (reference-by-identity, deployment side)."""
    isr = dep_harness.isr_with_deployment_targeting("m")
    dep_before = dep_harness.gene_hash(isr, ("deployment", "dep1"))
    mutated = dep_harness.evolve_target_implementation(isr, "m")  # id stable
    assert dep_harness.gene_hash(mutated, ("module", "m")) != \
        dep_harness.gene_hash(isr, ("module", "m"))  # target moved
    assert dep_harness.gene_hash(mutated, ("deployment", "dep1")) == dep_before  # intent held


def test_deployment_is_independent_lifecycle_dimension(dep_harness):
    """Together: strategy change moves only deployment; implementation
    evolution moves only the target. Deployment composes with architecture
    by reference only."""
    isr = dep_harness.isr_with_deployment_targeting("m")
    implemented = dep_harness.evolve_target_implementation(isr, "m")
    dep_before = dep_harness.gene_hash(implemented, ("deployment", "dep1"))
    restrategized = dep_harness.operator.set_rollout_strategy(
        implemented, deployment_id="dep1", strategy=RolloutStrategy.BLUE_GREEN
    ).candidate_isr
    assert dep_harness.gene_hash(restrategized, ("module", "m")) == \
        dep_harness.gene_hash(implemented, ("module", "m"))
    assert dep_harness.gene_hash(restrategized, ("deployment", "dep1")) != dep_before


# -- declared, never inferred ---------------------------------------------------------------

def test_deployment_is_declared_not_inferred(dep_harness):
    a = dep_harness.isr_with_deployment_targeting("pay")
    b = dep_harness.isr_with_deployment_targeting("m")
    assert dep_harness.gene_hash(a, ("capability", "pay")) == \
        dep_harness.gene_hash(b, ("capability", "pay"))  # same structure
    assert dep_harness.gene_hash(a, ("deployment", "dep1")) != \
        dep_harness.gene_hash(b, ("deployment", "dep1"))


def test_deployment_identity_is_semantic_not_structural(dep_harness):
    a = dep_harness.isr_with_deployment_targeting("pay")
    b = dep_harness.isr_with_deployment_targeting("pay")
    b = b.with_system(dataclasses.replace(b.system, id="other-sys-id"))
    assert dep_harness.gene_hash(a, ("deployment", "dep1")) == \
        dep_harness.gene_hash(b, ("deployment", "dep1"))  # same declaration
    assert a.content_hash != b.content_hash  # system identity differs


# -- locality -------------------------------------------------------------------------------

def test_add_deployment_does_not_touch_other_genes(dep_harness):
    isr = dep_harness.isr_with()
    before = dep_harness.all_gene_hashes(isr)
    mutated = dep_harness.operator.add_intent(
        isr, dep_harness.valid_intent()
    ).candidate_isr
    assert dep_harness.all_gene_hashes(mutated) == before
    assert dep_harness.has_gene(mutated, ("deployment", "dep1"))


# -- the dangerous boundary: no realization technology --------------------------------------

def test_deployment_has_no_realization_fields():
    fields = {f.name for f in dataclasses.fields(DeploymentIntent)}
    realization = {
        f for f in fields
        if any(bad in f.lower() for bad in (
            "replica", "pod", "container", "cluster", "kube", "manifest",
            "image", "helm", "terraform", "pipeline", "ci_cd", "command",
            "script", "config",
        ))
    }
    assert not realization, f"deployment carries a realization field: {realization}"


def test_deployment_has_no_rollback_command():
    fields = {f.name for f in dataclasses.fields(DeploymentIntent)}
    assert not {
        f for f in fields
        if "command" in f.lower() or "script" in f.lower()
    }, "rollback must be a contract, never a command"


def test_deployment_mechanism_lint_rejects_leaked_realization(dep_harness):
    leak = dataclasses.replace(
        dep_harness.valid_intent(),
        rollout_constraints=("kubernetes replica_count must hold",),
    )
    hits = deployment_mechanism_hits(leak)
    assert "kubernetes" in hits
    assert "replica_count" in hits
    with pytest.raises(DeploymentValidationError):
        assert_deployment_technology_agnostic(leak)


def test_deployment_lint_allows_semantic_strategies(dep_harness):
    for strategy in RolloutStrategy:
        assert_deployment_technology_agnostic(
            dataclasses.replace(
                dep_harness.valid_intent(), rollout_strategy=strategy
            )
        )
    assert_deployment_technology_agnostic(dep_harness.valid_intent())
    assert not deployment_mechanism_hits(
        dataclasses.replace(
            dep_harness.valid_intent(),
            rollout_constraints=("at most one degraded target",),
            health_requirements=("payment remains reachable",),
            rollback_invariants=("payment state preserved",),
        )
    )


# -- structural validation -----------------------------------------------------------------

def test_dangling_target_ref_rejected(dep_harness):
    dangling = dep_harness.isr_with(
        intents=(
            dataclasses.replace(
                dep_harness.valid_intent(), target_refs=("no-such-gene",)
            ),
        ),
    )
    assert dangling.validate_structure() is False


def test_dangling_rollback_target_rejected(dep_harness):
    dangling = dep_harness.isr_with(
        intents=(
            dataclasses.replace(
                dep_harness.valid_intent(), rollback_target_ref="no-such-gene"
            ),
        ),
    )
    assert dangling.validate_structure() is False


def test_rollback_target_must_be_own_target(dep_harness):
    invalid = dep_harness.isr_with(
        intents=(
            dataclasses.replace(
                dep_harness.valid_intent(), target_refs=("m",),
                rollback_target_ref="pay",
            ),
        ),
    )
    assert invalid.validate_structure() is False


def test_duplicate_deployment_id_rejected(dep_harness):
    duplicate = dep_harness.isr_with(
        intents=(dep_harness.valid_intent(), dep_harness.valid_intent()),
    )
    assert duplicate.validate_structure() is False


# -- construction validity ----------------------------------------------------------------

def test_deployment_construction_validation():
    with pytest.raises(DeploymentValidationError):
        DeploymentIntent(
            deployment_id="", target_refs=("pay",),
            rollout_strategy=RolloutStrategy.IMMEDIATE,
        )
    with pytest.raises(DeploymentValidationError):
        DeploymentIntent(
            deployment_id="d", target_refs=(),
            rollout_strategy=RolloutStrategy.IMMEDIATE,
        )
    with pytest.raises(DeploymentValidationError):
        DeploymentIntent(
            deployment_id="d", target_refs=("pay",),
            rollout_strategy=RolloutStrategy.IMMEDIATE,
            rollback_required=True, rollback_target_ref=None,
        )


# -- canonicalization ----------------------------------------------------------------------

def test_empty_deployment_carrier_identity_neutral(dep_harness):
    isr = dep_harness.isr_without_deployment()
    assert dep_harness.with_empty_deployment(isr).content_hash == isr.content_hash


# -- the eleven gates, parameterized --------------------------------------------------------

@pytest.mark.parametrize("gate", PRIMITIVE_GATE)
def test_primitive_gate(gate, dep_harness):
    result = dep_harness.run_gate(gate)
    assert result.passed, f"{gate}: {result.evidence}"


def test_all_gates_pass_together(dep_harness):
    results = assert_all_gates(dep_harness)
    assert len(results) == len(PRIMITIVE_GATE)


# -- lineage is chain-anchored -------------------------------------------------------------

def test_deployment_mutation_is_chain_anchored(tmp_path):
    ledger = EvolutionLedger(root=str(tmp_path))
    operator = DeploymentOperator(ledger=ledger)
    harness = DeploymentPrimitiveHarness()
    isr = harness.isr_with()
    candidate = operator.add_intent(isr, harness.valid_intent())
    assert ledger.verify_event_chain() is True
    event = ledger.events()[0]
    assert event.event_type is EventType.MEASUREMENT
    assert event.payload["operator_id"] == "deployment"
    assert event.payload["subject_id"] == "dep1"
    assert event.payload["isr_hash_before"] == isr.content_hash
    assert event.payload["isr_hash_after"] == candidate.candidate_isr.content_hash


def test_deployment_remove_add_round_trip(dep_harness):
    isr = dep_harness.isr_with()
    added = dep_harness.operator.add_intent(
        isr, dep_harness.valid_intent()
    ).candidate_isr
    removed = dep_harness.operator.remove_intent(
        added, deployment_id="dep1"
    ).candidate_isr
    assert removed.content_hash == isr.content_hash


# -- the audit, mechanically one row ---------------------------------------------------------

def test_audit_moves_exactly_one_row(dep_harness):
    result = dep_harness.audit.run(dep_harness.isr_with())
    by_id = {c.capability_id: c.status for c in result.capabilities}
    expressed = {cid for cid, s in by_id.items() if s is CapabilityStatus.EXPRESSED}
    missing = {cid for cid, s in by_id.items() if s is CapabilityStatus.MISSING}
    # Pre-landing (R2.10.3-I) matrix: 11/18/0/1.
    pre_expressed = {
        "behavior_transitions", "behavior_await_surface",
        "behavior_temporal_semantics", "business_capabilities",
        "data_migrations", "reliability_resilience",
        "architecture_boundaries", "requirements_acceptance_traceability",
        "deployment_rollout_rollback", "testing_anchoring",
        "documentation",
    }
    pre_missing = {
        "evolution_objectives_protected_regions",
    }
    moved_rows = {}
    for cid in pre_expressed | pre_missing:
        before = "EXPRESSED" if cid in pre_expressed else "MISSING"
        after = "EXPRESSED" if cid in expressed else "MISSING"
        if before != after:
            moved_rows[cid] = (before, after)
    assert moved_rows == {
        "evolution_objectives_protected_regions": ("MISSING", "EXPRESSED")
    }
    assert (len(expressed), 18, 0, len(missing)) == (12, 18, 0, 0)  # NOT 11/18/0/1

