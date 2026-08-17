"""R2.10.3-F — requirements_acceptance_traceability: obligations, not tasks.

The ISR declares what the system must accomplish (Requirement) and what must
be demonstrably true for acceptance (AcceptanceCriterion). The acceptance
criterion is the deliberately calibrated middle layer between "too weak to
evaluate" (statement = "system is reliable" — nothing mechanically
determinable) and "too coupled to a testing technology" (pytest_test =
"test_reliability.py" — the ISR becomes a test manifest). It carries an
obligation + a semantic KIND + subjects: enough for an evaluation substrate
to dispatch on, no mechanism for how. No is_satisfied(), no verdict, no
test-reference field exists anywhere in this primitive (a structural test
pins that).

THIS LANDING ACTIVATES B's RESERVATION: ``BusinessCapability.requirement_refs``
was carried empty and unvalidated since R2.10.3-B. F introduces ``Requirement``
and makes those refs resolvable against ``System.requirements`` WITHOUT editing
the ``BusinessCapability`` construct — the first real test of whether the
R2.10.2 derived dependency graph was correct.

The substance of the slice is reference-by-identity asymmetry: changing a
requirement's statement/criteria moves the REQUIREMENT gene but not the
capability that references it by id; adding a ``requirement_ref`` to a
capability is an EXPLICITLY DECLARED cross-reference and DOES move the
capability gene. Both directions are proven below. Requirements are declared,
never inferred from behavior or implementation structure.

The audit gate embeds the pre-landing matrix (7/18/0/5 — after R2.10.3-E)
and asserts the delta is exactly {requirements_acceptance_traceability:
MISSING -> EXPRESSED} -> 8/18/0/4.
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
    RequirementValidationError,
    StateType,
    System,
    TemporalConstraint,
    TemporalConstraintKind,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)
from constitutional_architecture.isr.semantics.requirement import (
    REQUIREMENT_MECHANISM_TERMS,
    assert_requirement_technology_agnostic,
    project_acceptance_criteria,
    project_requirements,
    requirement_mechanism_hits,
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
from tiannara.application.evolution.requirement_mutation import RequirementOperator


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


class RequirementPrimitiveHarness:
    """The eleven-gate harness for requirements_acceptance_traceability."""

    primitive_id = "requirements_acceptance_traceability"

    def __init__(self) -> None:
        self.audit = ISRCapabilityAudit()
        self.operator = RequirementOperator()
        self.locality_probe = MutationLocalityProbe()
        self.backend = FastAPIHexagonalBackend()

    # -- recipes ------------------------------------------------------------

    def valid_criterion(self) -> AcceptanceCriterion:
        return AcceptanceCriterion(
            criterion_id="crit.cancel",
            obligation="Order cancellation must become effective before settlement",
            kind=ObligationKind.ORDERING,
            subject_refs=("w1",),
        )

    def valid_requirement(self) -> Requirement:
        return Requirement(
            requirement_id="req.cancel",
            statement="Cancellation must become effective before settlement",
            target_refs=("pay",),
            acceptance_refs=("crit.cancel",),
            constraint_refs=("w1",),
        )

    def isr_with(
        self,
        requirements: tuple[Requirement, ...] = (),
        criteria: tuple[AcceptanceCriterion, ...] = (),
        capabilities: tuple[BusinessCapability, ...] | None = None,
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
        if capabilities is not None:
            capabilities = tuple(capabilities)
        else:
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
        return ISR(
            system=System(
                id="req-sys",
                name="RequirementSystem",
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
            )
        )

    def isr_without_requirements(self) -> ISR:
        return self.isr_with()

    def isr_with_declared_requirement(self) -> ISR:
        return self.isr_with(
            requirements=(self.valid_requirement(),),
            criteria=(self.valid_criterion(),),
        )

    def isr_with_capability_linked(self) -> ISR:
        isr = self.isr_with_declared_requirement()
        return self.operator.link_capability(
            isr, requirement_id="req.cancel", capability_id="pay"
        ).candidate_isr

    def with_empty_requirements(self, isr: ISR) -> ISR:
        return isr.with_system(
            dataclasses.replace(isr.system, requirements=(), acceptance_criteria=())
        )

    def evolve_requirement_statement(self, isr: ISR, requirement_id: str) -> ISR:
        """Respecify one obligation; nothing else changes."""
        return self.operator.set_statement(
            isr,
            requirement_id=requirement_id,
            statement="Cancellation must become effective before settlement OR authorization",
        ).candidate_isr

    def evolve_capability_implementation(self, isr: ISR, capability_id: str) -> ISR:
        """Mutate the implementation behind a capability; identity stable."""
        modules = []
        for module in isr.system.modules:
            if any(w.id == "w1" for w in module.workflows):
                module = dataclasses.replace(
                    module,
                    description="implementation evolved under capability",
                )
            modules.append(module)
        return isr.with_system(
            dataclasses.replace(isr.system, modules=tuple(modules))
        )

    # -- gene addressing ------------------------------------------------------

    def all_gene_hashes(self, isr: ISR) -> dict[str, str]:
        """Every gene except the requirement + criterion gene classes."""
        return {
            path: h
            for path, h in gene_index(isr).items()
            if "system.requirements" not in path
            and "system.acceptance_criteria" not in path
        }

    def gene_hash(self, isr: ISR, gene: tuple) -> str:
        """("requirement", rid) / ("criterion", cid) / ("capability", cid) /
        ("module", mid) / ("behavior", wf_id) / ("boundary", bid) /
        ("reliability", rid) / ("migration", mid) / ("temporal", cid)."""
        idx = gene_index(isr)
        kind, name = gene
        if kind == "requirement":
            for ri, requirement in enumerate(isr.system.requirements):
                if requirement.requirement_id == name:
                    return idx[f"system.requirements[{ri}]"]
        if kind == "criterion":
            for ci, criterion in enumerate(isr.system.acceptance_criteria):
                if criterion.criterion_id == name:
                    return idx[f"system.acceptance_criteria[{ci}]"]
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
        ok = {"requirements", "acceptance_criteria"} <= system_fields
        try:
            self.valid_requirement()
            self.valid_criterion()
        except RequirementValidationError:
            ok = False
        mechanism_fields = {
            f.name
            for f in dataclasses.fields(Requirement) + dataclasses.fields(AcceptanceCriterion)
            if any(bad in f.name.lower() for bad in (
                "test", "assert", "runner", "file", "suite", "verdict",
                "satisfied", "score", "status", "result",
            ))
        }
        ok = ok and not mechanism_fields
        kinds = {k.value for k in ObligationKind}
        ok = ok and kinds == {"ORDERING", "PRESENCE", "ABSENCE", "INVARIANT", "THRESHOLD"}
        return _result(
            "representation",
            ok,
            f"System.requirements + System.acceptance_criteria carriers; "
            f"Requirement/AcceptanceCriterion constructs; ObligationKind x5; "
            f"no test/verdict fields: {mechanism_fields or 'none'}",
        )

    def _gate_canonicalization(self):
        isr = self.isr_without_requirements()
        same = self.with_empty_requirements(isr).content_hash == isr.content_hash
        return _result(
            "canonicalization",
            same,
            f"empty requirement + criterion carriers identity-neutral: {same}",
        )

    def _gate_semantic_identity(self):
        isr = self.isr_with()
        declared = self.operator.add_requirement(
            isr, self.valid_requirement()
        ).candidate_isr
        step1 = declared.content_hash != isr.content_hash
        respecified = self.evolve_requirement_statement(declared, "req.cancel")
        step2 = respecified.content_hash != declared.content_hash
        removed = self.operator.remove_requirement(
            respecified, requirement_id="req.cancel"
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
            dict(requirement_id="", statement="s", target_refs=("pay",)),
            dict(requirement_id="r", statement="", target_refs=("pay",)),
            dict(requirement_id="r", statement="s", target_refs=()),
            dict(criterion_id="", obligation="o", kind=ObligationKind.PRESENCE),
            dict(criterion_id="c", obligation="", kind=ObligationKind.PRESENCE),
        ):
            try:
                if "kind" in bad:
                    AcceptanceCriterion(**bad)
                else:
                    Requirement(**bad)
                ok = False
            except RequirementValidationError:
                pass
        dangling_target = self.isr_with(
            requirements=(
                dataclasses.replace(
                    self.valid_requirement(), target_refs=("no-such-capability",)
                ),
            ),
        )
        ok = ok and dangling_target.validate_structure() is False
        dangling_acceptance = self.isr_with(
            requirements=(
                dataclasses.replace(
                    self.valid_requirement(),
                    acceptance_refs=("no-such-criterion",),
                ),
            ),
        )
        ok = ok and dangling_acceptance.validate_structure() is False
        dangling_constraint = self.isr_with(
            requirements=(
                dataclasses.replace(
                    self.valid_requirement(),
                    constraint_refs=("no-such-gene",),
                ),
            ),
        )
        ok = ok and dangling_constraint.validate_structure() is False
        dangling_subject = self.isr_with(
            criteria=(
                dataclasses.replace(
                    self.valid_criterion(), subject_refs=("no-such-gene",)
                ),
            ),
        )
        ok = ok and dangling_subject.validate_structure() is False
        dup_requirement = self.isr_with(
            requirements=(self.valid_requirement(), self.valid_requirement()),
        )
        ok = ok and dup_requirement.validate_structure() is False
        dup_criterion = self.isr_with(
            criteria=(self.valid_criterion(), self.valid_criterion()),
        )
        ok = ok and dup_criterion.validate_structure() is False
        dangling_link = self.isr_with(
            capabilities=(
                BusinessCapability(
                    capability_id="pay",
                    intent="process a payment",
                    behavior_refs=("w1",),
                    interface_refs=("i1",),
                    requirement_refs=("no-such-requirement",),
                ),
            ),
        )
        ok = ok and dangling_link.validate_structure() is False
        ok = ok and self.isr_with_declared_requirement().validate_structure() is True
        ok = ok and self.isr_with_capability_linked().validate_structure() is True
        return _result(
            "validation",
            ok,
            "construction contracts enforced; dangling target/acceptance/"
            "constraint/subject refs + duplicates rejected pre-execution; "
            "capability requirement_refs now RESOLVE (B's reservation activated)",
        )

    def _gate_locality(self):
        isr = self.isr_with()
        mutated = self.operator.add_requirement(
            isr, self.valid_requirement()
        ).candidate_isr
        result = self.locality_probe.probe(
            isr, mutated, "system.requirements[0]"
        )
        return _result(
            "locality",
            result.locality_holds,
            f"target gene changed: {result.target_gene_changed}; "
            f"unintended changes: {result.unintended_changes}",
        )

    def _gate_projection(self):
        isr = self.isr_with_declared_requirement()
        requirements = project_requirements(isr)
        criteria = project_acceptance_criteria(isr)
        deterministic = (
            requirements == project_requirements(isr)
            and criteria == project_acceptance_criteria(isr)
        )
        reflects = any(
            r.get("requirement_id") == "req.cancel"
            and "pay" in r.get("target_refs", [])
            and "crit.cancel" in r.get("acceptance_refs", [])
            for r in requirements
        ) and any(
            c.get("criterion_id") == "crit.cancel"
            and c.get("kind") == "ORDERING"
            and "w1" in c.get("subject_refs", [])
            for c in criteria
        )
        text = str(requirements) + str(criteria)
        coupled = [term for term in TECHNOLOGY_COUPLING_TERMS if term in text]
        mechanism = [
            term for term in REQUIREMENT_MECHANISM_TERMS if term in text
        ]
        return _result(
            "projection",
            deterministic and reflects and not coupled and not mechanism,
            f"deterministic: {deterministic}; reflects obligation+kind: {reflects}; "
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
            f"existing backend byte-identical with requirements declared: "
            f"{compatible}; deterministic: {deterministic}",
        )

    def _gate_evidence(self):
        isr = self.isr_with_declared_requirement()
        observable = any(
            r.get("requirement_id") == "req.cancel"
            for r in project_requirements(isr)
        ) and any(
            c.get("criterion_id") == "crit.cancel"
            for c in project_acceptance_criteria(isr)
        )
        empty = (
            project_requirements(self.isr_without_requirements()) == ()
            and project_acceptance_criteria(self.isr_without_requirements()) == ()
        )
        return _result(
            "evidence",
            observable and empty,
            f"obligation observable in semantic projection: {observable}; "
            f"no requirements -> empty projections: {empty}",
        )

    def _gate_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = EvolutionLedger(root=str(tmp))
            operator = RequirementOperator(ledger=ledger)
            isr = self.isr_with()
            candidate = operator.add_requirement(isr, self.valid_requirement())
            chain_ok = ledger.verify_event_chain() is True
            events = ledger.events()
            event = events[0] if events else None
            attributed = (
                event is not None
                and event.event_type is EventType.MEASUREMENT
                and event.payload["operator_id"] == "requirement"
                and event.payload["subject_id"] == "req.cancel"
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
        same = len(c1) == len(c2) == 2 and all(
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
            "deployment_rollout_rollback",
            "documentation", "testing_anchoring",
            "evolution_objectives_protected_regions",
        }
        matrix_ok = (
            expressed == post_expressed
            and partial == post_partial
            and missing == post_missing
            and CapabilityStatus.PROJECTED not in by_id.values()
        )
        # Exactly one row moved vs the pre-landing (R2.10.3-E) matrix 7/18/0/5.
        pre_expressed = post_expressed - {"requirements_acceptance_traceability"}
        pre_missing = post_missing | {"requirements_acceptance_traceability"}
        one_row_only = (
            expressed - pre_expressed == {"requirements_acceptance_traceability"}
            and missing == pre_missing - {"requirements_acceptance_traceability"}
            and partial == post_partial
        )
        return _result(
            "audit",
            matrix_ok and one_row_only,
            f"summary: {result.summary()}; expected 8/18/0/4 with exactly "
            f"requirements_acceptance_traceability: MISSING -> EXPRESSED and "
            f"the other 29 rows untouched",
        )


def _result(gate: str, passed: bool, evidence: str) -> GateResult:
    return GateResult(gate=gate, passed=passed, evidence=evidence)


@pytest.fixture
def req_harness() -> RequirementPrimitiveHarness:
    return RequirementPrimitiveHarness()


# -- reference-by-identity asymmetry: the substance of the slice ---------------------------

def test_changing_requirement_does_not_change_capability_gene(req_harness):
    """Respecifying an obligation moves the REQUIREMENT gene; the capability
    that references it by id does NOT move."""
    isr = req_harness.isr_with_capability_linked()
    cap_before = req_harness.gene_hash(isr, ("capability", "pay"))
    req_before = req_harness.gene_hash(isr, ("requirement", "req.cancel"))
    mutated = req_harness.evolve_requirement_statement(isr, "req.cancel")
    assert req_harness.gene_hash(mutated, ("requirement", "req.cancel")) != req_before
    assert req_harness.gene_hash(mutated, ("capability", "pay")) == cap_before


def test_adding_requirement_ref_to_capability_changes_capability_gene(req_harness):
    """The reverse direction: an EXPLICITLY DECLARED cross-reference moves the
    capability gene — the declared link is real traceability, not noise."""
    isr = req_harness.isr_with_declared_requirement()
    cap_before = req_harness.gene_hash(isr, ("capability", "pay"))
    linked = req_harness.operator.link_capability(
        isr, requirement_id="req.cancel", capability_id="pay"
    ).candidate_isr
    assert req_harness.gene_hash(linked, ("capability", "pay")) != cap_before
    assert req_harness.gene_hash(linked, ("requirement", "req.cancel")) == \
        req_harness.gene_hash(isr, ("requirement", "req.cancel"))


def test_capability_requirement_refs_now_resolve(req_harness):
    """B's reservation is ACTIVATED: requirement_refs resolve against
    System.requirements; a dangling ref is rejected pre-execution."""
    assert req_harness.isr_with_capability_linked().validate_structure() is True
    dangling = req_harness.isr_with(
        capabilities=(
            BusinessCapability(
                capability_id="pay",
                intent="process a payment",
                behavior_refs=("w1",),
                interface_refs=("i1",),
                requirement_refs=("no-such-requirement",),
            ),
        ),
    )
    assert dangling.validate_structure() is False


def test_capability_with_empty_requirement_refs_unchanged_by_activation(req_harness):
    """The graph-check: a capability with empty requirement_refs is
    byte-identical after the reservation became active."""
    plain = req_harness.isr_with()
    assert all(c.requirement_refs == () for c in plain.system.business_capabilities)
    assert plain.validate_structure() is True


# -- declared, never inferred ---------------------------------------------------------------

def test_requirement_is_declared_not_inferred(req_harness):
    a = req_harness.isr_with(
        requirements=(req_harness.valid_requirement(),),
    )
    b = req_harness.isr_with(
        requirements=(
            dataclasses.replace(
                req_harness.valid_requirement(),
                statement="Nothing whatsoever is required of this system",
            ),
        ),
    )
    assert req_harness.gene_hash(a, ("capability", "pay")) == \
        req_harness.gene_hash(b, ("capability", "pay"))  # same structure
    assert req_harness.gene_hash(a, ("requirement", "req.cancel")) != \
        req_harness.gene_hash(b, ("requirement", "req.cancel"))


def test_requirement_identity_is_semantic_not_structural(req_harness):
    a = req_harness.isr_with_declared_requirement()
    b = req_harness.isr_with_declared_requirement()  # identical declarations
    b = b.with_system(dataclasses.replace(b.system, id="other-sys-id"))
    assert req_harness.gene_hash(a, ("requirement", "req.cancel")) == \
        req_harness.gene_hash(b, ("requirement", "req.cancel"))
    assert a.content_hash != b.content_hash


# -- locality -------------------------------------------------------------------------------

def test_add_requirement_does_not_touch_other_genes(req_harness):
    isr = req_harness.isr_with()
    before = req_harness.all_gene_hashes(isr)
    mutated = req_harness.operator.add_requirement(
        isr, req_harness.valid_requirement()
    ).candidate_isr
    assert req_harness.all_gene_hashes(mutated) == before
    assert req_harness.has_gene(mutated, ("requirement", "req.cancel"))


def test_changing_requirement_only_moves_requirement_gene(req_harness):
    isr = req_harness.isr_with_declared_requirement()
    before = req_harness.all_gene_hashes(isr)
    mutated = req_harness.evolve_requirement_statement(isr, "req.cancel")
    assert req_harness.all_gene_hashes(mutated) == before
    assert req_harness.gene_hash(mutated, ("requirement", "req.cancel")) != \
        req_harness.gene_hash(isr, ("requirement", "req.cancel"))


def test_assigning_criterion_only_moves_requirement_gene(req_harness):
    isr = req_harness.isr_with_declared_requirement()
    unassigned = req_harness.operator.remove_requirement(
        isr, requirement_id="req.cancel"
    ).candidate_isr
    declared = req_harness.operator.add_requirement(
        unassigned,
        dataclasses.replace(
            req_harness.valid_requirement(), acceptance_refs=()
        ),
    ).candidate_isr
    before = req_harness.all_gene_hashes(declared)
    assigned = req_harness.operator.assign_criterion(
        declared, requirement_id="req.cancel", criterion_id="crit.cancel"
    ).candidate_isr
    assert req_harness.all_gene_hashes(assigned) == before
    assert req_harness.gene_hash(assigned, ("requirement", "req.cancel")) != \
        req_harness.gene_hash(declared, ("requirement", "req.cancel"))


# -- the dangerous boundary: no test mechanism leaks into the obligation -------------------

def test_acceptance_criterion_has_no_test_fields():
    fields = {f.name for f in dataclasses.fields(AcceptanceCriterion)}
    leak = {
        f for f in fields
        if any(bad in f.lower() for bad in (
            "test", "assert", "runner", "file", "suite", "verdict",
            "satisfied", "score", "status", "result",
        ))
    }
    assert not leak, f"acceptance criterion carries an evaluation field: {leak}"


def test_requirement_has_no_test_reference_field():
    fields = {f.name for f in dataclasses.fields(Requirement)}
    leak = {
        f for f in fields
        if any(bad in f.lower() for bad in (
            "test", "assert", "runner", "file", "suite",
        ))
    }
    assert not leak, f"requirement carries a test-reference field: {leak}"


def test_acceptance_criterion_is_obligation_not_verdict(req_harness):
    criterion = req_harness.valid_criterion()
    assert criterion.kind is ObligationKind.ORDERING
    assert not hasattr(criterion, "is_satisfied")
    assert not hasattr(criterion, "verdict")
    assert not hasattr(criterion, "score")
    assert not hasattr(criterion, "passed")
    assert not hasattr(criterion, "evidence_refs")  # evidence binding is H's job


def test_requirement_mechanism_lint_rejects_leaked_test_mechanism(req_harness):
    leak = dataclasses.replace(
        req_harness.valid_requirement(),
        statement="run test_cancel_order.py via pytest",
    )
    hits = requirement_mechanism_hits(leak)
    assert "pytest" in hits
    with pytest.raises(RequirementValidationError):
        assert_requirement_technology_agnostic(leak)
    assert_requirement_technology_agnostic(req_harness.valid_requirement())
    assert_requirement_technology_agnostic(req_harness.valid_criterion())


def test_requirement_lint_allows_semantic_obligations(req_harness):
    assert_requirement_technology_agnostic(
        "Order cancellation must become effective before settlement"
    )
    assert_requirement_technology_agnostic(
        "Settlement must not be initiated for a cancelled order"
    )
    assert_requirement_technology_agnostic(
        "Authorized volume must remain below the declared limit"
    )


# -- structural validation -----------------------------------------------------------------

def test_dangling_target_ref_rejected(req_harness):
    dangling = req_harness.isr_with(
        requirements=(
            dataclasses.replace(
                req_harness.valid_requirement(), target_refs=("no-such-capability",)
            ),
        ),
    )
    assert dangling.validate_structure() is False


def test_dangling_acceptance_ref_rejected(req_harness):
    dangling = req_harness.isr_with(
        requirements=(
            dataclasses.replace(
                req_harness.valid_requirement(),
                acceptance_refs=("no-such-criterion",),
            ),
        ),
    )
    assert dangling.validate_structure() is False


def test_dangling_constraint_ref_rejected(req_harness):
    dangling = req_harness.isr_with(
        requirements=(
            dataclasses.replace(
                req_harness.valid_requirement(),
                constraint_refs=("no-such-gene",),
            ),
        ),
    )
    assert dangling.validate_structure() is False


def test_dangling_subject_ref_rejected(req_harness):
    dangling = req_harness.isr_with(
        criteria=(
            dataclasses.replace(
                req_harness.valid_criterion(), subject_refs=("no-such-gene",)
            ),
        ),
    )
    assert dangling.validate_structure() is False


def test_duplicate_requirement_id_rejected(req_harness):
    duplicate = req_harness.isr_with(
        requirements=(req_harness.valid_requirement(), req_harness.valid_requirement()),
    )
    assert duplicate.validate_structure() is False


def test_duplicate_criterion_id_rejected(req_harness):
    duplicate = req_harness.isr_with(
        criteria=(req_harness.valid_criterion(), req_harness.valid_criterion()),
    )
    assert duplicate.validate_structure() is False


# -- construction validity ----------------------------------------------------------------

def test_requirement_construction_validation():
    with pytest.raises(RequirementValidationError):
        Requirement(requirement_id="", statement="s", target_refs=("pay",))
    with pytest.raises(RequirementValidationError):
        Requirement(requirement_id="r", statement="", target_refs=("pay",))
    with pytest.raises(RequirementValidationError):
        Requirement(requirement_id="r", statement="s", target_refs=())
    with pytest.raises(RequirementValidationError):
        AcceptanceCriterion(criterion_id="", obligation="o", kind=ObligationKind.PRESENCE)
    with pytest.raises(RequirementValidationError):
        AcceptanceCriterion(criterion_id="c", obligation="", kind=ObligationKind.PRESENCE)


# -- canonicalization ---------------------------------------------------------------------

def test_empty_requirement_carriers_identity_neutral(req_harness):
    isr = req_harness.isr_without_requirements()
    assert req_harness.with_empty_requirements(isr).content_hash == isr.content_hash


# -- the eleven gates, parameterized --------------------------------------------------------

@pytest.mark.parametrize("gate", PRIMITIVE_GATE)
def test_primitive_gate(gate, req_harness):
    result = req_harness.run_gate(gate)
    assert result.passed, f"{gate}: {result.evidence}"


def test_all_gates_pass_together(req_harness):
    results = assert_all_gates(req_harness)
    assert len(results) == len(PRIMITIVE_GATE)


# -- lineage is chain-anchored -------------------------------------------------------------

def test_requirement_mutation_is_chain_anchored(tmp_path):
    ledger = EvolutionLedger(root=str(tmp_path))
    operator = RequirementOperator(ledger=ledger)
    harness = RequirementPrimitiveHarness()
    isr = harness.isr_with()
    candidate = operator.add_requirement(isr, harness.valid_requirement())
    assert ledger.verify_event_chain() is True
    event = ledger.events()[0]
    assert event.event_type is EventType.MEASUREMENT
    assert event.payload["operator_id"] == "requirement"
    assert event.payload["subject_id"] == "req.cancel"
    assert event.payload["isr_hash_before"] == isr.content_hash
    assert event.payload["isr_hash_after"] == candidate.candidate_isr.content_hash


def test_remove_requirement_restores_identity(req_harness):
    isr = req_harness.isr_with()
    declared = req_harness.operator.add_requirement(
        isr, req_harness.valid_requirement()
    ).candidate_isr
    removed = req_harness.operator.remove_requirement(
        declared, requirement_id="req.cancel"
    ).candidate_isr
    assert removed.content_hash == isr.content_hash


# -- the audit, mechanically one row ---------------------------------------------------------

def test_audit_moves_exactly_one_row(req_harness):
    result = req_harness.audit.run(req_harness.isr_with())
    by_id = {c.capability_id: c.status for c in result.capabilities}
    expressed = {cid for cid, s in by_id.items() if s is CapabilityStatus.EXPRESSED}
    missing = {cid for cid, s in by_id.items() if s is CapabilityStatus.MISSING}
    pre_expressed = {
        "behavior_transitions", "behavior_await_surface",
        "behavior_temporal_semantics", "business_capabilities",
        "data_migrations", "reliability_resilience",
        "architecture_boundaries",
    }
    pre_missing = {
        "requirements_acceptance_traceability",
        "deployment_rollout_rollback",
        "documentation", "testing_anchoring",
        "evolution_objectives_protected_regions",
    }
    moved_rows = {}
    for cid in pre_expressed | pre_missing:
        before = "EXPRESSED" if cid in pre_expressed else "MISSING"
        after = "EXPRESSED" if cid in expressed else "MISSING"
        if before != after:
            moved_rows[cid] = (before, after)
    assert moved_rows == {
        "requirements_acceptance_traceability": ("MISSING", "EXPRESSED")
    }
    assert (len(expressed), 18, 0, len(missing)) == (8, 18, 0, 4)  # NOT 7/18/0/5

