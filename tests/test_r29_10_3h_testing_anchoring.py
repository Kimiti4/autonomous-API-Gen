"""R2.10.3-H — testing_anchoring: the declaration side of the ISR<->evidence loop.

H closes the loop between the ISR's semantic obligations and the evaluation
boundary WITHOUT becoming a test-generation primitive — the inversion that
lets the testing layer define the software's meaning is the failure mode H
exists to avoid. Principle held since R2.8: **the ISR declares what evidence
must establish; the evaluation system determines how that evidence is
produced.** H is the declaration side, full stop.

A TestingAnchor declares which semantic obligation is demonstrated
(obligation_refs → F's AcceptanceCriterion ids), which genes are exercised
(subject_refs → behaviors/capabilities/requirements), what evidence must
establish (evidence_requirements), what must remain protected
(protection_policy), and whether the anchor is a fixed reference or follows
its subjects (authority). NO test file, function, framework, fixture,
marker, or execution mechanism — structurally impossible (field guard) and
gated (TESTING_MECHANISM_TERMS lint).

Scope holds: H does NOT evaluate (no is_satisfied, no verdict — structural
test); H does NOT wire obligation→anchor→evidence into the live evaluation
loop — obligation_refs RESOLVE against F's AcceptanceCriterion without
editing F (the F→H edge), binding is the evaluation system's follow-up.

The R2.8 connection: PROTECTED reuses R2.8.7's protected-evaluation-surface
semantics generalized into the ISR — a protected anchor's removal or
modification raises ConstitutionalViolation (the SAME violation E's
BoundaryOperator raises for protected boundaries). One protection mechanism
across primitives, not a parallel security model.

The audit gate embeds the pre-landing matrix (9/18/0/3 — after R2.10.3-G)
and asserts the delta is exactly {testing_anchoring: MISSING -> EXPRESSED}
-> 10/18/0/2.
"""
from __future__ import annotations

import dataclasses
import tempfile
from typing import Any

import pytest

from constitutional_architecture.isr.model import (
    AcceptanceCriterion,
    AnchorAuthority,
    ArchitecturalBoundary,
    BusinessCapability,
    CompatibilityPolicy,
    DataMigrationIntent,
    DegradationPolicy,
    DeploymentIntent,
    Entity,
    FailureMode,
    ISR,
    Interface,
    InterfaceType,
    Module,
    ObligationKind,
    ProtectionPolicy,
    RecoveryBehavior,
    RecoveryObjective,
    ReliabilityRequirement,
    Requirement,
    RolloutStrategy,
    StateType,
    System,
    TemporalConstraint,
    TemporalConstraintKind,
    TestingAnchor,
    TestingAnchorValidationError,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)
from constitutional_architecture.isr.semantics.testing_anchor import (
    TESTING_MECHANISM_TERMS,
    assert_testing_technology_agnostic,
    project_testing_anchors,
    testing_mechanism_hits as mechanism_hits,
)
from constitutional_architecture.validators import ConstitutionalViolation
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
from tiannara.application.evolution.testing_anchor_mutation import TestingAnchorOperator


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


