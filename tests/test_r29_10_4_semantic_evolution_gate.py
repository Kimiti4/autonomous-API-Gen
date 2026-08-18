"""R2.10.4 — SemanticEvolutionGate: universal ISR evolution integration.

R2.10.1 (A) proved per-gene identity; R2.10.2 (B-H) and R2.10.3 (I, J)
added the semantic primitives. R2.10.4 proves they COMPOSE: one candidate
evolves >=4 independent genes across distinct domains (capability +
reliability + deployment + temporal) while

  1. locality holds                   — exactly the declared genes move;
                                       a hidden side effect on an unrelated
                                       gene is DETECTED (fail visible).
  2. cross-gene references hold       — the identity index (the ONE
                                       namespace) finds no new dangling
                                       reference; a delta that dangles is
                                       REJECTED by the gate.
  3. backend independence holds       — all ten primitives' mechanism lints
                                       aggregate; a coupled gene in a
                                       composition is REJECTED.
  4. the R2.8 evidence substrate holds — the gate holds no evaluation
                                       machinery of its own (the protection
                                       projection is consumed by the R2.8
                                       gate stack).
  5. reproducibility + ledger         — same parent + delta + seed ->
                                       same candidate hash and identical
                                       chain-anchored MEASUREMENT events
                                       with canonical edit lists.

Parent-authoritative invariant (permanent, enforced two ways): a candidate
is judged by the rules it was generated under, never by rules it authored.
R2.10.4 moves no matrix row and adds no carriers: the recipe ISR hash is
unchanged (the eleventh Option A use) and the matrix stays 12/18/0/0.
"""
from __future__ import annotations

import ast
import dataclasses
import inspect
import pathlib
import tempfile

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
    DocumentationAudience,
    DocumentationIntent,
    DocumentationPurpose,
    Entity,
    EvolutionObjective,
    EvolutionPolicy,
    FailureMode,
    ISR,
    Interface,
    InterfaceType,
    Module,
    ObjectiveDimension,
    ObjectiveDirection,
    ObjectiveTier,
    ObligationKind,
    PreservationInvariant,
    ProtectedRegion,
    ProtectionKind,
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
    Workflow,
    WorkflowState,
    WorkflowTransition,
)
from constitutional_architecture.isr.semantics.reliability import (
    RELIABILITY_MECHANISM_TERMS,
)
from tiannara.application.evolution.identity_index import SemanticIdentityIndex
from tiannara.application.evolution.isr_capability_audit import (
    CapabilityStatus,
    ISRCapabilityAudit,
)
from tiannara.application.evolution.ledger import (
    EventType,
    EvolutionLedger,
    stable_isr_hash,
)
from tiannara.application.evolution.semantic_evolution_gate import (
    PROOF_BACKEND_INDEPENDENCE,
    PROOF_LOCALITY,
    PROOF_R28_EVIDENCE_PATH,
    PROOF_REFERENCE_INTEGRITY,
    GeneEdit,
    MultiGeneDelta,
    SemanticEvolutionGate,
    apply_multi_gene_delta,
    is_projection_consumed_by_r28,
    resolve_evolution_policy,
)
from .test_r29_10_1_capability_audit import RECIPE


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


class BuggyApplicationGate(SemanticEvolutionGate):
    """An application layer that applies the declared delta AND silently
    touches an undeclared gene (the locality negative variant)."""

    def _apply(self, parent_isr, delta, seed):
        candidate = super()._apply(parent_isr, delta, seed)
        index = SemanticIdentityIndex()
        workflow = next(
            w
            for m in candidate.system.modules
            for w in m.workflows
            if w.id == "w1"
        )
        return index.replace_gene(
            candidate,
            "behavior",
            "w1",
            dataclasses.replace(workflow, description="touched by a buggy layer"),
        )


