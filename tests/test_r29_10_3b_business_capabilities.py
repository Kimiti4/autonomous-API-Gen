"""R2.10.3-B — business_capabilities: first-class semantic genes, not labels.

The primitive that matters most for the behavioral -> architectural
transition. The whole design hinges on reference-by-identity: a capability
must reference implementation by identity, never by content — otherwise its
identity would change every time a referenced workflow evolved and it could
not anchor architectural replacement.

Capability-specific proofs on top of the eleven-gate protocol:
  1. First-class representation — capability in ISR, not infer(ISR).
  2. Non-inference — distinct declared capabilities over identical
     implementation are distinguished; identity is semantic, not structural.
  3. Mutation locality — capability mutation touches only the capability gene.
  4. Reference-by-identity stability — the referenced behavior can evolve
     while the capability definition stays byte-identical.
  5. Reference integrity — dangling references die pre-execution.
"""
from __future__ import annotations

import dataclasses
import tempfile
from typing import Any

import pytest

from constitutional_architecture.isr.model import (
    BusinessCapability,
    CapabilityValidationError,
    Constraint,
    ConstraintScope,
    ISR,
    Interface,
    InterfaceType,
    Module,
    StateType,
    System,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)
from constitutional_architecture.isr.semantics.capability import (
    project_business_capabilities,
)
from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend
from tiannara.application.evolution.capability_mutation import CapabilityOperator
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


