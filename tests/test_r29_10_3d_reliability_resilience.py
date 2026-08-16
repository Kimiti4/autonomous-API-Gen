"""R2.10.3-D — reliability_resilience: required behavior under failure.

The strictest boundary yet: reliability must express WHAT must remain true
when the system encounters failure, and be STRUCTURALLY incapable of
expressing HOW a technology achieves it. Retry counts, backoff strategies,
replica counts, restart policies, probes, queue names, replication commands,
Kubernetes/docker/systemd are compiler/backend/deployment realizations —
enforced by both a field-name test and a mechanism lint whose terms collide
with MECHANISMS, never with semantic behaviors (``failover_config`` is
rejected while ``IMMEDIATE_FAILOVER`` is fine).

Semantic dimensions modeled: failure modes (WHAT fails), required recovery
behavior (WHAT must happen — a backend may realize EVENTUAL_RECOVERY by
retry, queue replay, supervisor restart, or replica failover so long as the
declared contract holds), degradation policy (acceptable service STATE),
preservation invariants (hold during degraded operation), dependency
constraints, and recovery deadlines as semantic durations composing with the
temporal primitive's duration semantics WITHOUT embedding timer machinery in
either primitive.

Targets are explicit ISR identities (business capabilities from R2.10.3-B,
modules, services) — never inferred modules.

The audit gate embeds the pre-landing matrix (5/18/0/7 — after R2.10.3-C)
and asserts the delta is exactly {reliability_resilience: MISSING ->
EXPRESSED} -> 6/18/0/6.
"""
from __future__ import annotations

import dataclasses
import tempfile
from typing import Any

import pytest

from constitutional_architecture.isr.model import (
    BusinessCapability,
    DataMigrationIntent,
    CompatibilityPolicy,
    DegradationPolicy,
    Entity,
    FailureMode,
    ISR,
    Interface,
    InterfaceType,
    Module,
    RecoveryBehavior,
    RecoveryObjective,
    ReliabilityRequirement,
    ReliabilityValidationError,
    StateType,
    System,
    TemporalConstraint,
    TemporalConstraintKind,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)
from constitutional_architecture.isr.semantics.projection import canonicalize
from constitutional_architecture.isr.semantics.reliability import (
    RELIABILITY_MECHANISM_TERMS,
    assert_reliability_technology_agnostic,
    project_reliability_requirements,
    reliability_mechanism_hits,
)
from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend
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
from tiannara.application.evolution.reliability_mutation import ReliabilityOperator


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