class SemanticEvolutionIntegrationHarness:
    """The R2.10.4 integration harness: a composition parent with all ten
    semantic carriers, the four-gene delta, and the negative variants."""

    def __init__(self) -> None:
        self.index = SemanticIdentityIndex()
        self._tmp = tempfile.TemporaryDirectory()
        self.ledger = EvolutionLedger(root=self._tmp.name)
        self.gate = SemanticEvolutionGate(
            identity_index=self.index, ledger=self.ledger
        )
        self.buggy_gate = BuggyApplicationGate(
            identity_index=self.index, ledger=self.ledger
        )
        self.last_verdict = None

    # -- parents ---------------------------------------------------------------

    def parent_isr(self) -> ISR:
        """The four-gene composition parent. region_1 protects the anchor and
        the boundary identities — the delta evolves capability / reliability
        / deployment / temporal, which the protection does not touch."""
        return ISR(
            system=System(
                id="r2.10.4-sys",
                name="SemanticEvolutionSystem",
                modules=(
                    Module(
                        id="m",
                        name="M",
                        entities=tuple(_entity(eid) for eid in ("e1", "e2")),
                        workflows=(_workflow("w1", "op_w1"),),
                        interfaces=(
                            Interface(
                                id="i1", name="i1",
                                interface_type=InterfaceType.REST,
                            ),
                        ),
                        temporal_constraints=(
                            TemporalConstraint(
                                constraint_id="t1.deadline",
                                kind=TemporalConstraintKind.TRANSITION_DEADLINE,
                                target_ref="w1-t1",
                                duration_ms=250,
                            ),
                        ),
                        data_migrations=(
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
                        ),
                    ),
                ),
                business_capabilities=(
                    BusinessCapability(
                        capability_id="capability_pay",
                        intent="process a payment",
                        behavior_refs=("w1",),
                        interface_refs=("i1",),
                    ),
                ),
                reliability_requirements=(
                    ReliabilityRequirement(
                        requirement_id="rr1",
                        target_refs=("capability_pay",),
                        failure_modes=(
                            FailureMode.TRANSIENT_DEPENDENCY_FAILURE,
                        ),
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
                ),
                architectural_boundaries=(
                    ArchitecturalBoundary(
                        boundary_id="b1",
                        member_refs=("m",),
                        forbidden_dependency_refs=(),
                        protected=False,
                        crossing_invariants=(
                            "no cross without declared intent",
                        ),
                    ),
                ),
                requirements=(
                    Requirement(
                        requirement_id="req.pay",
                        statement=(
                            "payments must complete within one business day"
                        ),
                        target_refs=("capability_pay",),
                        acceptance_refs=("crit.pay",),
                        constraint_refs=("w1",),
                    ),
                ),
                acceptance_criteria=(
                    AcceptanceCriterion(
                        criterion_id="crit.pay",
                        obligation=(
                            "payments must complete within one business day"
                        ),
                        kind=ObligationKind.PRESENCE,
                        subject_refs=("capability_pay",),
                    ),
                ),
                deployment_intents=(
                    DeploymentIntent(
                        deployment_id="dep1",
                        target_refs=("capability_pay",),
                        rollout_strategy=RolloutStrategy.CANARY,
                        rollback_required=True,
                        rollback_target_ref="capability_pay",
                        rollback_invariants=("payment state preserved",),
                    ),
                ),
                testing_anchors=(
                    TestingAnchor(
                        anchor_id="anchor1",
                        subject_refs=("w1",),
                        obligation_refs=("crit.pay",),
                        evidence_requirements=(
                            "the payment deadline intent must be demonstrable",
                        ),
                        protection_policy=ProtectionPolicy.EVOLVABLE,
                        authority=AnchorAuthority.DERIVED,
                    ),
                ),
                documentation_intents=(
                    DocumentationIntent(
                        documentation_id="doc1",
                        subject_refs=("capability_pay",),
                        purpose=DocumentationPurpose.OPERATIONAL_REFERENCE,
                        audience=DocumentationAudience.DEVELOPER,
                        obligations=(
                            "the capability's declared behavior must be documented",
                        ),
                    ),
                ),
                evolution_objectives=(
                    EvolutionObjective(
                        objective_id="opt1",
                        dimension=ObjectiveDimension.RELIABILITY,
                        direction=ObjectiveDirection.MAXIMIZE,
                        tier=ObjectiveTier.OPTIMIZATION,
                        priority=0,
                        weight=1.0,
                        subject_refs=("rr1",),
                    ),
                ),
                protected_regions=(
                    ProtectedRegion(
                        region_id="region_1",
                        subject_refs=("anchor1", "b1"),
                        protection_kind=ProtectionKind.IMMUTABLE,
                    ),
                ),
                evolution_policies=(
                    EvolutionPolicy(
                        policy_id="policy1",
                        objective_refs=("opt1",),
                        protected_region_refs=("region_1",),
                        selection_constraints=(
                            "no candidate may sacrifice the declared reliability",
                        ),
                    ),
                ),
            )
        )

    def multi_region_isr(self) -> ISR:
        """Two regions the four-gene delta puts in play simultaneously:
        region_A IMMUTABLE over the capability, region_B PRESERVATION over
        the temporal constraint. Strictest kind must win and both must be
        evidenced (no short-circuit)."""
        isr = self.parent_isr()
        return isr.with_system(
            dataclasses.replace(
                isr.system,
                protected_regions=(
                    ProtectedRegion(
                        region_id="region_A",
                        subject_refs=("capability_pay",),
                        protection_kind=ProtectionKind.IMMUTABLE,
                    ),
                    ProtectedRegion(
                        region_id="region_B",
                        subject_refs=("t1.deadline",),
                        protection_kind=ProtectionKind.PRESERVATION,
                        invariants=(
                            PreservationInvariant(
                                kind=ObligationKind.INVARIANT,
                                subject_refs=("t1.deadline",),
                                statement=(
                                    "the temporal constraint must hold unchanged"
                                ),
                            ),
                        ),
                    ),
                ),
                evolution_policies=(
                    EvolutionPolicy(
                        policy_id="policy1",
                        objective_refs=("opt1",),
                        protected_region_refs=("region_A", "region_B"),
                        selection_constraints=(
                            "no candidate may sacrifice the declared reliability",
                        ),
                    ),
                ),
            )
        )

    # -- deltas ----------------------------------------------------------------

    def _capability_edit(self, intent: str = "process a payment with dispute resolution") -> GeneEdit:
        capability = self.parent_isr().system.business_capabilities[0]
        return GeneEdit(
            "capability", "capability_pay",
            dataclasses.replace(capability, intent=intent),
        )

    def _reliability_edit(self, preservation: str | None = None) -> GeneEdit:
        """Evolve the reliability gene: recovery converges faster (a real
        semantic change). The coupled variant additionally leaks a mechanism
        term into the preservation invariant."""
        requirement = self.parent_isr().system.reliability_requirements[0]
        recovery = requirement.recovery_objectives[0]
        return GeneEdit(
            "reliability", "rr1",
            dataclasses.replace(
                requirement,
                recovery_objectives=(
                    dataclasses.replace(recovery, max_recovery_duration_ms=3000),
                ),
                preservation_invariants=(
                    (preservation,) if preservation is not None
                    else requirement.preservation_invariants
                ),
            ),
        )

    def _deployment_edit(self) -> GeneEdit:
        intent = self.parent_isr().system.deployment_intents[0]
        return GeneEdit(
            "deployment", "dep1",
            dataclasses.replace(intent, rollout_strategy=RolloutStrategy.BLUE_GREEN),
        )

    def _temporal_edit(self) -> GeneEdit:
        constraint = self.parent_isr().system.modules[0].temporal_constraints[0]
        return GeneEdit(
            "temporal", "t1.deadline",
            dataclasses.replace(constraint, duration_ms=350),
        )

    def four_gene_delta(self) -> MultiGeneDelta:
        return MultiGeneDelta(
            delta_id="four-gene",
            edits=(
                self._capability_edit(),
                self._reliability_edit(),
                self._deployment_edit(),
                self._temporal_edit(),
            ),
        )

    def dangling_delta(self) -> MultiGeneDelta:
        """The declared capability edit points its behavior_ref at a workflow
        that does not exist — the gate must reject it, not the constructor."""
        capability = self.parent_isr().system.business_capabilities[0]
        return MultiGeneDelta(
            delta_id="dangling",
            edits=(
                GeneEdit(
                    "capability", "capability_pay",
                    dataclasses.replace(
                        capability,
                        behavior_refs=("no_such_workflow",),
                    ),
                ),
                self._reliability_edit(),
                self._deployment_edit(),
                self._temporal_edit(),
            ),
        )

    def coupled_delta(self) -> MultiGeneDelta:
        """The declared reliability edit smuggles a mechanism term into an
        otherwise clean composition."""
        return MultiGeneDelta(
            delta_id="coupled",
            edits=(
                self._capability_edit(),
                self._reliability_edit(
                    preservation="pay coherent with retry_count 3"
                ),
                self._deployment_edit(),
                self._temporal_edit(),
            ),
        )

    # -- the evolution scenarios -----------------------------------------------

    def evolve(self, seed: int = 7):
        self.last_verdict = self.gate.evaluate(self.parent_isr(), self.four_gene_delta(), seed=seed)
        return self.last_verdict

    def evolve_with_hidden_side_effect(self, seed: int = 7):
        self.last_verdict = self.buggy_gate.evaluate(
            self.parent_isr(), self.four_gene_delta(), seed=seed
        )
        return self.last_verdict

    def evolve_to_dangling_reference(self):
        self.last_verdict = self.gate.evaluate(
            self.parent_isr(), self.dangling_delta(), seed=7
        )
        return self.last_verdict

    def evolve_with_coupled_gene(self):
        self.last_verdict = self.gate.evaluate(
            self.parent_isr(), self.coupled_delta(), seed=7
        )
        return self.last_verdict

    def evolve_multi_region(self):
        self.last_verdict = self.gate.evaluate(
            self.multi_region_isr(), self.four_gene_delta(), seed=7
        )
        return self.last_verdict

    def candidate_that_weakens_its_own_gate(self):
        """A candidate whose only 'advantage' would come from stripping its
        own evolution policy carriers. It must be judged under the PARENT's
        rules: the parent region region_A protects capability_pay, which the
        delta changes — infeasible, no matter what the candidate declares."""
        parent = self.multi_region_isr()
        candidate = self.gate._apply(parent, self.four_gene_delta(), seed=7)
        weakened = candidate.with_system(
            dataclasses.replace(
                candidate.system,
                evolution_objectives=(),
                protected_regions=(),
                evolution_policies=(),
            )
        )
        self.last_verdict = self.gate.evaluate_candidate(
            parent, weakened, self.four_gene_delta(), seed=7
        )
        return self.last_verdict

    def all_regions_evaluated(self) -> set[str]:
        return set(self.last_verdict.protection.regions_evaluated)

    def proof(self, verdict, proof_id):
        return next(p for p in verdict.proofs if p.proof_id == proof_id)


@pytest.fixture
def harness() -> SemanticEvolutionIntegrationHarness:
    return SemanticEvolutionIntegrationHarness()


# =============================================================================
# The positive composition — four independent genes across distinct domains
# =============================================================================

def test_multi_gene_evolution_preserves_unrelated_genes(harness):
    """Capability + reliability + deployment + temporal evolve together;
    every unrelated gene is byte-identical (one identity namespace)."""
    parent = harness.parent_isr()
    assert parent.validate_structure() is True
    verdict = harness.evolve(seed=7)
    candidate = apply_multi_gene_delta(parent, harness.four_gene_delta(), seed=7)
    assert verdict.feasible is True
    assert verdict.policy_resolved_from == "parent"
    assert verdict.protection.protected_ok is True
    before = harness.index.gene_hashes(parent)
    after = harness.index.gene_hashes(candidate)
    moved = {key for key in before if before[key] != after.get(key)}
    assert moved == set(harness.four_gene_delta().edited_genes)
    assert harness.proof(verdict, PROOF_LOCALITY).held is True
    assert harness.proof(verdict, PROOF_REFERENCE_INTEGRITY).held is True
    assert harness.proof(verdict, PROOF_BACKEND_INDEPENDENCE).held is True
    assert harness.proof(verdict, PROOF_R28_EVIDENCE_PATH).held is True


def test_disturbed_unrelated_gene_is_detected(harness):
    """The locality negative variant: an application layer that silently
    touches an unrelated gene must fail VISIBLY — the gate surfaces the
    disturbance, it does not swallow it."""
    verdict = harness.evolve_with_hidden_side_effect(seed=7)
    assert verdict.feasible is False
    locality = harness.proof(verdict, PROOF_LOCALITY)
    assert locality.held is False
    assert "disturbed" in locality.evidence
    assert "w1" in locality.evidence


def test_cross_gene_references_hold(harness):
    """The evolved candidate's cross-gene references all still resolve
    through the identity index (parent and candidate both clean)."""
    parent = harness.parent_isr()
    assert harness.index.dangling_references(parent) == ()
    verdict = harness.evolve(seed=7)
    candidate = apply_multi_gene_delta(parent, harness.four_gene_delta(), seed=7)
    assert harness.index.dangling_references(candidate) == ()
    assert harness.proof(verdict, PROOF_REFERENCE_INTEGRITY).held is True


def test_dangling_cross_reference_rejected(harness):
    """The reference-integrity negative variant: a delta that dangles is
    rejected BY THE GATE — feasibility passed (region_1 is untouched), so
    the proof path must surface the broken reference."""
    verdict = harness.evolve_to_dangling_reference()
    assert verdict.protection.protected_ok is True
    assert verdict.feasible is False
    proof = harness.proof(verdict, PROOF_REFERENCE_INTEGRITY)
    assert proof.held is False
    assert "no_such_workflow" in proof.evidence


def test_projection_remains_backend_independent(harness):
    """All ten primitives' mechanism lints aggregate on the composed
    candidate — the semantic projection carries no implementation."""
    verdict = harness.evolve(seed=7)
    proof = harness.proof(verdict, PROOF_BACKEND_INDEPENDENCE)
    assert proof.held is True
    assert "10 primitives" in proof.evidence


def test_technology_coupling_rejected_in_composition(harness):
    """The backend-independence negative variant: one coupled gene among
    otherwise-clean genes fails the whole composition, naming the leak."""
    verdict = harness.evolve_with_coupled_gene()
    assert verdict.feasible is False
    proof = harness.proof(verdict, PROOF_BACKEND_INDEPENDENCE)
    assert proof.held is False
    assert "retry_count" in proof.evidence
    assert all(term in RELIABILITY_MECHANISM_TERMS for term in ("retry_count",))


def test_multi_gene_evolution_reproducible_and_ledger_verifiable(harness):
    """Same parent + delta + seed -> same candidate hash and identical
    chain-anchored MEASUREMENT events with the canonical edit list."""
    parent = harness.parent_isr()
    v1 = harness.gate.evaluate(parent, harness.four_gene_delta(), seed=7)
    v2 = harness.gate.evaluate(parent, harness.four_gene_delta(), seed=7)
    assert v1.candidate_semantic_hash == v2.candidate_semantic_hash
    assert harness.ledger.verify_event_chain() is True
    events = harness.ledger.events()
    assert len(events) == 2
    assert all(e.event_type is EventType.MEASUREMENT for e in events)
    assert all(e.is_intact() for e in events)
    # Chain anchoring makes the two event hashes differ (each event links to
    # its predecessor); the reproducibility is in the CONTENT: same payload,
    # same bound hashes, each verdict's range covering exactly its event.
    assert events[0].payload == events[1].payload
    assert events[0].isr_hash == events[1].isr_hash == stable_isr_hash(parent)
    assert events[0].candidate_hash == events[1].candidate_hash
    assert v1.ledger_event_range == (events[0].event_hash, events[0].event_hash)
    assert v2.ledger_event_range == (events[1].event_hash, events[1].event_hash)
    assert events[1].parent_event_id == events[0].event_hash
    assert events[0].payload["edits"] == [
        {"domain": "capability", "gene_id": "capability_pay"},
        {"domain": "deployment", "gene_id": "dep1"},
        {"domain": "reliability", "gene_id": "rr1"},
        {"domain": "temporal", "gene_id": "t1.deadline"},
    ]
    assert all(p["held"] for p in events[0].payload["proofs"])
    assert events[0].candidate_hash == v1.candidate_semantic_hash


def test_option_a_holds_under_composition(harness):
    """R2.10.4 adds no carriers and moves no matrix row: the recipe ISR is
    byte-identical (the eleventh Option A use) and the matrix stays
    12/18/0/0."""
    assert RECIPE.content_hash == (
        "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
    )
    result = ISRCapabilityAudit().run(RECIPE)
    assert result.integrity is True
    assert result.isr_hash == RECIPE.content_hash
    summary = result.summary()
    assert (summary["expressed"], summary["partial"], summary["missing"]) == (
        12, 18, 0,
    )
    by_id = {c.capability_id: c.status for c in result.capabilities}
    expressed = {cid for cid, s in by_id.items() if s is CapabilityStatus.EXPRESSED}
    missing = {cid for cid, s in by_id.items() if s is CapabilityStatus.MISSING}
    assert expressed == {
        "behavior_transitions", "behavior_await_surface",
        "behavior_temporal_semantics", "business_capabilities",
        "data_migrations", "reliability_resilience",
        "architecture_boundaries", "requirements_acceptance_traceability",
        "deployment_rollout_rollback", "testing_anchoring",
        "documentation", "evolution_objectives_protected_regions",
    }
    assert missing == set()
    assert CapabilityStatus.PROJECTED not in by_id.values()


# =============================================================================
# Parent authority — a candidate is judged by the rules it was generated under
# =============================================================================

def test_policy_always_resolved_from_parent():
    """AST proof: the gate source resolves the policy from the parent
    constitution only — never from the candidate."""
    source = pathlib.Path(inspect.getfile(SemanticEvolutionGate)).read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    calls = [
        ast.unparse(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "resolve_evolution_policy"
    ]
    assert any("resolve_evolution_policy(parent_isr)" in call for call in calls)
    assert not any("candidate" in call for call in calls)


def test_candidate_cannot_weaken_its_own_gate(harness):
    """Behavioral proof: a candidate that strips its own evolution policy
    carriers is still judged under the PARENT's regions — region_A protects
    the capability the delta changes, so the weakening gains nothing."""
    verdict = harness.candidate_that_weakens_its_own_gate()
    assert verdict.feasible is False
    assert verdict.policy_resolved_from == "parent"
    assert verdict.protection.protected_ok is False
    assert verdict.protection.kind is ProtectionKind.IMMUTABLE
    assert any("region 'region_A' is IMMUTABLE" in n for n in verdict.protection.notes)
    assert verdict.proofs == ()


# =============================================================================
# Multi-region protection — strictest kind wins, no region short-circuits
# =============================================================================

def test_multi_region_protection_strictest_wins(harness):
    """One delta puts two regions in play (capability + temporal). Both are
    evaluated; the strictest kind (IMMUTABLE) wins; both violations are
    evidenced; feasibility fails before any proof or ledger event."""
    verdict = harness.evolve_multi_region()
    assert verdict.feasible is False
    assert verdict.protection.protected_ok is False
    assert verdict.protection.kind is ProtectionKind.IMMUTABLE
    assert verdict.protection.affected_subjects == ("capability_pay", "t1.deadline")
    assert harness.all_regions_evaluated() == {"region_A", "region_B"}
    notes = " | ".join(verdict.protection.notes)
    assert "region 'region_A' is IMMUTABLE" in notes
    assert "the temporal constraint must hold unchanged" in notes
    assert verdict.proofs == ()
    assert verdict.ledger_event_range is None
    assert harness.ledger.events() == []


def test_feasibility_precedes_objectives_under_multi_gene(harness):
    """Feasibility is the FIRST gate: an infeasible candidate returns with
    no proofs and no ledger event (protection failure), while a feasible
    candidate that fails a proof still shows protection passed — the two
    failure paths are distinct and the source order enforces it."""
    infeasible = harness.evolve_multi_region()
    assert infeasible.protection.protected_ok is False
    assert infeasible.proofs == ()
    assert infeasible.ledger_event_range is None
    proof_failure = harness.evolve_to_dangling_reference()
    assert proof_failure.protection.protected_ok is True
    assert proof_failure.proofs != ()
    assert proof_failure.ledger_event_range is None
    source = pathlib.Path(inspect.getfile(SemanticEvolutionGate)).read_text(
        encoding="utf-8"
    )
    assert (
        source.index("if not protection.protected_ok:")
        < source.index("self._prove_locality")
    )


# =============================================================================
# The R2.8 evidence substrate — the gate holds no evaluator of its own
# =============================================================================

def test_gate_holds_no_evaluation_machinery():
    """The protection projection is consumed by the R2.8 gate stack; neither
    the gate nor the protection module may contain evaluation identifiers
    (fitness / score / metric / measurement) structurally."""
    assert is_projection_consumed_by_r28() is True


def test_merged_policy_resolution_is_deterministic(harness):
    """Multiple policies merge into one deterministic governing policy —
    still resolved from the parent side only."""
    parent = harness.parent_isr()
    doubled = parent.with_system(
        dataclasses.replace(
            parent.system,
            evolution_policies=(
                parent.system.evolution_policies[0],
                EvolutionPolicy(
                    policy_id="policy2",
                    objective_refs=("opt1",),
                    protected_region_refs=(),
                ),
            ),
        )
    )
    merged = resolve_evolution_policy(doubled)
    assert merged.policy_id == "merged"
    assert merged.objective_refs == ("opt1",)
    assert merged.protected_region_refs == ("region_1",)
    again = resolve_evolution_policy(doubled)
    assert merged == again
    no_policy = resolve_evolution_policy(parent.with_system(
        dataclasses.replace(parent.system, evolution_policies=())
    ))
    assert no_policy.policy_id == "parent"
    assert no_policy.objective_refs == ()
    assert no_policy.protected_region_refs == ()