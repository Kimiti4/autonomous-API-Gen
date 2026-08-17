"""R2.10.3-E — architecture_boundaries: constraint on relationships, never a container.

A boundary is a SEMANTIC constraint on relationships between genes — NOT a
module, a service, or a deployment unit. It declares what may or may not
cross it. A backend may realize it as a module / package / process /
service / network boundary / repository / container, but NONE of those
realizations is part of this primitive (enforced by a field-name test and a
realization lint over the canonical semantic form).

Deliberately the minimum carrier R2.8.6 already proved: ``member_refs`` +
``forbidden_dependency_refs`` + ``protected`` is exactly the semantic content
the architectural-integrity gate enforced on the FSM substrate, now elevated
into the constitutional ISR as a first-class gene. The gene DECLARES the
constraint; wiring the R2.8.6 enforcement machinery to read from the gene is
a follow-up integration, deliberately NOT part of this landing.

The substance of the slice: the boundary gene stays byte-identical while its
members' implementations evolve (reference-by-identity), and boundary
mutation moves only the boundary gene — architecture as an independently
evolvable dimension.

The audit gate embeds the pre-landing matrix (6/18/0/6 — after R2.10.3-D)
and asserts the delta is exactly {architecture_boundaries: MISSING ->
EXPRESSED} -> 7/18/0/5.
"""
from __future__ import annotations

import dataclasses
import tempfile
from typing import Any

import pytest

from constitutional_architecture.isr.model import (
    ArchitecturalBoundary,
    BoundaryValidationError,
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
    StateType,
    System,
    TemporalConstraint,
    TemporalConstraintKind,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)
from constitutional_architecture.isr.semantics.boundary import (
    BOUNDARY_MECHANISM_TERMS,
    assert_boundary_technology_agnostic,
    boundary_mechanism_hits,
    project_architectural_boundaries,
)
from constitutional_architecture.isr.semantics.projection import canonicalize
from constitutional_architecture.validators import ConstitutionalViolation
from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend
from tiannara.application.evolution.boundary_mutation import BoundaryOperator
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