class TestingAnchorPrimitiveHarness:
    """The eleven-gate harness for testing_anchoring."""

    primitive_id = "testing_anchoring"

    def __init__(self) -> None:
        self.audit = ISRCapabilityAudit()
        self.operator = TestingAnchorOperator()
        self.locality_probe = MutationLocalityProbe()
        self.backend = FastAPIHexagonalBackend()

    # -- recipes ------------------------------------------------------------

    def valid_anchor(self) -> TestingAnchor:
        return TestingAnchor(
            anchor_id="anchor1",
            subject_refs=("w1",),
            obligation_refs=("crit.cancel",),
            evidence_requirements=("ORDERING before authorization demonstrated",),
            protection_policy=ProtectionPolicy.EVOLVABLE,
            authority=AnchorAuthority.DERIVED,
        )

    def isr_with(
        self,
        anchors: tuple[TestingAnchor, ...] = (),
        with_deployment: bool = True,
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
        intents = (
            (
                DeploymentIntent(
                    deployment_id="dep1",
                    target_refs=("pay",),
                    rollout_strategy=RolloutStrategy.CANARY,
                    rollback_required=True,
                    rollback_target_ref="pay",
                    rollback_invariants=("payment state preserved",),
                ),
            )
            if with_deployment
            else ()
        )
        return ISR(
            system=System(
                id="ta-sys",
                name="TestingAnchorSystem",
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
                testing_anchors=anchors,
            )
        )

    def isr_without_anchors(self) -> ISR:
        return self.isr_with()

    def isr_with_anchor(self) -> ISR:
        return self.isr_with(anchors=(self.valid_anchor(),))

    def isr_with_protected_anchor(self, anchor_id: str = "anchor1") -> ISR:
        return self.isr_with(
            anchors=(
                dataclasses.replace(
                    self.valid_anchor(), protection_policy=ProtectionPolicy.PROTECTED
                ),
            )
        )

    def isr_with_anchor_on_subject(self, subject_id: str) -> ISR:
        return self.isr_with(
            anchors=(
                dataclasses.replace(
                    self.valid_anchor(), subject_refs=(subject_id,)
                ),
            )
        )

    def with_empty_anchors(self, isr: ISR) -> ISR:
        return isr.with_system(
            dataclasses.replace(isr.system, testing_anchors=())
        )

    def respecify_anchor(self, isr: ISR, anchor_id: str) -> ISR:
        return self.operator.respecify_anchor(
            isr,
            anchor_id=anchor_id,
            evidence_requirements=("evidence obligation respecified",),
        ).candidate_isr

    def evolve_subject_implementation(self, isr: ISR, workflow_id: str) -> ISR:
        """Mutate a subject's implementation while its identity is stable."""
        modules = []
        for module in isr.system.modules:
            workflows = tuple(
                dataclasses.replace(
                    w, description=f"implementation evolved under anchor {workflow_id}"
                )
                if w.id == workflow_id
                else w
                for w in module.workflows
            )
            module = dataclasses.replace(module, workflows=workflows)
            modules.append(module)
        return isr.with_system(
            dataclasses.replace(isr.system, modules=tuple(modules))
        )

    # -- gene addressing ------------------------------------------------------

    def all_gene_hashes(self, isr: ISR) -> dict[str, str]:
        """Every gene except the testing anchor gene class."""
        return {
            path: h
            for path, h in gene_index(isr).items()
            if "testing_anchors" not in path
        }

    def gene_hashes(self, isr: ISR, domain: str) -> dict[str, str]:
        return {p: h for p, h in gene_index(isr).items() if domain in p}

    def gene_hash(self, isr: ISR, gene: tuple) -> str:
        """("anchor", aid) / ("capability", cid) / ("module", mid) /
        ("behavior", wf_id) / ("boundary", bid) / ("reliability", rid) /
        ("requirement", rid) / ("criterion", cid) / ("deployment", did) /
        ("migration", mid) / ("temporal", cid)."""
        idx = gene_index(isr)
        kind, name = gene
        if kind == "anchor":
            for ai, anchor in enumerate(isr.system.testing_anchors):
                if anchor.anchor_id == name:
                    return idx[f"system.testing_anchors[{ai}]"]
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
        if kind == "deployment":
            for di, intent in enumerate(isr.system.deployment_intents):
                if intent.deployment_id == name:
                    return idx[f"system.deployment_intents[{di}]"]
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
        ok = "testing_anchors" in system_fields
        try:
            self.valid_anchor()
        except TestingAnchorValidationError:
            ok = False
        implementation_fields = {
            f.name
            for f in dataclasses.fields(TestingAnchor)
            if any(bad in f.name.lower() for bad in (
                "test_file", "function", "marker", "fixture", "command",
                "runner", "script", "satisfied", "verdict", "score",
                "execution", "framework",
            ))
        }
        ok = ok and not implementation_fields
        policies = {p.value for p in ProtectionPolicy}
        ok = ok and policies == {"PROTECTED", "EVOLVABLE"}
        authorities = {a.value for a in AnchorAuthority}
        ok = ok and authorities == {"AUTHORITATIVE", "DERIVED"}
        return _result(
            "representation",
            ok,
            f"System.testing_anchors carrier; TestingAnchor with "
            f"subjects/obligations/evidence/protection/authority; "
            f"ProtectionPolicy x2 + AnchorAuthority x2; no test-"
            f"implementation fields: {implementation_fields or 'none'}",
        )

    def _gate_canonicalization(self):
        isr = self.isr_without_anchors()
        same = self.with_empty_anchors(isr).content_hash == isr.content_hash
        return _result(
            "canonicalization",
            same,
            f"empty testing anchor carrier identity-neutral: {same}",
        )

    def _gate_semantic_identity(self):
        isr = self.isr_with()
        with_anchor = self.operator.add_anchor(
            isr, self.valid_anchor()
        ).candidate_isr
        step1 = with_anchor.content_hash != isr.content_hash
        respecified = self.respecify_anchor(with_anchor, "anchor1")
        step2 = respecified.content_hash != with_anchor.content_hash
        removed = self.operator.remove_anchor(
            respecified, anchor_id="anchor1"
        ).candidate_isr
        step3 = removed.content_hash == isr.content_hash
        return _result(
            "semantic_identity",
            step1 and step2 and step3,
            f"add changes hash: {step1}; respecify changes hash: {step2}; "
            f"remove restores hash: {step3}",
        )

    def _gate_validation(self):
        ok = True
        for bad in (
            dict(anchor_id="", subject_refs=("w1",)),
            dict(anchor_id="a", subject_refs=()),
        ):
            try:
                TestingAnchor(**bad)
                ok = False
            except TestingAnchorValidationError:
                pass
        dangling_subject = self.isr_with(
            anchors=(
                dataclasses.replace(
                    self.valid_anchor(), subject_refs=("no-such-gene",)
                ),
            ),
        )
        ok = ok and dangling_subject.validate_structure() is False
        dangling_obligation = self.isr_with(
            anchors=(
                dataclasses.replace(
                    self.valid_anchor(), obligation_refs=("no-such-criterion",)
                ),
            ),
        )
        ok = ok and dangling_obligation.validate_structure() is False
        duplicate = self.isr_with(
            anchors=(self.valid_anchor(), self.valid_anchor()),
        )
        ok = ok and duplicate.validate_structure() is False
        ok = ok and self.isr_with_anchor().validate_structure() is True
        return _result(
            "validation",
            ok,
            "construction contracts enforced; dangling subject + obligation "
            "refs rejected pre-execution; duplicate ids rejected; valid "
            "anchor validates",
        )

    def _gate_locality(self):
        isr = self.isr_with()
        mutated = self.operator.add_anchor(
            isr, self.valid_anchor()
        ).candidate_isr
        result = self.locality_probe.probe(
            isr, mutated, "system.testing_anchors[0]"
        )
        return _result(
            "locality",
            result.locality_holds,
            f"target gene changed: {result.target_gene_changed}; "
            f"unintended changes: {result.unintended_changes}",
        )

    def _gate_projection(self):
        isr = self.isr_with_anchor()
        projected = project_testing_anchors(isr)
        deterministic = projected == project_testing_anchors(isr)
        reflects = any(
            a.get("anchor_id") == "anchor1"
            and "w1" in a.get("subject_refs", [])
            and "crit.cancel" in a.get("obligation_refs", [])
            and a.get("protection_policy") == "EVOLVABLE"
            and a.get("authority") == "DERIVED"
            for a in projected
        )
        text = str(projected)
        coupled = [
            term for term in TECHNOLOGY_COUPLING_TERMS if term in text
        ]
        mechanism = [
            term for term in TESTING_MECHANISM_TERMS if term in text
        ]
        return _result(
            "projection",
            deterministic and reflects and not coupled and not mechanism,
            f"deterministic: {deterministic}; reflects anchoring: {reflects}; "
            f"coupling terms: {coupled}; mechanism terms: {mechanism}",
        )

    def _gate_compilation(self):
        isr = self.isr_with()
        mutated = self.operator.add_anchor(
            isr, self.valid_anchor()
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
            f"existing backend byte-identical with anchors present: "
            f"{compatible}; deterministic: {deterministic}",
        )

    def _gate_evidence(self):
        isr = self.isr_with_anchor()
        observable = any(
            a.get("anchor_id") == "anchor1"
            for a in project_testing_anchors(isr)
        )
        empty = project_testing_anchors(
            self.isr_without_anchors()
        ) == ()
        return _result(
            "evidence",
            observable and empty,
            f"anchor observable in semantic projection: {observable}; "
            f"no anchors -> empty projection: {empty}",
        )

    def _gate_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = EvolutionLedger(root=str(tmp))
            operator = TestingAnchorOperator(ledger=ledger)
            isr = self.isr_with()
            candidate = operator.add_anchor(isr, self.valid_anchor())
            chain_ok = ledger.verify_event_chain() is True
            events = ledger.events()
            event = events[0] if events else None
            attributed = (
                event is not None
                and event.event_type is EventType.MEASUREMENT
                and event.payload["operator_id"] == "testing_anchor"
                and event.payload["subject_id"] == "anchor1"
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
            "deployment_rollout_rollback", "testing_anchoring",
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
        pre_expressed = post_expressed - {"testing_anchoring"}
        pre_missing = post_missing | {"testing_anchoring"}
        one_row_only = (
            expressed - pre_expressed == {"testing_anchoring"}
            and missing == pre_missing - {"testing_anchoring"}
            and partial == post_partial
        )
        return _result(
            "audit",
            matrix_ok and one_row_only,
            f"summary: {result.summary()}; expected 12/18/0/0 with exactly "
            f"testing_anchoring: MISSING -> EXPRESSED and the other 29 rows "
            f"untouched",
        )


def _result(gate: str, passed: bool, evidence: str) -> GateResult:
    return GateResult(gate=gate, passed=passed, evidence=evidence)


@pytest.fixture
def ta_harness() -> TestingAnchorPrimitiveHarness:
    return TestingAnchorPrimitiveHarness()


# -- locality: changing testing intent moves only the testing gene --------------------------

def test_changing_anchor_only_moves_testing_gene(ta_harness):
    isr = ta_harness.isr_with_anchor()
    subject_before = ta_harness.gene_hashes(isr, domain="workflows")
    mutated = ta_harness.respecify_anchor(isr, "anchor1")
    assert ta_harness.gene_hash(mutated, ("anchor", "anchor1")) != \
        ta_harness.gene_hash(isr, ("anchor", "anchor1"))  # anchor moved
    assert ta_harness.gene_hashes(mutated, domain="workflows") == subject_before  # subjects held


def test_changing_anchor_touches_only_testing_gene(ta_harness):
    """The full locality of the proof: every other gene domain is byte-identical."""
    isr = ta_harness.isr_with_anchor()
    before = ta_harness.all_gene_hashes(isr)
    mutated = ta_harness.respecify_anchor(isr, "anchor1")
    assert ta_harness.all_gene_hashes(mutated) == before
    assert ta_harness.gene_hash(mutated, ("anchor", "anchor1")) != \
        ta_harness.gene_hash(isr, ("anchor", "anchor1"))


def test_add_anchor_does_not_touch_other_genes(ta_harness):
    isr = ta_harness.isr_with()
    before = ta_harness.all_gene_hashes(isr)
    mutated = ta_harness.operator.add_anchor(
        isr, ta_harness.valid_anchor()
    ).candidate_isr
    assert ta_harness.all_gene_hashes(mutated) == before
    assert ta_harness.has_gene(mutated, ("anchor", "anchor1"))


# -- reference-by-identity: implementation evolves, anchor holds ---------------------------

def test_anchor_stable_when_subject_implementation_evolves(ta_harness):
    isr = ta_harness.isr_with_anchor_on_subject("w1")
    anchor_before = ta_harness.gene_hash(isr, ("anchor", "anchor1"))
    mutated = ta_harness.evolve_subject_implementation(isr, "w1")  # id stable
    assert ta_harness.gene_hash(mutated, ("behavior", "w1")) != \
        ta_harness.gene_hash(isr, ("behavior", "w1"))  # subject moved
    assert ta_harness.gene_hash(mutated, ("anchor", "anchor1")) == anchor_before  # anchor held


def test_anchor_stable_when_capability_evolves(ta_harness):
    isr = ta_harness.isr_with_anchor_on_subject("pay")
    anchor_before = ta_harness.gene_hash(isr, ("anchor", "anchor1"))
    modules = []
    for module in isr.system.modules:
        workflows = tuple(
            dataclasses.replace(
                w, description="capability implementation evolved"
            )
            for w in module.workflows
        )
        module = dataclasses.replace(module, workflows=workflows)
        modules.append(module)
    evolved = isr.with_system(
        dataclasses.replace(isr.system, modules=tuple(modules))
    )
    assert ta_harness.gene_hash(evolved, ("behavior", "w1")) != \
        ta_harness.gene_hash(isr, ("behavior", "w1"))  # implementation moved
    assert ta_harness.gene_hash(evolved, ("anchor", "anchor1")) == anchor_before


# -- the R2.8 connection: PROTECTED anchors are constitutionally protected -----------------

def test_removing_protected_anchor_rejected(ta_harness):
    isr = ta_harness.isr_with_protected_anchor("anchor1")
    with pytest.raises(ConstitutionalViolation):
        ta_harness.operator.remove_anchor(isr, anchor_id="anchor1")


def test_modifying_protected_anchor_rejected(ta_harness):
    isr = ta_harness.isr_with_protected_anchor("anchor1")
    with pytest.raises(ConstitutionalViolation):
        ta_harness.operator.respecify_anchor(
            isr, anchor_id="anchor1",
            evidence_requirements=("tampered",),
        )


def test_downgrading_protected_anchor_rejected(ta_harness):
    isr = ta_harness.isr_with_protected_anchor("anchor1")
    with pytest.raises(ConstitutionalViolation):
        ta_harness.operator.regrade_anchor(
            isr, anchor_id="anchor1", policy=ProtectionPolicy.EVOLVABLE
        )


def test_removing_evolvable_anchor_restores_identity(ta_harness):
    isr = ta_harness.isr_with()
    with_anchor = ta_harness.operator.add_anchor(
        isr, ta_harness.valid_anchor()
    ).candidate_isr
    removed = ta_harness.operator.remove_anchor(
        with_anchor, anchor_id="anchor1"
    ).candidate_isr
    assert removed.content_hash == isr.content_hash


def test_elevating_anchor_is_authorized(ta_harness):
    isr = ta_harness.isr_with_anchor()
    elevated = ta_harness.operator.regrade_anchor(
        isr, anchor_id="anchor1", policy=ProtectionPolicy.PROTECTED
    ).candidate_isr
    anchor = elevated.system.testing_anchors[0]
    assert anchor.protection_policy is ProtectionPolicy.PROTECTED


# -- declared, never inferred ---------------------------------------------------------------

def test_anchor_is_declared_not_inferred(ta_harness):
    a = ta_harness.isr_with_anchor_on_subject("w1")
    b = ta_harness.isr_with_anchor_on_subject("pay")
    assert ta_harness.gene_hashes(a, domain="workflows") == \
        ta_harness.gene_hashes(b, domain="workflows")  # same subjects
    assert ta_harness.gene_hash(a, ("anchor", "anchor1")) != \
        ta_harness.gene_hash(b, ("anchor", "anchor1"))


def test_anchor_identity_is_semantic_not_structural(ta_harness):
    a = ta_harness.isr_with_anchor_on_subject("w1")
    b = ta_harness.isr_with_anchor_on_subject("w1")
    b = b.with_system(dataclasses.replace(b.system, id="other-sys-id"))
    assert ta_harness.gene_hash(a, ("anchor", "anchor1")) == \
        ta_harness.gene_hash(b, ("anchor", "anchor1"))  # same declaration
    assert a.content_hash != b.content_hash  # system identity differs


# -- the F->H edge: obligation_refs resolve against F's AcceptanceCriterion ------------------

def test_obligation_refs_resolve_against_acceptance_criteria(ta_harness):
    assert ta_harness.isr_with_anchor().validate_structure() is True
    dangling = ta_harness.isr_with(
        anchors=(
            dataclasses.replace(
                ta_harness.valid_anchor(),
                obligation_refs=("no-such-criterion",),
            ),
        ),
    )
    assert dangling.validate_structure() is False


def test_anchor_carrier_added_without_editing_f(ta_harness):
    """The F->H edge activates by resolution only: F's AcceptanceCriterion
    construct and validator are untouched by H (asserted by the fact that
    the existing F suites still pass unchanged with the F-era assertions)."""
    isr = ta_harness.isr_with_anchor()
    criterion = isr.system.acceptance_criteria[0]
    assert criterion.criterion_id == "crit.cancel"
    assert not hasattr(criterion, "anchor_refs")  # F's construct carries no H edge
    assert not hasattr(criterion, "testing_refs")


# -- the dangerous boundary: no test implementation leaks into the anchor --------------------

def test_anchor_has_no_test_implementation_fields():
    fields = {f.name for f in dataclasses.fields(TestingAnchor)}
    impl = {
        f for f in fields
        if any(bad in f.lower() for bad in (
            "test_file", "function", "marker", "fixture", "command",
            "runner", "script", "execution", "framework",
        ))
    }
    assert not impl, f"anchor carries a test-implementation field: {impl}"


def test_anchor_has_no_evaluation_methods():
    anchor = TestingAnchor(anchor_id="a", subject_refs=("w1",))
    assert not hasattr(anchor, "is_satisfied")
    assert not hasattr(anchor, "verdict")
    assert not hasattr(anchor, "score")
    assert not hasattr(anchor, "execute")
    assert not hasattr(anchor, "evidence_refs")  # evidence binding is the evaluator's follow-up


def test_testing_lint_rejects_leaked_test_mechanism(ta_harness):
    leak = dataclasses.replace(
        ta_harness.valid_anchor(),
        evidence_requirements=("test_file test_cancel_order.py via pytest",),
    )
    hits = mechanism_hits(leak)
    assert "pytest" in hits
    assert "test_file" in hits
    with pytest.raises(TestingAnchorValidationError):
        assert_testing_technology_agnostic(leak)


def test_testing_lint_allows_semantic_evidence_obligations(ta_harness):
    assert_testing_technology_agnostic(ta_harness.valid_anchor())
    assert_testing_technology_agnostic(
        TestingAnchor(
            anchor_id="a2",
            subject_refs=("w1",),
            obligation_refs=("crit.cancel",),
            evidence_requirements=(
                "ORDERING must be demonstrated before authorization",),
        )
    )
    assert not mechanism_hits(
        TestingAnchor(
            anchor_id="a3",
            subject_refs=("w1",),
            evidence_requirements=("the declared behavior must be demonstrated",),
        )
    )


# -- structural validation -----------------------------------------------------------------

def test_dangling_subject_ref_rejected(ta_harness):
    dangling = ta_harness.isr_with(
        anchors=(
            dataclasses.replace(
                ta_harness.valid_anchor(), subject_refs=("no-such-gene",)
            ),
        ),
    )
    assert dangling.validate_structure() is False


def test_dangling_obligation_ref_rejected(ta_harness):
    dangling = ta_harness.isr_with(
        anchors=(
            dataclasses.replace(
                ta_harness.valid_anchor(), obligation_refs=("no-such-criterion",)
            ),
        ),
    )
    assert dangling.validate_structure() is False


def test_duplicate_anchor_id_rejected(ta_harness):
    duplicate = ta_harness.isr_with(
        anchors=(ta_harness.valid_anchor(), ta_harness.valid_anchor()),
    )
    assert duplicate.validate_structure() is False


# -- construction validity ----------------------------------------------------------------

def test_anchor_construction_validation():
    with pytest.raises(TestingAnchorValidationError):
        TestingAnchor(anchor_id="", subject_refs=("w1",))
    with pytest.raises(TestingAnchorValidationError):
        TestingAnchor(anchor_id="a", subject_refs=())


# -- canonicalization ----------------------------------------------------------------------

def test_empty_anchor_carrier_identity_neutral(ta_harness):
    isr = ta_harness.isr_without_anchors()
    assert ta_harness.with_empty_anchors(isr).content_hash == isr.content_hash


# -- the eleven gates, parameterized --------------------------------------------------------

@pytest.mark.parametrize("gate", PRIMITIVE_GATE)
def test_primitive_gate(gate, ta_harness):
    result = ta_harness.run_gate(gate)
    assert result.passed, f"{gate}: {result.evidence}"


def test_all_gates_pass_together(ta_harness):
    results = assert_all_gates(ta_harness)
    assert len(results) == len(PRIMITIVE_GATE)


# -- lineage is chain-anchored -------------------------------------------------------------

def test_anchor_mutation_is_chain_anchored(tmp_path):
    ledger = EvolutionLedger(root=str(tmp_path))
    operator = TestingAnchorOperator(ledger=ledger)
    harness = TestingAnchorPrimitiveHarness()
    isr = harness.isr_with()
    candidate = operator.add_anchor(isr, harness.valid_anchor())
    assert ledger.verify_event_chain() is True
    event = ledger.events()[0]
    assert event.event_type is EventType.MEASUREMENT
    assert event.payload["operator_id"] == "testing_anchor"
    assert event.payload["subject_id"] == "anchor1"
    assert event.payload["isr_hash_before"] == isr.content_hash
    assert event.payload["isr_hash_after"] == candidate.candidate_isr.content_hash


def test_anchor_remove_add_round_trip(ta_harness):
    isr = ta_harness.isr_with()
    added = ta_harness.operator.add_anchor(
        isr, ta_harness.valid_anchor()
    ).candidate_isr
    removed = ta_harness.operator.remove_anchor(
        added, anchor_id="anchor1"
    ).candidate_isr
    assert removed.content_hash == isr.content_hash


# -- the audit, mechanically one row ---------------------------------------------------------

def test_audit_moves_exactly_one_row(ta_harness):
    result = ta_harness.audit.run(ta_harness.isr_with())
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