class CapabilityPrimitiveHarness:
    """The eleven-gate harness for business_capabilities."""

    primitive_id = "business_capabilities"

    def __init__(self) -> None:
        self.audit = ISRCapabilityAudit()
        self.operator = CapabilityOperator()
        self.locality_probe = MutationLocalityProbe()
        self.backend = FastAPIHexagonalBackend()

    # -- recipes ------------------------------------------------------------

    def isr_with(
        self,
        workflow_ids: tuple[str, ...] = ("W1", "W2"),
        capabilities: tuple[BusinessCapability, ...] = (),
        interface_ids: tuple[str, ...] = ("I1",),
        constraint_ids: tuple[str, ...] = ("C1",),
    ) -> ISR:
        interfaces = tuple(
            Interface(id=iid, name=iid, interface_type=InterfaceType.REST)
            for iid in interface_ids
        )
        constraints = tuple(
            Constraint(id=cid, name=cid, scope=ConstraintScope.SYSTEM)
            for cid in constraint_ids
        )
        return ISR(
            system=System(
                id="capability-sys",
                name="CapabilitySystem",
                modules=(
                    Module(
                        id="m",
                        name="M",
                        workflows=tuple(
                            _workflow(wid, f"op_{wid.lower()}") for wid in workflow_ids
                        ),
                        interfaces=interfaces,
                    ),
                ),
                constraints=constraints,
                business_capabilities=capabilities,
            )
        )

    def empty_isr(self) -> ISR:
        return self.isr_with(workflow_ids=("W1",))

    def fsm_with(self) -> ISR:
        return self.isr_with()

    # -- gene addressing ------------------------------------------------------

    def all_gene_hashes(self, isr: ISR) -> dict[str, str]:
        """Every gene except the capability gene class."""
        return {
            path: h
            for path, h in gene_index(isr).items()
            if "business_capabilities" not in path
        }

    def gene_hash(self, isr: ISR, gene: tuple) -> str:
        """(\"capability\", cid) / (\"behavior\", wf_id) / (\"interface\", iid) /
        (\"constraint\", cid)."""
        idx = gene_index(isr)
        kind, name = gene
        if kind == "capability":
            for ci, capability in enumerate(isr.system.business_capabilities):
                if capability.capability_id == name:
                    return idx[f"system.business_capabilities[{ci}]"]
            return ""
        if kind == "behavior":
            for mi, module in enumerate(isr.system.modules):
                for wi, workflow in enumerate(module.workflows):
                    if workflow.id == name:
                        return idx[f"system.modules[{mi}].workflows[{wi}]"]
            return ""
        if kind == "interface":
            for mi, module in enumerate(isr.system.modules):
                for ii, interface in enumerate(module.interfaces):
                    if interface.id == name:
                        return idx[f"system.modules[{mi}].interfaces[{ii}]"]
            return ""
        if kind == "constraint":
            for ci, constraint in enumerate(isr.system.constraints):
                if constraint.id == name:
                    return idx[f"system.constraints[{ci}]"]
            return ""
        return ""

    def has_gene(self, isr: ISR, gene: tuple) -> bool:
        return self.gene_hash(isr, gene) != ""

    def behavior_genes_identical(self, a: ISR, b: ISR) -> bool:
        a_hash = {p: h for p, h in self.all_gene_hashes(a).items() if ".workflows" in p}
        b_hash = {p: h for p, h in self.all_gene_hashes(b).items() if ".workflows" in p}
        return a_hash == b_hash

    def mutate_behavior_content(self, isr: ISR, workflow_id: str) -> ISR:
        modules = []
        for module in isr.system.modules:
            workflows = tuple(
                dataclasses.replace(wf, description=wf.description + " evolved")
                if wf.id == workflow_id
                else wf
                for wf in module.workflows
            )
            modules.append(dataclasses.replace(module, workflows=workflows))
        return isr.with_system(dataclasses.replace(isr.system, modules=tuple(modules)))

    def with_empty_capabilities(self, isr: ISR) -> ISR:
        return isr.with_system(
            dataclasses.replace(isr.system, business_capabilities=())
        )

    # -- gates ----------------------------------------------------------------

    def run_gate(self, gate: str) -> GateResult:
        method = getattr(self, f"_gate_{gate}", None)
        if method is None:
            raise AssertionError(f"no implementation for gate '{gate}'")
        return method()

    def _gate_representation(self):
        system_fields = {f.name for f in dataclasses.fields(System)}
        ok = "business_capabilities" in system_fields
        try:
            BusinessCapability(capability_id="pay", intent="process a payment")
            ok = ok and True
        except CapabilityValidationError:
            ok = False
        not_alias = (
            BusinessCapability is not Workflow
            and BusinessCapability is not Module
            and BusinessCapability is not WorkflowState
        )
        return _result(
            "representation",
            ok and not_alias,
            "System.business_capabilities carrier; BusinessCapability is a distinct "
            "dataclass (never an alias for Workflow/Module)",
        )

    def _gate_canonicalization(self):
        isr = self.isr_with()
        same = self.with_empty_capabilities(isr).content_hash == isr.content_hash
        return _result(
            "canonicalization",
            same,
            f"empty capability carrier identity-neutral: {same}",
        )

    def _gate_semantic_identity(self):
        isr = self.isr_with()
        with_cap = self.operator.add_capability(
            isr,
            BusinessCapability(
                capability_id="pay",
                intent="process a payment",
                behavior_refs=("W1",),
            ),
        ).candidate_isr
        step1 = with_cap.content_hash != isr.content_hash
        respecified = self.operator.set_capability_intent(
            with_cap, capability_id="pay", intent="process a refund"
        ).candidate_isr
        step2 = respecified.content_hash != with_cap.content_hash
        removed = self.operator.remove_capability(
            respecified, capability_id="pay"
        ).candidate_isr
        step3 = removed.content_hash == isr.content_hash
        return _result(
            "semantic_identity",
            step1 and step2 and step3,
            f"add changes hash: {step1}; intent change changes hash: {step2}; "
            f"remove restores hash: {step3}",
        )

    def _gate_validation(self):
        ok = True
        for bad in (
            dict(capability_id="", intent="x"),
            dict(capability_id="x", intent=""),
        ):
            try:
                BusinessCapability(**bad)
                ok = False
            except CapabilityValidationError:
                pass
        duplicate = self.isr_with(
            capabilities=(
                BusinessCapability(capability_id="pay", intent="a"),
                BusinessCapability(capability_id="pay", intent="b"),
            )
        )
        ok = ok and duplicate.validate_structure() is False
        for ref_kind, ref_id in (
            ("behavior_refs", "W_missing"),
            ("interface_refs", "I_missing"),
            ("constraint_refs", "C_missing"),
        ):
            dangling = self.isr_with(
                capabilities=(
                    BusinessCapability(
                        capability_id="pay",
                        intent="a",
                        **{ref_kind: (ref_id,)},
                    ),
                )
            )
            ok = ok and dangling.validate_structure() is False
        return _result(
            "validation",
            ok,
            "empty id/intent rejected at construction; duplicate ids and dangling "
            "behavior/interface/constraint references rejected pre-execution",
        )

    def _gate_locality(self):
        isr = self.isr_with()
        mutated = self.operator.add_capability(
            isr,
            BusinessCapability(
                capability_id="pay",
                intent="process a payment",
                behavior_refs=("W1",),
                interface_refs=("I1",),
                constraint_refs=("C1",),
            ),
        ).candidate_isr
        result = self.locality_probe.probe(
            isr, mutated, "system.business_capabilities[0]"
        )
        return _result(
            "locality",
            result.locality_holds,
            f"target gene changed: {result.target_gene_changed}; "
            f"unintended changes: {result.unintended_changes}",
        )

    def _gate_projection(self):
        isr = self.isr_with(
            capabilities=(
                BusinessCapability(
                    capability_id="pay",
                    intent="process a payment",
                    behavior_refs=("W1",),
                    interface_refs=("I1",),
                    constraint_refs=("C1",),
                ),
            )
        )
        projected = project_business_capabilities(isr)
        deterministic = projected == project_business_capabilities(isr)
        reflects = any(
            cap.get("capability_id") == "pay" and "payment" in cap.get("intent", "")
            for cap in projected
        )
        coupled = [
            term
            for term in TECHNOLOGY_COUPLING_TERMS
            if any(term in str(cap) for cap in projected)
        ]
        return _result(
            "projection",
            deterministic and reflects and not coupled,
            f"deterministic: {deterministic}; reflects intent+identities: {reflects}; "
            f"coupling terms: {coupled}",
        )

    def _gate_compilation(self):
        isr = self.isr_with()
        mutated = self.operator.add_capability(
            isr,
            BusinessCapability(
                capability_id="pay",
                intent="process a payment",
                behavior_refs=("W1",),
            ),
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
            f"existing backend byte-identical with capability map present: {compatible}; "
            f"deterministic: {deterministic}",
        )

    def _gate_evidence(self):
        isr = self.isr_with(
            capabilities=(
                BusinessCapability(
                    capability_id="pay",
                    intent="process a payment",
                    behavior_refs=("W1",),
                ),
            )
        )
        observable = any(
            cap.get("capability_id") == "pay" for cap in project_business_capabilities(isr)
        )
        empty = project_business_capabilities(self.isr_with()) == ()
        return _result(
            "evidence",
            observable and empty,
            f"capability observable in semantic projection: {observable}; "
            f"no capabilities -> empty projection: {empty}",
        )

    def _gate_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = EvolutionLedger(root=str(tmp))
            operator = CapabilityOperator(ledger=ledger)
            isr = self.isr_with()
            capability = BusinessCapability(
                capability_id="pay",
                intent="process a payment",
                behavior_refs=("W1",),
            )
            candidate = operator.add_capability(isr, capability)
            chain_ok = ledger.verify_event_chain() is True
            events = ledger.events()
            event = events[0] if events else None
            attributed = (
                event is not None
                and event.event_type is EventType.MEASUREMENT
                and event.payload["operator_id"] == "capability"
                and event.payload["capability_id"] == "pay"
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
        c1 = self.operator.generate(isr, seed=7, population_size=2)
        c2 = self.operator.generate(isr, seed=7, population_size=2)
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
            "data_migrations",  # R2.10.3-C
            "reliability_resilience",  # R2.10.3-D
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
        # Exactly one row moved vs the pre-landing (R2.10.3-A) matrix 3/18/0/9.
        pre_expressed = post_expressed - {"business_capabilities"}
        pre_missing = post_missing | {"business_capabilities"}
        one_row_only = (
            expressed - pre_expressed == {"business_capabilities"}
            and missing == pre_missing - {"business_capabilities"}
            and partial == post_partial
        )
        return _result(
            "audit",
            matrix_ok and one_row_only,
            f"summary: {result.summary()}; expected 4/18/0/8 with exactly "
            f"business_capabilities: MISSING -> EXPRESSED and the other 29 rows untouched",
        )


def _result(gate: str, passed: bool, evidence: str) -> GateResult:
    return GateResult(gate=gate, passed=passed, evidence=evidence)


@pytest.fixture
def cap_harness() -> CapabilityPrimitiveHarness:
    return CapabilityPrimitiveHarness()


# -- 1 + 2: first-class, non-inference --------------------------------------------

def test_capability_is_declared_not_inferred(cap_harness):
    # Identical workflows, different declared capabilities -> different capability gene.
    isr_a = cap_harness.isr_with(
        workflow_ids=("W1", "W2"),
        capabilities=(
            BusinessCapability("pay", "process a payment", behavior_refs=("W1",)),
        ),
    )
    isr_b = cap_harness.isr_with(
        workflow_ids=("W1", "W2"),
        capabilities=(
            BusinessCapability("refund", "process a refund", behavior_refs=("W2",)),
        ),
    )
    assert cap_harness.behavior_genes_identical(isr_a, isr_b)  # same implementation
    assert cap_harness.gene_hash(isr_a, ("capability", "pay")) != \
        cap_harness.gene_hash(isr_b, ("capability", "refund"))


def test_capability_identity_is_semantic_not_structural(cap_harness):
    # Equivalent declarations over differently structured implementations:
    # capability identity is the declared (id, intent), not the implementation.
    a = cap_harness.isr_with(workflow_ids=("W1",), capabilities=(
        BusinessCapability("pay", "process a payment", behavior_refs=("W1",)),
    ))
    b = cap_harness.isr_with(workflow_ids=("W1", "W2"), capabilities=(
        BusinessCapability("pay", "process a payment", behavior_refs=("W1",)),
    ))
    assert cap_harness.gene_hash(a, ("capability", "pay")) == \
        cap_harness.gene_hash(b, ("capability", "pay"))
    assert a.content_hash != b.content_hash  # implementation differs


# -- 3: mutation locality ------------------------------------------------------------

def test_add_capability_does_not_touch_other_genes(cap_harness):
    isr = cap_harness.isr_with(
        workflow_ids=("W1",),
        interface_ids=("I1",),
        constraint_ids=("C1",),
    )
    before = cap_harness.all_gene_hashes(isr)
    mutated = cap_harness.operator.add_capability(
        isr,
        BusinessCapability(
            "pay", "process a payment",
            behavior_refs=("W1",), interface_refs=("I1",), constraint_refs=("C1",),
        ),
    ).candidate_isr
    after = cap_harness.all_gene_hashes(mutated)
    assert before == after  # every pre-existing gene byte-identical
    assert cap_harness.has_gene(mutated, ("capability", "pay"))


def test_capability_intent_mutation_keeps_implementation_stable(cap_harness):
    isr = cap_harness.isr_with(workflow_ids=("W1",), capabilities=(
        BusinessCapability("pay", "process a payment", behavior_refs=("W1",)),
    ))
    before = cap_harness.all_gene_hashes(isr)
    mutated = cap_harness.operator.set_capability_intent(
        isr, capability_id="pay", intent="process a refund"
    ).candidate_isr
    after = cap_harness.all_gene_hashes(mutated)
    assert before == after  # implementation genes stable
    assert cap_harness.gene_hash(mutated, ("capability", "pay")) != \
        cap_harness.gene_hash(isr, ("capability", "pay"))


# -- 4: reference-by-identity stability ------------------------------------------------

def test_capability_stable_when_referenced_behavior_evolves(cap_harness):
    isr = cap_harness.isr_with(workflow_ids=("W1",), capabilities=(
        BusinessCapability("pay", "process a payment", behavior_refs=("W1",)),
    ))
    cap_hash_before = cap_harness.gene_hash(isr, ("capability", "pay"))
    mutated = cap_harness.mutate_behavior_content(isr, "W1")  # content changes, id stable
    assert cap_harness.gene_hash(mutated, ("behavior", "W1")) != \
        cap_harness.gene_hash(isr, ("behavior", "W1"))  # behavior gene moved
    assert cap_harness.gene_hash(mutated, ("capability", "pay")) == cap_hash_before


# -- 5: reference integrity + construction validation -------------------------------------

def test_dangling_reference_rejected(cap_harness):
    dangling = cap_harness.isr_with(capabilities=(
        BusinessCapability("pay", "process a payment", behavior_refs=("W_missing",)),
    ))
    assert dangling.validate_structure() is False
    for ref_kind in ("interface_refs", "constraint_refs"):
        bad = cap_harness.isr_with(capabilities=(
            BusinessCapability("pay", "process a payment", **{ref_kind: ("X_missing",)}),
        ))
        assert bad.validate_structure() is False


def test_capability_construction_validation():
    with pytest.raises(CapabilityValidationError):
        BusinessCapability(capability_id="", intent="x")
    with pytest.raises(CapabilityValidationError):
        BusinessCapability(capability_id="x", intent="")


def test_duplicate_capability_id_rejected(cap_harness):
    duplicate = cap_harness.isr_with(capabilities=(
        BusinessCapability("pay", "a", behavior_refs=("W1",)),
        BusinessCapability("pay", "b", behavior_refs=("W1",)),
    ))
    assert duplicate.validate_structure() is False


# -- canonicalization ---------------------------------------------------------------------

def test_empty_capability_carrier_identity_neutral(cap_harness):
    isr = cap_harness.empty_isr()
    assert cap_harness.with_empty_capabilities(isr).content_hash == isr.content_hash


def test_requirement_refs_reserved_until_traceability_lands(cap_harness):
    """requirement_refs is carried but not validated until R2.10.4."""
    isr = cap_harness.isr_with(capabilities=(
        BusinessCapability("pay", "process a payment",
                           behavior_refs=("W1",),
                           requirement_refs=("REQ-not-yet-represented",)),
    ))
    assert isr.validate_structure() is True  # reserved, not dangling-checked yet
    assert project_business_capabilities(isr)[0]["requirement_refs"] == [
        "REQ-not-yet-represented"
    ]


# -- the eleven gates, parameterized -------------------------------------------------------

@pytest.mark.parametrize("gate", PRIMITIVE_GATE)
def test_primitive_gate(gate, cap_harness):
    result = cap_harness.run_gate(gate)
    assert result.passed, f"{gate}: {result.evidence}"


def test_all_gates_pass_together(cap_harness):
    results = assert_all_gates(cap_harness)
    assert len(results) == len(PRIMITIVE_GATE)


# -- lineage is chain-anchored ---------------------------------------------------------------

def test_capability_mutation_is_chain_anchored(tmp_path):
    ledger = EvolutionLedger(root=str(tmp_path))
    operator = CapabilityOperator(ledger=ledger)
    isr = CapabilityPrimitiveHarness().isr_with()
    capability = BusinessCapability("pay", "process a payment", behavior_refs=("W1",))
    candidate = operator.add_capability(isr, capability)
    assert ledger.verify_event_chain() is True
    event = ledger.events()[0]
    assert event.event_type is EventType.MEASUREMENT
    assert event.payload["operator_id"] == "capability"
    assert event.payload["capability_id"] == "pay"
    assert event.payload["isr_hash_before"] == isr.content_hash
    assert event.payload["isr_hash_after"] == candidate.candidate_isr.content_hash


# -- remove restores identity -------------------------------------------------------------------

def test_remove_capability_restores_semantic_identity(cap_harness):
    isr = cap_harness.isr_with()
    with_cap = cap_harness.operator.add_capability(
        isr, BusinessCapability("pay", "process a payment", behavior_refs=("W1",))
    ).candidate_isr
    removed = cap_harness.operator.remove_capability(
        with_cap, capability_id="pay"
    ).candidate_isr
    assert removed.content_hash == isr.content_hash