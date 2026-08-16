"""R2.10.3-A — behavior_temporal_semantics: the first primitive landing.

The proving run for the R2.10.2 extension protocol: this primitive extends
the one gene surface already EXPRESSED (behavior), so it must prove a new
primitive can land on an already-evolvable gene without disturbing it.

The critical test is not "temporal semantics can be represented" but
"temporal semantics can be independently evolved" without unintentionally
changing unrelated behavior genes.

Eleven gates (PRIMITIVE_GATE) run through a single parameterized harness —
the same suite R2.10.3-B/C/D will point at their own primitives.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from constitutional_architecture.isr.model import (
    Event,
    EventGuarantee,
    EventPattern,
    ISR,
    Module,
    StateType,
    System,
    TemporalConstraint,
    TemporalConstraintKind,
    TemporalValidationError,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)
from constitutional_architecture.isr.semantics.projection import canonicalize
from constitutional_architecture.isr.semantics.temporal import (
    project_temporal_evidence,
    project_temporal_semantics,
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
from tiannara.application.evolution.temporal_mutation import TemporalConstraintOperator


def _recipe_isr() -> ISR:
    """Focused temporal recipe: one module, two transitions, awaiting states,
    and two events (for EVENT_ORDERING references)."""
    module = Module(
        id="orders",
        name="Orders",
        workflows=(
            Workflow(
                id="wf-orders",
                name="Order lifecycle",
                states=(
                    WorkflowState(
                        id="await-payment",
                        name="awaiting payment",
                        state_type=StateType.INTERMEDIATE,
                        metadata={"awaits": "collect_payment"},
                    ),
                    WorkflowState(
                        id="placed",
                        name="placed",
                        state_type=StateType.FINAL,
                    ),
                    WorkflowState(
                        id="failed",
                        name="failed",
                        state_type=StateType.ERROR,
                    ),
                ),
                transitions=(
                    WorkflowTransition(
                        id="t1",
                        name="payment collected",
                        from_state_id="await-payment",
                        to_state_id="placed",
                        trigger="collect_payment",
                    ),
                    WorkflowTransition(
                        id="t2",
                        name="payment failed",
                        from_state_id="await-payment",
                        to_state_id="failed",
                        trigger="fail_payment",
                    ),
                ),
            ),
        ),
        events=(
            Event(
                id="order-placed",
                name="order placed",
                pattern=EventPattern.PUBLISH_SUBSCRIBE,
                guarantee=EventGuarantee.AT_LEAST_ONCE,
            ),
            Event(
                id="payment-settled",
                name="payment settled",
                pattern=EventPattern.REQUEST_REPLY,
                guarantee=EventGuarantee.EXACTLY_ONCE,
            ),
        ),
    )
    return ISR(system=System(id="temporal-sys", name="TemporalSystem", modules=(module,)))


def _replace_module_constraints(isr: ISR, module_id: str, constraints) -> ISR:
    modules = []
    for module in isr.system.modules:
        if module.id == module_id:
            module = dataclasses.replace(module, temporal_constraints=tuple(constraints))
        modules.append(module)
    return isr.with_system(dataclasses.replace(isr.system, modules=tuple(modules)))


class TemporalPrimitiveHarness:
    """The eleven-gate harness for behavior_temporal_semantics."""

    primitive_id = "behavior_temporal_semantics"

    def __init__(self) -> None:
        self.audit = ISRCapabilityAudit()
        self.operator = TemporalConstraintOperator()
        self.locality_probe = MutationLocalityProbe()
        self.backend = FastAPIHexagonalBackend()

    # -- recipe ------------------------------------------------------------

    def fsm_with_transitions(self) -> ISR:
        return _recipe_isr()

    def transition_ids(self, isr: ISR) -> tuple[str, ...]:
        return tuple(
            t.id for m in isr.system.modules for wf in m.workflows for t in wf.transitions
        )

    def gene_hash(self, isr: ISR, gene: tuple) -> str:
        """Semantic hash of one gene, addressed like the audit's gene_index.

        (\"transition\", tid) -> the transition gene
        (\"await\", tid)      -> the state gene awaiting that transition's trigger
        (\"temporal\", cid)   -> the temporal constraint gene
        """
        idx = gene_index(isr)
        kind, name = gene
        for mi, module in enumerate(isr.system.modules):
            for wi, workflow in enumerate(module.workflows):
                for ti, transition in enumerate(workflow.transitions):
                    if kind == "transition" and transition.id == name:
                        return idx[f"system.modules[{mi}].workflows[{wi}].transitions[{ti}]"]
                    if kind == "await" and transition.id == name:
                        for si, state in enumerate(workflow.states):
                            if state.metadata.get("awaits") == transition.trigger:
                                return idx[
                                    f"system.modules[{mi}].workflows[{wi}].states[{si}]"
                                ]
            if kind == "temporal":
                for ci, constraint in enumerate(module.temporal_constraints):
                    if constraint.constraint_id == name:
                        return idx[f"system.modules[{mi}].temporal_constraints[{ci}]"]
        return ""

    def add_deadline(self, isr: ISR, transition_id: str, duration_ms: int) -> ISR:
        return self.operator.add_deadline(
            isr, transition_id=transition_id, duration_ms=duration_ms
        ).candidate_isr

    def with_empty_temporal(self, isr: ISR) -> ISR:
        modules = tuple(
            dataclasses.replace(m, temporal_constraints=())
            for m in isr.system.modules
        )
        return isr.with_system(dataclasses.replace(isr.system, modules=modules))

    # -- gates -------------------------------------------------------------

    def run_gate(self, gate: str):
        method = getattr(self, f"_gate_{gate}", None)
        if method is None:
            return pytest.fail(f"no implementation for gate '{gate}'")
        return method()

    def _gate_representation(self):
        fields = {f.name for f in dataclasses.fields(Module)}
        ok = "temporal_constraints" in fields
        kinds = {k.value for k in TemporalConstraintKind}
        ok = ok and kinds == {"TRANSITION_DEADLINE", "STATE_MIN_DURATION", "EVENT_ORDERING"}
        for kind in TemporalConstraintKind:
            ok = ok and self._construct(kind) is not None
        return _result(
            "representation",
            ok,
            "Module.temporal_constraints carrier + TemporalConstraint for all three kinds",
        )

    def _gate_canonicalization(self):
        isr = self.fsm_with_transitions()
        empty = self.with_empty_temporal(isr)
        same = empty.content_hash == isr.content_hash
        present = _replace_module_constraints(
            isr, "orders", (TemporalConstraint(
                constraint_id="t1.deadline",
                kind=TemporalConstraintKind.TRANSITION_DEADLINE,
                target_ref="t1",
                duration_ms=250,
            ),)
        )
        canonical = canonicalize(present)
        meaningful = "250" in canonical and "t1.deadline" in canonical
        return _result(
            "canonicalization",
            same and meaningful,
            f"empty carrier identity-neutral: {same}; meaningful content projected: {meaningful}",
        )

    def _gate_semantic_identity(self):
        isr = self.fsm_with_transitions()
        with_deadline = self.add_deadline(isr, transition_id="t1", duration_ms=250)
        step1 = with_deadline.content_hash != isr.content_hash
        edited = self.operator.edit_duration(
            with_deadline, constraint_id="t1.deadline", new_duration_ms=500
        ).candidate_isr
        step2 = edited.content_hash != with_deadline.content_hash
        removed = self.operator.remove_constraint(
            edited, constraint_id="t1.deadline"
        ).candidate_isr
        step3 = removed.content_hash == isr.content_hash
        return _result(
            "semantic_identity",
            step1 and step2 and step3,
            f"add changes hash: {step1}; edit changes hash: {step2}; remove restores hash: {step3}",
        )

    def _gate_validation(self):
        ok = True
        try:
            TemporalConstraint(
                constraint_id="bad", kind=TemporalConstraintKind.TRANSITION_DEADLINE,
                target_ref="t1", duration_ms=-1,
            )
            ok = False
        except TemporalValidationError:
            pass
        try:
            TemporalConstraint(
                constraint_id="bad", kind=TemporalConstraintKind.EVENT_ORDERING,
                target_ref="payment-settled", duration_ms=100,
            )
            ok = False
        except TemporalValidationError:
            pass
        dangling = _replace_module_constraints(
            self.fsm_with_transitions(), "orders",
            (TemporalConstraint(
                constraint_id="dangling", kind=TemporalConstraintKind.TRANSITION_DEADLINE,
                target_ref="no-such-transition", duration_ms=100,
            ),),
        )
        ok = ok and dangling.validate_structure() is False
        bad_order = _replace_module_constraints(
            self.fsm_with_transitions(), "orders",
            (TemporalConstraint(
                constraint_id="bad-order", kind=TemporalConstraintKind.EVENT_ORDERING,
                target_ref="payment-settled", duration_ms=100, reference_ref="no-such-event",
            ),),
        )
        ok = ok and bad_order.validate_structure() is False
        return _result(
            "validation",
            ok,
            "negative duration / missing ordering reference rejected at construction; dangling targets and references rejected pre-execution",
        )

    def _gate_locality(self):
        isr = self.fsm_with_transitions()
        mutated = self.add_deadline(isr, transition_id="t1", duration_ms=250)
        result = self.locality_probe.probe(
            isr, mutated, "system.modules[0].temporal_constraints[0]"
        )
        return _result(
            "locality",
            result.locality_holds,
            f"target gene changed: {result.target_gene_changed}; "
            f"unintended changes: {result.unintended_changes}",
        )

    def _gate_projection(self):
        isr = self.add_deadline(self.fsm_with_transitions(), "t1", 250)
        projected = project_temporal_semantics(isr)
        deterministic = projected == project_temporal_semantics(isr)
        reflects = any(
            "transition t1 must complete within 250ms of its trigger" == line
            for line in projected
        )
        coupled = [
            term for term in TECHNOLOGY_COUPLING_TERMS
            if any(term in line for line in projected)
        ]
        return _result(
            "projection",
            deterministic and reflects and not coupled,
            f"deterministic: {deterministic}; reflects deadline: {reflects}; "
            f"coupling terms in projection: {coupled}",
        )

    def _gate_compilation(self):
        isr = self.fsm_with_transitions()
        mutated = self.add_deadline(isr, transition_id="t1", duration_ms=250)
        before = self.backend.async_resolution_module(
            isr.system.modules[0].workflows
        )
        after = self.backend.async_resolution_module(
            mutated.system.modules[0].workflows
        )
        compatible = before == after
        deterministic = self.backend.async_resolution_module(
            mutated.system.modules[0].workflows
        ) == after
        return _result(
            "compilation",
            compatible and deterministic,
            f"existing backend byte-identical with temporal gene present: {compatible}; "
            f"deterministic: {deterministic}",
        )

    def _gate_evidence(self):
        isr = self.add_deadline(self.fsm_with_transitions(), "t1", 250)
        evidence = project_temporal_evidence(isr)
        reflects = any(
            "t1.deadline" in line and "TRANSITION_DEADLINE" in line and "t1" in line
            for line in evidence
        )
        empty_evidence = project_temporal_evidence(self.fsm_with_transitions()) == ()
        return _result(
            "evidence",
            reflects and empty_evidence,
            f"constraint observable in evidence projection: {reflects}; "
            f"no constraints -> no evidence: {empty_evidence}",
        )

    def _gate_lineage(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            ledger = EvolutionLedger(root=str(tmp))
            operator = TemporalConstraintOperator(ledger=ledger)
            isr = self.fsm_with_transitions()
            candidate = operator.add_deadline(isr, transition_id="t1", duration_ms=250)
            chain_ok = ledger.verify_event_chain() is True
            events = ledger.events()
            event = events[0] if events else None
            attributed = (
                event is not None
                and event.event_type is EventType.MEASUREMENT
                and event.payload["operator_id"] == "temporal_constraint"
                and event.payload["constraint_id"] == "t1.deadline"
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
        isr = self.fsm_with_transitions()
        c1 = self.operator.generate(isr, seed=7, population_size=2)
        c2 = self.operator.generate(isr, seed=7, population_size=2)
        same = (
            len(c1) == len(c2) == 2
            and all(
                a.candidate_id == b.candidate_id
                and a.candidate_isr.content_hash == b.candidate_isr.content_hash
                and a.mutation_delta == b.mutation_delta
                for a, b in zip(c1, c2)
            )
        )
        return _result(
            "reproducibility",
            same,
            "same ISR + seed -> same candidate ids, hashes, and deltas",
        )

    def _gate_audit(self):
        result = self.audit.run(self.fsm_with_transitions())
        by_id = {c.capability_id: c.status for c in result.capabilities}
        expressed = {cid for cid, status in by_id.items() if status is CapabilityStatus.EXPRESSED}
        partial = {cid for cid, status in by_id.items() if status is CapabilityStatus.PARTIAL}
        missing = {cid for cid, status in by_id.items() if status is CapabilityStatus.MISSING}
        expected_expressed = {
            "behavior_transitions", "behavior_await_surface",
            "behavior_temporal_semantics", "business_capabilities",  # R2.10.3-B
            "data_migrations",  # R2.10.3-C
            "reliability_resilience",  # R2.10.3-D
        }
        expected_partial = {
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
        expected_missing = {
            "architecture_boundaries", "deployment_rollout_rollback",
            "requirements_acceptance_traceability",
            "documentation", "testing_anchoring",
            "evolution_objectives_protected_regions",
        }
        one_row_only = (
            expressed == expected_expressed
            and partial == expected_partial
            and missing == expected_missing
            and CapabilityStatus.PROJECTED not in by_id.values()
        )
        return _result(
            "audit",
            one_row_only,
            f"summary: {result.summary()}; expected 3/18/0/9 with exactly "
            f"behavior_temporal_semantics: MISSING -> EXPRESSED and the other 29 rows untouched",
        )

    @staticmethod
    def _construct(kind: TemporalConstraintKind) -> TemporalConstraint:
        if kind is TemporalConstraintKind.EVENT_ORDERING:
            return TemporalConstraint(
                constraint_id="x", kind=kind, target_ref="payment-settled",
                duration_ms=100, reference_ref="order-placed",
            )
        return TemporalConstraint(
            constraint_id="x", kind=kind, target_ref="t1", duration_ms=100,
        )


def _result(gate: str, passed: bool, evidence: str):
    return GateResult(gate=gate, passed=passed, evidence=evidence)


@pytest.fixture
def temporal_harness() -> TemporalPrimitiveHarness:
    return TemporalPrimitiveHarness()


# -- the critical tests ---------------------------------------------------------

def test_temporal_mutation_does_not_touch_transition_genes(temporal_harness):
    isr = temporal_harness.fsm_with_transitions()
    transition_hashes_before = {
        tid: temporal_harness.gene_hash(isr, ("transition", tid))
        for tid in temporal_harness.transition_ids(isr)
    }
    await_hashes_before = {
        tid: temporal_harness.gene_hash(isr, ("await", tid))
        for tid in temporal_harness.transition_ids(isr)
    }

    mutated = temporal_harness.add_deadline(isr, transition_id="t1", duration_ms=250)

    # The temporal gene changed...
    assert temporal_harness.gene_hash(mutated, ("temporal", "t1.deadline")) != \
        temporal_harness.gene_hash(isr, ("temporal", "t1.deadline"))
    # ...and NOTHING else did.
    for tid, h in transition_hashes_before.items():
        assert temporal_harness.gene_hash(mutated, ("transition", tid)) == h
    for tid, h in await_hashes_before.items():
        assert temporal_harness.gene_hash(mutated, ("await", tid)) == h


def test_empty_temporal_is_identity_neutral(temporal_harness):
    """Option A landing rule: adding the empty carrier changes nothing."""
    isr = temporal_harness.fsm_with_transitions()
    assert temporal_harness.with_empty_temporal(isr).content_hash == isr.content_hash


def test_temporal_change_moves_semantic_hash(temporal_harness):
    isr = temporal_harness.fsm_with_transitions()
    mutated = temporal_harness.add_deadline(isr, transition_id="t1", duration_ms=250)
    assert mutated.content_hash != isr.content_hash


# -- the eleven gates, parameterized ---------------------------------------------

@pytest.mark.parametrize("gate", PRIMITIVE_GATE)
def test_primitive_gate(gate, temporal_harness):
    result = temporal_harness.run_gate(gate)
    assert result.passed, f"{gate}: {result.evidence}"


def test_all_gates_pass_together(temporal_harness):
    results = assert_all_gates(temporal_harness)
    assert len(results) == len(PRIMITIVE_GATE)


# -- validation is pre-execution ---------------------------------------------------

def test_negative_duration_rejected_at_construction():
    with pytest.raises(TemporalValidationError):
        TemporalConstraint(
            constraint_id="bad", kind=TemporalConstraintKind.TRANSITION_DEADLINE,
            target_ref="t1", duration_ms=-1,
        )


def test_event_ordering_requires_reference_at_construction():
    with pytest.raises(TemporalValidationError):
        TemporalConstraint(
            constraint_id="bad", kind=TemporalConstraintKind.EVENT_ORDERING,
            target_ref="payment-settled", duration_ms=100,
        )


def test_dangling_target_rejected_pre_execution():
    isr = _replace_module_constraints(
        _recipe_isr(), "orders",
        (TemporalConstraint(
            constraint_id="dangling", kind=TemporalConstraintKind.TRANSITION_DEADLINE,
            target_ref="no-such-transition", duration_ms=100,
        ),),
    )
    assert isr.validate_structure() is False


# -- lineage is chain-anchored ------------------------------------------------------

def test_temporal_mutation_is_chain_anchored(tmp_path: Path):
    ledger = EvolutionLedger(root=str(tmp_path))
    operator = TemporalConstraintOperator(ledger=ledger)
    isr = _recipe_isr()
    candidate = operator.add_deadline(isr, transition_id="t1", duration_ms=250)
    assert ledger.verify_event_chain() is True
    event = ledger.events()[0]
    assert event.event_type is EventType.MEASUREMENT
    assert event.payload["operator_id"] == "temporal_constraint"
    assert event.payload["isr_hash_before"] == isr.content_hash
    assert event.payload["isr_hash_after"] == candidate.candidate_isr.content_hash


# -- remove restores identity --------------------------------------------------------

def test_remove_constraint_restores_semantic_identity(temporal_harness):
    isr = temporal_harness.fsm_with_transitions()
    with_deadline = temporal_harness.add_deadline(isr, transition_id="t1", duration_ms=250)
    removed = temporal_harness.operator.remove_constraint(
        with_deadline, constraint_id="t1.deadline"
    ).candidate_isr
    assert removed.content_hash == isr.content_hash