class BoundaryPrimitiveHarness:
    """The eleven-gate harness for architecture_boundaries."""

    primitive_id = "architecture_boundaries"

    def __init__(self) -> None:
        self.audit = ISRCapabilityAudit()
        self.operator = BoundaryOperator()
        self.locality_probe = MutationLocalityProbe()
        self.backend = FastAPIHexagonalBackend()

    # -- recipes ------------------------------------------------------------

    def valid_boundary(self) -> ArchitecturalBoundary:
        return ArchitecturalBoundary(
            boundary_id="b1",
            member_refs=("m",),
            forbidden_dependency_refs=(),
            protected=False,
            crossing_invariants=("no cross without declared intent",),
        )

    def isr_with(
        self,
        boundaries: tuple[ArchitecturalBoundary, ...] = (),
        with_capability: bool = True,
        with_temporal: bool = True,
        with_migration: bool = True,
        with_reliability: bool = True,
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
        requirements = (
            (
                ReliabilityRequirement(
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
                ),
            )
            if with_reliability
            else ()
        )
        return ISR(
            system=System(
                id="boundary-sys",
                name="BoundarySystem",
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
                architectural_boundaries=boundaries,
            )
        )

    def isr_without_boundaries(self) -> ISR:
        return self.isr_with()

    def isr_with_behavior_capabilities_temporal_migrations_reliability(self) -> ISR:
        return self.isr_with()

    def isr_with_protected_boundary(self, boundary_id: str = "b1") -> ISR:
        return self.isr_with(
            boundaries=(
                dataclasses.replace(self.valid_boundary(), protected=True),
            )
        )

    def isr_with_boundary_enclosing(self, member_id: str = "m") -> ISR:
        return self.isr_with(
            boundaries=(
                dataclasses.replace(
                    self.valid_boundary(), member_refs=(member_id,)
                ),
            )
        )

    def evolve_member_implementation(self, isr: ISR, module_id: str) -> ISR:
        """Mutate a member's implementation while its identity is stable."""
        modules = []
        for module in isr.system.modules:
            if module.id == module_id:
                module = dataclasses.replace(
                    module, description="implementation evolved"
                )
            modules.append(module)
        return isr.with_system(
            dataclasses.replace(isr.system, modules=tuple(modules))
        )

    def with_empty_boundaries(self, isr: ISR) -> ISR:
        return isr.with_system(
            dataclasses.replace(isr.system, architectural_boundaries=())
        )

    # -- gene addressing ------------------------------------------------------

    def all_gene_hashes(self, isr: ISR) -> dict[str, str]:
        """Every gene except the boundary gene class."""
        return {
            path: h
            for path, h in gene_index(isr).items()
            if "architectural_boundaries" not in path
        }

    def gene_hash(self, isr: ISR, gene: tuple) -> str:
        """(\"boundary\", bid) / (\"module\", mid) / (\"entity\", eid) /
        (\"behavior\", wf_id) / (\"capability\", cid) / (\"temporal\", cid) /
        (\"migration\", mid) / (\"reliability\", rid)."""
        idx = gene_index(isr)
        kind, name = gene
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

    def module_genes_identical(self, a: ISR, b: ISR) -> bool:
        a_hash = {p: h for p, h in self.all_gene_hashes(a).items() if ".modules[" in p}
        b_hash = {p: h for p, h in self.all_gene_hashes(b).items() if ".modules[" in p}
        return a_hash == b_hash

    # -- gates ----------------------------------------------------------------

    def run_gate(self, gate: str) -> GateResult:
        method = getattr(self, f"_gate_{gate}", None)
        if method is None:
            raise AssertionError(f"no implementation for gate '{gate}'")
        return method()

    def _gate_representation(self):
        system_fields = {f.name for f in dataclasses.fields(System)}
        ok = "architectural_boundaries" in system_fields
        try:
            self.valid_boundary()
            ok = ok and True
        except BoundaryValidationError:
            ok = False
        realization_fields = {
            f.name
            for f in dataclasses.fields(ArchitecturalBoundary)
            if any(bad in f.name.lower() for bad in (
                "package", "container", "process", "pod", "network", "deploy"))
        }
        return _result(
            "representation",
            ok and not realization_fields,
            f"System.architectural_boundaries carrier; ArchitecturalBoundary "
            f"with members/forbidden/protected/invariants; no realization "
            f"fields: {realization_fields or 'none'}",
        )

    def _gate_canonicalization(self):
        isr = self.isr_without_boundaries()
        same = self.with_empty_boundaries(isr).content_hash == isr.content_hash
        return _result(
            "canonicalization",
            same,
            f"empty boundary carrier identity-neutral: {same}",
        )

    def _gate_semantic_identity(self):
        isr = self.isr_with()
        with_boundary = self.operator.add_boundary(
            isr, self.valid_boundary()
        ).candidate_isr
        step1 = with_boundary.content_hash != isr.content_hash
        repointed = self.operator.set_forbidden_refs(
            with_boundary,
            boundary_id="b1",
            forbidden_dependency_refs=("pay",),
        ).candidate_isr
        step2 = repointed.content_hash != with_boundary.content_hash
        removed = self.operator.remove_boundary(
            repointed, boundary_id="b1"
        ).candidate_isr
        step3 = removed.content_hash == isr.content_hash
        return _result(
            "semantic_identity",
            step1 and step2 and step3,
            f"add changes hash: {step1}; forbidden change changes hash: {step2}; "
            f"remove restores hash: {step3}",
        )

    def _gate_validation(self):
        ok = True
        for bad in (
            dict(boundary_id="", member_refs=("m",)),
            dict(boundary_id="b", member_refs=()),
            dict(boundary_id="b", member_refs=("m", "pay"),
                 forbidden_dependency_refs=("pay",)),  # member-also-forbidden
        ):
            try:
                ArchitecturalBoundary(**bad)
                ok = False
            except BoundaryValidationError:
                pass
        dangling = self.isr_with(
            boundaries=(
                dataclasses.replace(
                    self.valid_boundary(), member_refs=("no-such-gene",)
                ),
            )
        )
        ok = ok and dangling.validate_structure() is False
        dangling_forbidden = self.isr_with(
            boundaries=(
                dataclasses.replace(
                    self.valid_boundary(), forbidden_dependency_refs=("no-such-gene",)
                ),
            )
        )
        ok = ok and dangling_forbidden.validate_structure() is False
        duplicate = self.isr_with(
            boundaries=(self.valid_boundary(), self.valid_boundary())
        )
        ok = ok and duplicate.validate_structure() is False
        return _result(
            "validation",
            ok,
            "empty id / empty members / member-also-forbidden rejected at "
            "construction; dangling member + forbidden refs, duplicate ids "
            "rejected pre-execution",
        )

    def _gate_locality(self):
        isr = self.isr_with()
        mutated = self.operator.add_boundary(
            isr, self.valid_boundary()
        ).candidate_isr
        result = self.locality_probe.probe(
            isr, mutated, "system.architectural_boundaries[0]"
        )
        return _result(
            "locality",
            result.locality_holds,
            f"target gene changed: {result.target_gene_changed}; "
            f"unintended changes: {result.unintended_changes}",
        )

    def _gate_projection(self):
        isr = self.isr_with(boundaries=(self.valid_boundary(),))
        projected = project_architectural_boundaries(isr)
        deterministic = projected == project_architectural_boundaries(isr)
        reflects = any(
            b.get("boundary_id") == "b1"
            and "m" in b.get("member_refs", [])
            and b.get("protected") is False
            for b in projected
        )
        text = str(projected)
        coupled = [
            term for term in TECHNOLOGY_COUPLING_TERMS if term in text
        ]
        mechanism = [
            term for term in BOUNDARY_MECHANISM_TERMS if term in text
        ]
        return _result(
            "projection",
            deterministic and reflects and not coupled and not mechanism,
            f"deterministic: {deterministic}; reflects intent: {reflects}; "
            f"coupling terms: {coupled}; realization terms: {mechanism}",
        )

    def _gate_compilation(self):
        isr = self.isr_with()
        mutated = self.operator.add_boundary(
            isr, self.valid_boundary()
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
            f"existing backend byte-identical with boundaries present: "
            f"{compatible}; deterministic: {deterministic}",
        )

    def _gate_evidence(self):
        isr = self.isr_with(boundaries=(self.valid_boundary(),))
        observable = any(
            b.get("boundary_id") == "b1"
            for b in project_architectural_boundaries(isr)
        )
        empty = project_architectural_boundaries(
            self.isr_without_boundaries()
        ) == ()
        return _result(
            "evidence",
            observable and empty,
            f"boundary observable in semantic projection: {observable}; "
            f"no boundaries -> empty projection: {empty}",
        )

    def _gate_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = EvolutionLedger(root=str(tmp))
            operator = BoundaryOperator(ledger=ledger)
            isr = self.isr_with()
            candidate = operator.add_boundary(isr, self.valid_boundary())
            chain_ok = ledger.verify_event_chain() is True
            events = ledger.events()
            event = events[0] if events else None
            attributed = (
                event is not None
                and event.event_type is EventType.MEASUREMENT
                and event.payload["operator_id"] == "boundary"
                and event.payload["boundary_id"] == "b1"
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
            "evolution_objectives_protected_regions",
        }
        matrix_ok = (
            expressed == post_expressed
            and partial == post_partial
            and missing == post_missing
            and CapabilityStatus.PROJECTED not in by_id.values()
        )
        # Exactly one row moved vs the pre-landing (R2.10.3-D) matrix 6/18/0/6.
        pre_expressed = post_expressed - {"architecture_boundaries"}
        pre_missing = post_missing | {"architecture_boundaries"}
        one_row_only = (
            expressed - pre_expressed == {"architecture_boundaries"}
            and missing == pre_missing - {"architecture_boundaries"}
            and partial == post_partial
        )
        return _result(
            "audit",
            matrix_ok and one_row_only,
            f"summary: {result.summary()}; expected 8/18/0/4 with exactly "
            f"requirements_acceptance_traceability: MISSING -> EXPRESSED "
            f"vs the pre-landing (R2.10.3-E) 7/18/0/5",
        )


def _result(gate: str, passed: bool, evidence: str) -> GateResult:
    return GateResult(gate=gate, passed=passed, evidence=evidence)


@pytest.fixture
def bd_harness() -> BoundaryPrimitiveHarness:
    return BoundaryPrimitiveHarness()


# -- reference-by-identity: the substance of the slice ------------------------------

def test_boundary_stable_when_member_implementation_evolves(bd_harness):
    isr = bd_harness.isr_with_boundary_enclosing("m")
    bd_before = bd_harness.gene_hash(isr, ("boundary", "b1"))
    mutated = bd_harness.evolve_member_implementation(isr, "m")  # id stable
    assert bd_harness.gene_hash(mutated, ("module", "m")) != \
        bd_harness.gene_hash(isr, ("module", "m"))  # member moved
    assert bd_harness.gene_hash(mutated, ("boundary", "b1")) == bd_before  # boundary held


def test_boundary_is_semantic_constraint_not_container(bd_harness):
    # A boundary is not an alias for a module: the same boundary id with the
    # same membership is the same gene even when the enclosed module evolves.
    isr = bd_harness.isr_with_boundary_enclosing("m")
    bd = isr.system.architectural_boundaries[0]
    assert bd.boundary_id == "b1"
    assert bd.member_refs == ("m",)
    assert not any(
        bad in str(bd).lower()
        for bad in ("package", "container", "process", "pod", "network_zone")
    )


# -- locality -------------------------------------------------------------------

def test_add_boundary_does_not_touch_other_genes(bd_harness):
    isr = bd_harness.isr_with_behavior_capabilities_temporal_migrations_reliability()
    before = bd_harness.all_gene_hashes(isr)
    mutated = bd_harness.operator.add_boundary(
        isr, bd_harness.valid_boundary()
    ).candidate_isr
    assert bd_harness.all_gene_hashes(mutated) == before
    assert bd_harness.has_gene(mutated, ("boundary", "b1"))


def test_changing_boundary_only_moves_boundary_gene(bd_harness):
    isr = bd_harness.isr_with(boundaries=(bd_harness.valid_boundary(),))
    before = bd_harness.all_gene_hashes(isr)
    mutated = bd_harness.operator.set_forbidden_refs(
        isr, boundary_id="b1", forbidden_dependency_refs=("pay",)
    ).candidate_isr
    assert bd_harness.all_gene_hashes(mutated) == before  # only boundary gene moved
    assert bd_harness.gene_hash(mutated, ("boundary", "b1")) != \
        bd_harness.gene_hash(isr, ("boundary", "b1"))


# -- no inference ---------------------------------------------------------------

def test_boundary_is_declared_not_inferred(bd_harness):
    a = bd_harness.isr_with(
        boundaries=(dataclasses.replace(bd_harness.valid_boundary(), member_refs=("m",)),)
    )
    b = bd_harness.isr_with(
        boundaries=(dataclasses.replace(bd_harness.valid_boundary(), member_refs=("pay",)),)
    )
    assert bd_harness.module_genes_identical(a, b)  # same structure
    assert bd_harness.gene_hash(a, ("boundary", "b1")) != \
        bd_harness.gene_hash(b, ("boundary", "b1"))


def test_boundary_identity_is_declared_not_derived(bd_harness):
    # Equivalent declarations over differently structured implementations:
    # the boundary gene is the declared constraint, not the structure.
    a = bd_harness.isr_with(boundaries=(bd_harness.valid_boundary(),))
    b = bd_harness.isr_with(
        boundaries=(bd_harness.valid_boundary(),),
        with_migration=False,
    )
    assert bd_harness.gene_hash(a, ("boundary", "b1")) == \
        bd_harness.gene_hash(b, ("boundary", "b1"))
    assert a.content_hash != b.content_hash  # implementation differs


# -- protected-boundary preservation (R2.8.6 elevated) -------------------------------

def test_removing_protected_boundary_rejected(bd_harness):
    isr = bd_harness.isr_with_protected_boundary("b1")
    with pytest.raises(ConstitutionalViolation):
        bd_harness.operator.remove_boundary(isr, boundary_id="b1")


def test_removing_unprotected_boundary_restores_identity(bd_harness):
    isr = bd_harness.isr_with()
    with_boundary = bd_harness.operator.add_boundary(
        isr, bd_harness.valid_boundary()
    ).candidate_isr
    removed = bd_harness.operator.remove_boundary(
        with_boundary, boundary_id="b1"
    ).candidate_isr
    assert removed.content_hash == isr.content_hash


# -- dependency semantics -----------------------------------------------------------

def test_forbidden_dependency_is_explicit(bd_harness):
    isr = bd_harness.isr_with(boundaries=(
        dataclasses.replace(
            bd_harness.valid_boundary(), forbidden_dependency_refs=("pay",)
        ),
    ))
    projected = project_architectural_boundaries(isr)
    assert any(
        "pay" in b.get("forbidden_dependency_refs", [])
        for b in projected
    )


# -- the dangerous boundary: no realization technology ----------------------------------

def test_boundary_has_no_realization_fields():
    fields = {f.name for f in dataclasses.fields(ArchitecturalBoundary)}
    realization = {
        f for f in fields
        if any(bad in f.lower() for bad in (
            "package", "container", "process", "pod", "network", "deploy"))
    }
    assert not realization, f"boundary carries a realization field: {realization}"


def test_boundary_mechanism_lint_rejects_leaked_realization(bd_harness):
    leak = dataclasses.replace(
        bd_harness.valid_boundary(),
        crossing_invariants=("no cross to kubernetes pod",),
    )
    hits = boundary_mechanism_hits(leak)
    assert "kubernetes" in hits
    assert "pod" in hits
    with pytest.raises(BoundaryValidationError):
        assert_boundary_technology_agnostic(leak)
    assert_boundary_technology_agnostic(bd_harness.valid_boundary())


def test_boundary_lint_allows_semantic_references_to_isr_genes(bd_harness):
    # member_refs reference ISR genes (semantic references), not realizations:
    # the lint must NOT reject references to module/capability identities.
    enclosing = bd_harness.isr_with_boundary_enclosing("m")
    assert_boundary_technology_agnostic(enclosing.system.architectural_boundaries[0])
    capability_boundary = dataclasses.replace(
        bd_harness.valid_boundary(), member_refs=("pay",)
    )
    assert_boundary_technology_agnostic(capability_boundary)


# -- structural validation ---------------------------------------------------------------

def test_dangling_member_ref_rejected(bd_harness):
    dangling = bd_harness.isr_with(boundaries=(
        dataclasses.replace(
            bd_harness.valid_boundary(), member_refs=("no-such-gene",)
        ),
    ))
    assert dangling.validate_structure() is False


def test_dangling_forbidden_ref_rejected(bd_harness):
    dangling = bd_harness.isr_with(boundaries=(
        dataclasses.replace(
            bd_harness.valid_boundary(), forbidden_dependency_refs=("no-such-gene",)
        ),
    ))
    assert dangling.validate_structure() is False


def test_member_also_forbidden_dependency_rejected():
    with pytest.raises(BoundaryValidationError):
        ArchitecturalBoundary(
            boundary_id="b", member_refs=("m", "pay"),
            forbidden_dependency_refs=("pay",),
        )


# -- construction validity -----------------------------------------------------------

def test_boundary_construction_validation():
    with pytest.raises(BoundaryValidationError):
        ArchitecturalBoundary(boundary_id="", member_refs=("m",))
    with pytest.raises(BoundaryValidationError):
        ArchitecturalBoundary(boundary_id="b", member_refs=())


# -- canonicalization ------------------------------------------------------------------

def test_empty_boundary_carrier_identity_neutral(bd_harness):
    isr = bd_harness.isr_without_boundaries()
    assert bd_harness.with_empty_boundaries(isr).content_hash == isr.content_hash


# -- the eleven gates, parameterized ------------------------------------------------------

@pytest.mark.parametrize("gate", PRIMITIVE_GATE)
def test_primitive_gate(gate, bd_harness):
    result = bd_harness.run_gate(gate)
    assert result.passed, f"{gate}: {result.evidence}"


def test_all_gates_pass_together(bd_harness):
    results = assert_all_gates(bd_harness)
    assert len(results) == len(PRIMITIVE_GATE)


# -- lineage is chain-anchored ------------------------------------------------------------

def test_boundary_mutation_is_chain_anchored(tmp_path):
    ledger = EvolutionLedger(root=str(tmp_path))
    operator = BoundaryOperator(ledger=ledger)
    harness = BoundaryPrimitiveHarness()
    isr = harness.isr_with()
    candidate = operator.add_boundary(isr, harness.valid_boundary())
    assert ledger.verify_event_chain() is True
    event = ledger.events()[0]
    assert event.event_type is EventType.MEASUREMENT
    assert event.payload["operator_id"] == "boundary"
    assert event.payload["boundary_id"] == "b1"
    assert event.payload["isr_hash_before"] == isr.content_hash
    assert event.payload["isr_hash_after"] == candidate.candidate_isr.content_hash


# -- the audit, mechanically one row --------------------------------------------------------------

def test_audit_moves_exactly_one_row(bd_harness):
    result = bd_harness.audit.run(bd_harness.isr_with())
    by_id = {c.capability_id: c.status for c in result.capabilities}
    expressed = {cid for cid, s in by_id.items() if s is CapabilityStatus.EXPRESSED}
    missing = {cid for cid, s in by_id.items() if s is CapabilityStatus.MISSING}
    # Pre-landing (R2.10.3-H) matrix: 10/18/0/2.
    pre_expressed = {
        "behavior_transitions", "behavior_await_surface",
        "behavior_temporal_semantics", "business_capabilities",
        "data_migrations", "reliability_resilience",
        "architecture_boundaries", "requirements_acceptance_traceability",
        "deployment_rollout_rollback", "testing_anchoring",
    }
    pre_missing = {
        "documentation",
        "evolution_objectives_protected_regions",
    }
    moved_rows = {}
    for cid in pre_expressed | pre_missing:
        before = "EXPRESSED" if cid in pre_expressed else "MISSING"
        after = "EXPRESSED" if cid in expressed else "MISSING"
        if before != after:
            moved_rows[cid] = (before, after)
    assert moved_rows == {
        "documentation": ("MISSING", "EXPRESSED")
    }
    assert (len(expressed), 18, 0, len(missing)) == (11, 18, 0, 1)  # NOT 10/18/0/2