class ReliabilityPrimitiveHarness:
    """The eleven-gate harness for reliability_resilience."""

    primitive_id = "reliability_resilience"

    def __init__(self) -> None:
        self.audit = ISRCapabilityAudit()
        self.operator = ReliabilityOperator()
        self.locality_probe = MutationLocalityProbe()
        self.backend = FastAPIHexagonalBackend()

    # -- recipes ------------------------------------------------------------

    def valid_requirement(self) -> ReliabilityRequirement:
        return ReliabilityRequirement(
            requirement_id="r1",
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
            dependency_constraints=("pay recovery precedes settlement",),
        )

    def isr_with(
        self,
        requirements: tuple[ReliabilityRequirement, ...] = (),
        with_capability: bool = True,
        with_temporal: bool = True,
        with_migration: bool = True,
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
        return ISR(
            system=System(
                id="reliability-sys",
                name="ReliabilitySystem",
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
                reliability_requirements=requirements,
            )
        )

    def isr_without_reliability(self) -> ISR:
        return self.isr_with()

    def isr_with_behavior_capabilities_temporal_migrations(self) -> ISR:
        return self.isr_with()

    def with_empty_reliability(self, isr: ISR) -> ISR:
        return isr.with_system(
            dataclasses.replace(isr.system, reliability_requirements=())
        )

    # -- gene addressing ------------------------------------------------------

    def all_gene_hashes(self, isr: ISR) -> dict[str, str]:
        """Every gene except the reliability gene class."""
        return {
            path: h
            for path, h in gene_index(isr).items()
            if "reliability_requirements" not in path
        }

    def gene_hash(self, isr: ISR, gene: tuple) -> str:
        """(\"reliability\", rid) / (\"entity\", eid) / (\"behavior\", wf_id) /
        (\"capability\", cid) / (\"temporal\", cid) / (\"migration\", mid)."""
        idx = gene_index(isr)
        kind, name = gene
        if kind == "reliability":
            for ri, requirement in enumerate(isr.system.reliability_requirements):
                if requirement.requirement_id == name:
                    return idx[f"system.reliability_requirements[{ri}]"]
        for mi, module in enumerate(isr.system.modules):
            if kind == "entity":
                for ei, entity in enumerate(module.entities):
                    if entity.id == name:
                        return idx[f"system.modules[{mi}].entities[{ei}]"]
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
        if kind == "capability":
            for ci, capability in enumerate(isr.system.business_capabilities):
                if capability.capability_id == name:
                    return idx[f"system.business_capabilities[{ci}]"]
        return ""

    def has_gene(self, isr: ISR, gene: tuple) -> bool:
        return self.gene_hash(isr, gene) != ""

    def entity_genes_identical(self, a: ISR, b: ISR) -> bool:
        a_hash = {p: h for p, h in self.all_gene_hashes(a).items() if ".entities[" in p}
        b_hash = {p: h for p, h in self.all_gene_hashes(b).items() if ".entities[" in p}
        return a_hash == b_hash

    # -- gates ----------------------------------------------------------------

    def run_gate(self, gate: str) -> GateResult:
        method = getattr(self, f"_gate_{gate}", None)
        if method is None:
            raise AssertionError(f"no implementation for gate '{gate}'")
        return method()

    def _gate_representation(self):
        system_fields = {f.name for f in dataclasses.fields(System)}
        ok = "reliability_requirements" in system_fields
        try:
            self.valid_requirement()
            ok = ok and True
        except ReliabilityValidationError:
            ok = False
        modes = {m.value for m in FailureMode}
        ok = ok and modes == {
            "TRANSIENT_DEPENDENCY_FAILURE", "PERMANENT_DEPENDENCY_FAILURE",
            "RESOURCE_EXHAUSTION", "PARTIAL_CAPACITY_LOSS",
            "DATA_INTEGRITY_VIOLATION", "CASCADE_FAILURE",
        }
        mechanism_fields = {
            f.name
            for f in dataclasses.fields(ReliabilityRequirement)
            if any(bad in f.name.lower() for bad in (
                "retry", "backoff", "replica", "restart", "probe", "queue",
                "circuit"))
        }
        return _result(
            "representation",
            ok and not mechanism_fields,
            f"System.reliability_requirements carrier; ReliabilityRequirement "
            f"with six failure modes; no mechanism fields: {mechanism_fields or 'none'}",
        )

    def _gate_canonicalization(self):
        isr = self.isr_without_reliability()
        same = self.with_empty_reliability(isr).content_hash == isr.content_hash
        return _result(
            "canonicalization",
            same,
            f"empty reliability carrier identity-neutral: {same}",
        )

    def _gate_semantic_identity(self):
        isr = self.isr_with()
        with_requirement = self.operator.add_requirement(
            isr, self.valid_requirement()
        ).candidate_isr
        step1 = with_requirement.content_hash != isr.content_hash
        repolicyed = self.operator.set_degradation_policy(
            with_requirement,
            requirement_id="r1",
            policy=DegradationPolicy.PARTIAL_SERVICE,
        ).candidate_isr
        step2 = repolicyed.content_hash != with_requirement.content_hash
        removed = self.operator.remove_requirement(
            repolicyed, requirement_id="r1"
        ).candidate_isr
        step3 = removed.content_hash == isr.content_hash
        return _result(
            "semantic_identity",
            step1 and step2 and step3,
            f"add changes hash: {step1}; degradation change changes hash: {step2}; "
            f"remove restores hash: {step3}",
        )

    def _gate_validation(self):
        ok = True
        for bad in (
            dict(requirement_id="", target_refs=("pay",),
                 failure_modes=(FailureMode.TRANSIENT_DEPENDENCY_FAILURE,)),
            dict(requirement_id="r", target_refs=(),
                 failure_modes=(FailureMode.TRANSIENT_DEPENDENCY_FAILURE,)),
            dict(requirement_id="r", target_refs=("pay",), failure_modes=()),
        ):
            try:
                ReliabilityRequirement(**bad)
                ok = False
            except ReliabilityValidationError:
                pass
        try:
            RecoveryObjective(
                failure_mode=FailureMode.TRANSIENT_DEPENDENCY_FAILURE,
                required_behavior=RecoveryBehavior.EVENTUAL_RECOVERY,
                max_recovery_duration_ms=-1,
            )
            ok = False
        except ReliabilityValidationError:
            pass
        dangling = self.isr_with(
            requirements=(
                dataclasses.replace(
                    self.valid_requirement(), target_refs=("no-such-capability",)
                ),
            )
        )
        ok = ok and dangling.validate_structure() is False
        undeclared = self.isr_with(
            requirements=(
                dataclasses.replace(
                    self.valid_requirement(),
                    failure_modes=(FailureMode.TRANSIENT_DEPENDENCY_FAILURE,),
                    recovery_objectives=(
                        RecoveryObjective(
                            failure_mode=FailureMode.CASCADE_FAILURE,
                            required_behavior=RecoveryBehavior.GRACEFUL_DEGRADATION,
                        ),
                    ),
                ),
            )
        )
        ok = ok and undeclared.validate_structure() is False
        contradictory = self.isr_with(
            requirements=(
                dataclasses.replace(
                    self.valid_requirement(),
                    recovery_objectives=(
                        RecoveryObjective(
                            failure_mode=FailureMode.TRANSIENT_DEPENDENCY_FAILURE,
                            required_behavior=RecoveryBehavior.EVENTUAL_RECOVERY,
                        ),
                        RecoveryObjective(
                            failure_mode=FailureMode.TRANSIENT_DEPENDENCY_FAILURE,
                            required_behavior=RecoveryBehavior.IMMEDIATE_FAILOVER,
                        ),
                    ),
                ),
            )
        )
        ok = ok and contradictory.validate_structure() is False
        duplicate = self.isr_with(
            requirements=(self.valid_requirement(), self.valid_requirement())
        )
        ok = ok and duplicate.validate_structure() is False
        return _result(
            "validation",
            ok,
            "empty id / no targets / no failure modes / negative duration rejected "
            "at construction; dangling targets, undeclared-mode objectives, "
            "contradictory recovery, duplicate ids rejected pre-execution",
        )

    def _gate_locality(self):
        isr = self.isr_with()
        mutated = self.operator.add_requirement(
            isr, self.valid_requirement()
        ).candidate_isr
        result = self.locality_probe.probe(
            isr, mutated, "system.reliability_requirements[0]"
        )
        return _result(
            "locality",
            result.locality_holds,
            f"target gene changed: {result.target_gene_changed}; "
            f"unintended changes: {result.unintended_changes}",
        )

    def _gate_projection(self):
        isr = self.isr_with(requirements=(self.valid_requirement(),))
        projected = project_reliability_requirements(isr)
        deterministic = projected == project_reliability_requirements(isr)
        reflects = any(
            r.get("requirement_id") == "r1"
            and "pay" in r.get("target_refs", [])
            and "TRANSIENT_DEPENDENCY_FAILURE"
            in r.get("failure_modes", [])
            and r.get("degradation_policy") == "NO_DEGRADATION"
            for r in projected
        )
        text = str(projected)
        coupled = [
            term for term in TECHNOLOGY_COUPLING_TERMS if term in text
        ]
        mechanism = [
            term for term in RELIABILITY_MECHANISM_TERMS if term in text
        ]
        return _result(
            "projection",
            deterministic and reflects and not coupled and not mechanism,
            f"deterministic: {deterministic}; reflects intent: {reflects}; "
            f"coupling terms: {coupled}; mechanism terms: {mechanism}",
        )

    def _gate_compilation(self):
        isr = self.isr_with()
        mutated = self.operator.add_requirement(
            isr, self.valid_requirement()
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
            f"existing backend byte-identical with reliability requirements "
            f"present: {compatible}; deterministic: {deterministic}",
        )

    def _gate_evidence(self):
        isr = self.isr_with(requirements=(self.valid_requirement(),))
        observable = any(
            r.get("requirement_id") == "r1"
            for r in project_reliability_requirements(isr)
        )
        empty = project_reliability_requirements(
            self.isr_without_reliability()
        ) == ()
        return _result(
            "evidence",
            observable and empty,
            f"requirement observable in semantic projection: {observable}; "
            f"no requirements -> empty projection: {empty}",
        )

    def _gate_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = EvolutionLedger(root=str(tmp))
            operator = ReliabilityOperator(ledger=ledger)
            isr = self.isr_with()
            candidate = operator.add_requirement(isr, self.valid_requirement())
            chain_ok = ledger.verify_event_chain() is True
            events = ledger.events()
            event = events[0] if events else None
            attributed = (
                event is not None
                and event.event_type is EventType.MEASUREMENT
                and event.payload["operator_id"] == "reliability"
                and event.payload["requirement_id"] == "r1"
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
        post_missing = {
            "architecture_boundaries", "deployment_rollout_rollback",
            "requirements_acceptance_traceability",
            "documentation", "testing_anchoring",
            "evolution_objectives_protected_regions",
        }
        matrix_ok = (
            expressed == post_expressed
            and partial == post_partial
            and missing == post_missing
            and CapabilityStatus.PROJECTED not in by_id.values()
        )
        # Exactly one row moved vs the pre-landing (R2.10.3-C) matrix 5/18/0/7.
        pre_expressed = post_expressed - {"reliability_resilience"}
        pre_missing = post_missing | {"reliability_resilience"}
        one_row_only = (
            expressed - pre_expressed == {"reliability_resilience"}
            and missing == pre_missing - {"reliability_resilience"}
            and partial == post_partial
        )
        return _result(
            "audit",
            matrix_ok and one_row_only,
            f"summary: {result.summary()}; expected 6/18/0/6 with exactly "
            f"reliability_resilience: MISSING -> EXPRESSED and the other 29 "
            f"rows untouched",
        )


def _result(gate: str, passed: bool, evidence: str) -> GateResult:
    return GateResult(gate=gate, passed=passed, evidence=evidence)


@pytest.fixture
def rel_harness() -> ReliabilityPrimitiveHarness:
    return ReliabilityPrimitiveHarness()


# -- locality -------------------------------------------------------------------

def test_add_reliability_does_not_touch_other_genes(rel_harness):
    isr = rel_harness.isr_with_behavior_capabilities_temporal_migrations()
    before = rel_harness.all_gene_hashes(isr)  # behavior, capability, temporal, migration, entity
    mutated = rel_harness.operator.add_requirement(
        isr, rel_harness.valid_requirement()
    ).candidate_isr
    assert rel_harness.all_gene_hashes(mutated) == before
    assert rel_harness.has_gene(mutated, ("reliability", "r1"))


def test_changing_recovery_objective_only_moves_reliability_gene(rel_harness):
    isr = rel_harness.isr_with(requirements=(rel_harness.valid_requirement(),))
    before = rel_harness.all_gene_hashes(isr)
    mutated = rel_harness.operator.add_recovery_objective(
        isr,
        requirement_id="r1",
        objective=RecoveryObjective(
            failure_mode=FailureMode.PERMANENT_DEPENDENCY_FAILURE,
            required_behavior=RecoveryBehavior.GRACEFUL_DEGRADATION,
        ),
    ).candidate_isr
    assert rel_harness.all_gene_hashes(mutated) == before  # only reliability gene moved
    assert rel_harness.gene_hash(mutated, ("reliability", "r1")) != \
        rel_harness.gene_hash(isr, ("reliability", "r1"))


# -- non-inference ---------------------------------------------------------------

def test_reliability_is_declared_not_inferred(rel_harness):
    a = rel_harness.isr_with(requirements=(
        rel_harness.valid_requirement(),  # TRANSIENT_DEPENDENCY_FAILURE
    ))
    b = rel_harness.isr_with(requirements=(
        dataclasses.replace(
            rel_harness.valid_requirement(),
            failure_modes=(FailureMode.CASCADE_FAILURE,),
        ),
    ))
    assert rel_harness.entity_genes_identical(a, b)  # same protected targets
    assert rel_harness.gene_hash(a, ("reliability", "r1")) != \
        rel_harness.gene_hash(b, ("reliability", "r1"))


def test_reliability_identity_is_semantic_not_structural(rel_harness):
    # Equivalent declarations over differently structured implementations:
    # the reliability gene is the declared contract, not the implementation.
    a = rel_harness.isr_with(
        requirements=(rel_harness.valid_requirement(),),
    )
    b = rel_harness.isr_with(
        requirements=(rel_harness.valid_requirement(),),
        with_migration=False,
    )
    assert rel_harness.gene_hash(a, ("reliability", "r1")) == \
        rel_harness.gene_hash(b, ("reliability", "r1"))
    assert a.content_hash != b.content_hash  # implementation differs


# -- failure-mode identity ----------------------------------------------------------

def test_distinct_failure_modes_are_distinct():
    assert canonicalize(FailureMode.TRANSIENT_DEPENDENCY_FAILURE) != \
        canonicalize(FailureMode.CASCADE_FAILURE)
    assert canonicalize(FailureMode.RESOURCE_EXHAUSTION) != \
        canonicalize(FailureMode.PARTIAL_CAPACITY_LOSS)


# -- target identity -------------------------------------------------------------------

def test_requirement_targets_explicit_identities(rel_harness):
    isr = rel_harness.isr_with(requirements=(rel_harness.valid_requirement(),))
    projected = project_reliability_requirements(isr)
    assert any("pay" in r.get("target_refs", []) for r in projected)
    dangling = rel_harness.isr_with(requirements=(
        dataclasses.replace(
            rel_harness.valid_requirement(), target_refs=("no-such-capability",)
        ),
    ))
    assert dangling.validate_structure() is False


# -- the dangerous boundary: no implementation mechanism --------------------------------

def test_reliability_has_no_mechanism_fields():
    fields = {f.name for f in dataclasses.fields(ReliabilityRequirement)}
    mechanism = {
        f for f in fields
        if any(bad in f.lower() for bad in (
            "retry", "backoff", "replica", "restart", "probe", "queue",
            "circuit"))
    }
    assert not mechanism, f"reliability carries a mechanism field: {mechanism}"


def test_reliability_mechanism_lint_rejects_leaked_mechanism(rel_harness):
    leak = dataclasses.replace(
        rel_harness.valid_requirement(),
        preservation_invariants=("kubernetes_probe ok", "retry_count 3"),
    )
    hits = reliability_mechanism_hits(leak)
    assert "kubernetes" in hits
    assert "retry_count" in hits
    with pytest.raises(ReliabilityValidationError):
        assert_reliability_technology_agnostic(leak)
    assert_reliability_technology_agnostic(rel_harness.valid_requirement())


def test_mechanism_terms_reject_mechanism_not_behavior(rel_harness):
    # The terms collide with MECHANISMS, never with semantic behaviors:
    # IMMEDIATE_FAILOVER (a behavior) is fine; failover_config is rejected.
    immediate = dataclasses.replace(
        rel_harness.valid_requirement(),
        failure_modes=(FailureMode.PERMANENT_DEPENDENCY_FAILURE,),
        recovery_objectives=(
            RecoveryObjective(
                failure_mode=FailureMode.PERMANENT_DEPENDENCY_FAILURE,
                required_behavior=RecoveryBehavior.IMMEDIATE_FAILOVER,
            ),
        ),
    )
    assert_reliability_technology_agnostic(immediate)
    leaked = dataclasses.replace(
        immediate,
        dependency_constraints=("failover_config for pay",),
    )
    hits = reliability_mechanism_hits(leaked)
    assert "failover_config" in hits
    with pytest.raises(ReliabilityValidationError):
        assert_reliability_technology_agnostic(leaked)


# -- invariant preservation -------------------------------------------------------------

def test_reliability_declares_preservation_invariants(rel_harness):
    requirement = rel_harness.valid_requirement()
    assert requirement.preservation_invariants == ("pay coherent",)
    projected = project_reliability_requirements(
        rel_harness.isr_with(requirements=(requirement,))
    )
    assert any(
        "pay coherent" in r.get("preservation_invariants", [])
        for r in projected
    )


# -- temporal composition (disjoint genes, shared duration semantics) ---------------------

def test_recovery_deadline_composes_with_temporal_without_timer(rel_harness):
    isr = rel_harness.isr_with()
    temporal_before = {
        p: h for p, h in rel_harness.all_gene_hashes(isr).items()
        if "temporal_constraints" in p
    }
    mutated = rel_harness.operator.add_requirement(
        isr, rel_harness.valid_requirement()  # 5000ms semantic deadline
    ).candidate_isr
    assert {
        p: h for p, h in rel_harness.all_gene_hashes(mutated).items()
        if "temporal_constraints" in p
    } == temporal_before
    objective = mutated.system.reliability_requirements[0].recovery_objectives[0]
    assert objective.max_recovery_duration_ms == 5000
    assert_reliability_technology_agnostic(mutated.system.reliability_requirements[0])


# -- structural validation ---------------------------------------------------------------

def test_dangling_target_rejected(rel_harness):
    dangling = rel_harness.isr_with(requirements=(
        dataclasses.replace(
            rel_harness.valid_requirement(), target_refs=("no-such-capability",)
        ),
    ))
    assert dangling.validate_structure() is False


def test_contradictory_recovery_objectives_rejected(rel_harness):
    contradictory = rel_harness.isr_with(requirements=(
        dataclasses.replace(
            rel_harness.valid_requirement(),
            recovery_objectives=(
                RecoveryObjective(
                    failure_mode=FailureMode.TRANSIENT_DEPENDENCY_FAILURE,
                    required_behavior=RecoveryBehavior.EVENTUAL_RECOVERY,
                ),
                RecoveryObjective(
                    failure_mode=FailureMode.TRANSIENT_DEPENDENCY_FAILURE,
                    required_behavior=RecoveryBehavior.IMMEDIATE_FAILOVER,
                ),
            ),
        ),
    ))
    assert contradictory.validate_structure() is False


def test_undeclared_failure_mode_objective_rejected(rel_harness):
    undeclared = rel_harness.isr_with(requirements=(
        dataclasses.replace(
            rel_harness.valid_requirement(),
            recovery_objectives=(
                RecoveryObjective(
                    failure_mode=FailureMode.CASCADE_FAILURE,
                    required_behavior=RecoveryBehavior.GRACEFUL_DEGRADATION,
                ),
            ),
        ),
    ))
    assert undeclared.validate_structure() is False


# -- construction validity -----------------------------------------------------------

def test_reliability_construction_validation():
    with pytest.raises(ReliabilityValidationError):
        ReliabilityRequirement(
            requirement_id="", target_refs=("pay",),
            failure_modes=(FailureMode.TRANSIENT_DEPENDENCY_FAILURE,),
        )
    with pytest.raises(ReliabilityValidationError):
        ReliabilityRequirement(
            requirement_id="r", target_refs=(),
            failure_modes=(FailureMode.TRANSIENT_DEPENDENCY_FAILURE,),
        )
    with pytest.raises(ReliabilityValidationError):
        ReliabilityRequirement(
            requirement_id="r", target_refs=("pay",), failure_modes=(),
        )
    with pytest.raises(ReliabilityValidationError):
        RecoveryObjective(
            failure_mode=FailureMode.TRANSIENT_DEPENDENCY_FAILURE,
            required_behavior=RecoveryBehavior.EVENTUAL_RECOVERY,
            max_recovery_duration_ms=-1,
        )


def test_recovery_objective_is_contract_not_mechanism(rel_harness):
    requirement = rel_harness.valid_requirement()
    objective = requirement.recovery_objectives[0]
    assert objective.failure_mode is FailureMode.TRANSIENT_DEPENDENCY_FAILURE
    assert objective.required_behavior is RecoveryBehavior.EVENTUAL_RECOVERY
    assert objective.max_recovery_duration_ms == 5000
    assert not any(
        bad in str(requirement).lower()
        for bad in ("retry_count", "max_retries", "backoff", "replica_count",
                    "restart_policy", "liveness_probe", "queue_name")
    )


# -- canonicalization ------------------------------------------------------------------

def test_empty_reliability_carrier_identity_neutral(rel_harness):
    isr = rel_harness.isr_without_reliability()
    assert rel_harness.with_empty_reliability(isr).content_hash == isr.content_hash


# -- the eleven gates, parameterized ------------------------------------------------------

@pytest.mark.parametrize("gate", PRIMITIVE_GATE)
def test_primitive_gate(gate, rel_harness):
    result = rel_harness.run_gate(gate)
    assert result.passed, f"{gate}: {result.evidence}"


def test_all_gates_pass_together(rel_harness):
    results = assert_all_gates(rel_harness)
    assert len(results) == len(PRIMITIVE_GATE)


# -- lineage is chain-anchored ------------------------------------------------------------

def test_reliability_mutation_is_chain_anchored(tmp_path):
    ledger = EvolutionLedger(root=str(tmp_path))
    operator = ReliabilityOperator(ledger=ledger)
    harness = ReliabilityPrimitiveHarness()
    isr = harness.isr_with()
    candidate = operator.add_requirement(isr, harness.valid_requirement())
    assert ledger.verify_event_chain() is True
    event = ledger.events()[0]
    assert event.event_type is EventType.MEASUREMENT
    assert event.payload["operator_id"] == "reliability"
    assert event.payload["requirement_id"] == "r1"
    assert event.payload["isr_hash_before"] == isr.content_hash
    assert event.payload["isr_hash_after"] == candidate.candidate_isr.content_hash


# -- remove restores identity ------------------------------------------------------------------

def test_remove_requirement_restores_semantic_identity(rel_harness):
    isr = rel_harness.isr_with()
    with_requirement = rel_harness.operator.add_requirement(
        isr, rel_harness.valid_requirement()
    ).candidate_isr
    removed = rel_harness.operator.remove_requirement(
        with_requirement, requirement_id="r1"
    ).candidate_isr
    assert removed.content_hash == isr.content_hash


# -- the audit, mechanically one row --------------------------------------------------------------

def test_audit_moves_exactly_one_row(rel_harness):
    result = rel_harness.audit.run(rel_harness.isr_with())
    by_id = {c.capability_id: c.status for c in result.capabilities}
    expressed = {cid for cid, s in by_id.items() if s is CapabilityStatus.EXPRESSED}
    missing = {cid for cid, s in by_id.items() if s is CapabilityStatus.MISSING}
    # Pre-landing (R2.10.3-C) matrix: 5/18/0/7.
    pre_expressed = {
        "behavior_transitions", "behavior_await_surface",
        "behavior_temporal_semantics", "business_capabilities",
        "data_migrations",
    }
    pre_missing = {
        "architecture_boundaries", "deployment_rollout_rollback",
        "requirements_acceptance_traceability", "reliability_resilience",
        "documentation", "testing_anchoring",
        "evolution_objectives_protected_regions",
    }
    moved_rows = {}
    for cid in pre_expressed | pre_missing:
        before = "EXPRESSED" if cid in pre_expressed else "MISSING"
        after = "EXPRESSED" if cid in expressed else "MISSING"
        if before != after:
            moved_rows[cid] = (before, after)
    assert moved_rows == {"reliability_resilience": ("MISSING", "EXPRESSED")}
    assert (len(expressed), 18, 0, len(missing)) == (6, 18, 0, 6)  # NOT 5/18/0/7