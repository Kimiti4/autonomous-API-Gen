"""R2.9.2 -- autonomous constructive variation.

Proves the variation engine is a *hypothesis generator* that never judges:
deterministic identity under (ISR, observation, seed), mutation-only surface
(ISR deltas with verified closure), bounded seed-replayable exploration,
deceptive candidates (``TestDeletionMutation``) rejected at the identity
layer (``AwaitingSurfaceIntactInvariant``), and the full autonomous repair
round scoring every candidate through the shared R2.8 boundary and recording
the decision on the causal ledger. The end-to-end repair test is skipped when
Docker is absent; everything else is hermetic.
"""
from __future__ import annotations

import json

import pytest

from constitutional_architecture.isr.model import (
    ISR,
    Module,
    StateType,
    System,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)

from tiannara.application.evolution import (
    ActionInjectionOperator,
    AwaitingSurfaceIntactInvariant,
    AutonomousRepairCoordinator,
    BrokenTreeIntactInvariant,
    CandidateGate,
    DeterministicComplexityPreference,
    EvolutionLedger,
    FSMRepairVariation,
    GuardRelaxationOperator,
    NullCrossover,
    RandomFSMExploration,
    RealBackendSandbox,
    TestDeletionMutation,
    TransitionRestoration,
    TransitionRestorationOperator,
    NullMutation,
    docker_available,
)
from tiannara.application.evolution.candidate_gate import GateContext
from tiannara.application.evolution.candidate_sandbox import CompiledCandidate
from tiannara.application.evolution.fitness import FitnessVector
from tiannara.application.evolution.transition_restoration import apply_restoration
from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend
from tiannara.domain.models.evidence import TestRunResult
from tiannara.domain.models.observation import (
    FailureCategory,
    FailureObservation,
    FailurePhase,
)

COROUTINE = "process_payment"


def _workflow(resolving: bool, guard: str = "") -> Workflow:
    awaited = WorkflowState(
        id="order-await", name="awaiting",
        state_type=StateType.INTERMEDIATE, metadata={"awaits": COROUTINE},
    )
    final = WorkflowState(id="order-final", name="final", state_type=StateType.FINAL)
    transitions = ()
    if resolving:
        transitions = (
            WorkflowTransition(
                id="resolve-payment", name="resolve payment",
                from_state_id=awaited.id, to_state_id=final.id,
                trigger=COROUTINE, guard_condition=guard,
            ),
        )
    return Workflow(id="order", name="order", states=(awaited, final), transitions=transitions)


def _isr(resolving: bool, guard: str = "") -> ISR:
    return ISR(system=System(
        id="sys", name="OrderSystem",
        modules=(Module(id="m", name="M", workflows=(_workflow(resolving, guard),)),),
    ))


def _drop_resolution_edge(isr: ISR) -> ISR:
    module = isr.system.modules[0]
    wf = module.workflows[0]
    broken_wf = Workflow(
        id=wf.id, name=wf.name, description=wf.description,
        states=wf.states, transitions=(), metadata=wf.metadata,
    )
    broken_module = Module(
        id=module.id, name=module.name, description=module.description,
        entities=module.entities, services=module.services, workflows=(broken_wf,),
        policies=module.policies, interfaces=module.interfaces, events=module.events,
        dependencies=module.dependencies, metadata=module.metadata,
    )
    return isr.with_system(System(
        id=isr.system.id, name=isr.system.name, description=isr.system.description,
        modules=(broken_module,), deployment=isr.system.deployment,
        metadata=isr.system.metadata, global_policies=isr.system.global_policies,
        constraints=isr.system.constraints,
    ))


def _observation(coro: str = COROUTINE) -> FailureObservation:
    diagnostic = f"coroutine '{coro}' was never awaited"
    return FailureObservation(
        execution_id="exec-1", backend_id="test", phase=FailurePhase.TEST,
        category=FailureCategory.TEST_FAILURE, exit_code=1,
        command=["pytest", "-W", "error::RuntimeWarning", "-q"],
        diagnostics=(diagnostic,),
        evidence_hash="obs-hash",
        stderr_excerpt=f"RuntimeWarning: {diagnostic}",
    )


def _ctx(parent: ISR, candidate: ISR) -> GateContext:
    return GateContext(
        candidate_isr=candidate,
        candidate_artifact=CompiledCandidate(source_root="", compile_ok=True),
        candidate_run=TestRunResult(passed=True, exit_code=0),
        baseline_artifact=CompiledCandidate(source_root="", compile_ok=True),
        baseline_run=TestRunResult(passed=True, exit_code=0),
        observation=_observation(),
        mutation=NullMutation().propose(parent, _observation()),
        parent_isr=parent,
        broken_artifact=CompiledCandidate(source_root="", compile_ok=True),
    )


# -- hermetic: variation semantics -------------------------------------------

def test_null_crossover_identity():
    a = _isr(resolving=True)
    b = _isr(resolving=False)
    children = NullCrossover().crossover(a, b, seed=0)
    assert [c.content_hash for c in children] == [a.content_hash, b.content_hash]


def test_variation_deterministic_identity_and_replay():
    broken = _drop_resolution_edge(_isr(resolving=True))
    observation = _observation()
    variation = FSMRepairVariation()

    p1 = variation.generate(broken, observation, population_size=8, seed=0)
    p2 = variation.generate(broken, observation, population_size=8, seed=0)
    assert [c.candidate_id for c in p1] == [c.candidate_id for c in p2]
    assert p1  # restoration + null at minimum

    p_seeded = variation.generate(broken, observation, population_size=8, seed=42)
    p_replay = variation.generate(broken, observation, population_size=8, seed=42)
    assert [c.candidate_id for c in p_seeded] == [c.candidate_id for c in p_replay]

    # candidate_id is a function of the candidate ISR (de-dup + replay identity)
    from tiannara.application.evolution.ledger import stable_isr_hash
    for candidate in p1:
        assert candidate.candidate_id.endswith(stable_isr_hash(candidate.candidate_isr)[:12])


def test_variation_population_size_bounded():
    broken = _drop_resolution_edge(_isr(resolving=True))
    variation = FSMRepairVariation()
    for size in (1, 3, 8):
        population = variation.generate(broken, _observation(), population_size=size, seed=0)
        assert len(population) <= size
        assert len({c.candidate_id for c in population}) == len(population)  # no dups


def test_mutation_only_surface_and_closure():
    """Every candidate is an ISR delta (never a source patch): entries parse as
    R2.3 descriptors carrying the causal-required keys, and applying them to the
    parent reproduces the candidate ISR exactly (closure, as the CausalGate
    verifies it)."""
    from tiannara.application.evolution.ledger import stable_isr_hash

    broken = _drop_resolution_edge(_isr(resolving=True))
    variation = FSMRepairVariation()
    population = variation.generate(broken, _observation(), population_size=8, seed=0)
    assert population
    for candidate in population:
        if candidate.mutation_delta.size == 0:
            # NullMutation identity: an empty delta is a valid ISR delta
            assert candidate.operator_id == "null_mutation"
            continue
        for entry in candidate.mutation_delta.entries:
            desc = json.loads(entry)
            for key in ("workflow_id", "from_state_id", "to_state_id", "trigger"):
                assert key in desc, f"{candidate.operator_id} delta missing {key}"
        assert stable_isr_hash(apply_restoration(
            candidate.parent_isr, candidate.mutation_delta.entries
        )) == stable_isr_hash(candidate.candidate_isr)


def test_guard_relaxation_operator_targeted_and_declines():
    guarded = _isr(resolving=True, guard="blocked")
    proposed = GuardRelaxationOperator().propose(guarded, _observation())
    assert proposed is not None
    assert proposed.operator_id == "guard_relaxation"
    for module in proposed.candidate_isr.system.modules:
        for wf in module.workflows:
            for t in wf.transitions:
                if t.trigger == COROUTINE:
                    assert t.guard_condition == ""
    # deterministic replay
    again = GuardRelaxationOperator().propose(guarded, _observation())
    assert again.candidate_id == proposed.candidate_id
    # declines when no guarded transition exists (the dropped-edge defect)
    broken = _drop_resolution_edge(_isr(resolving=True))
    assert GuardRelaxationOperator().propose(broken, _observation()) is None


def test_action_injection_operator_targeted_and_declines():
    resolving = _isr(resolving=True)
    proposed = ActionInjectionOperator().propose(resolving, _observation())
    assert proposed is not None
    assert proposed.operator_id == "action_injection"
    for module in proposed.candidate_isr.system.modules:
        for wf in module.workflows:
            for t in wf.transitions:
                if t.trigger == COROUTINE:
                    assert "notify-resolution" in t.actions
    again = ActionInjectionOperator().propose(resolving, _observation())
    assert again.candidate_id == proposed.candidate_id
    # declines when the resolving transition is absent
    broken = _drop_resolution_edge(_isr(resolving=True))
    assert ActionInjectionOperator().propose(broken, _observation()) is None


def test_exploration_bounded_deterministic_and_never_fabricates_repair():
    broken = _drop_resolution_edge(_isr(resolving=True))
    observation = _observation()
    exploration = RandomFSMExploration()
    p1 = exploration.generate(broken, observation, population_size=8, seed=3)
    p2 = exploration.generate(broken, observation, population_size=8, seed=3)
    assert [c.candidate_id for c in p1] == [c.candidate_id for c in p2]
    assert len(p1) <= 4  # max_candidates bound
    for candidate in p1:
        # exploration never proposes the exact repair edge (targeted job)
        desc = json.loads(candidate.mutation_delta.entries[0])
        assert desc["op"] == "explore"
        assert desc["trigger"] != COROUTINE


def test_deceptive_candidate_rejected_by_identity_invariant():
    broken = _drop_resolution_edge(_isr(resolving=True))
    deceptive = TestDeletionMutation().propose(broken, _observation())
    assert deceptive is not None
    desc = json.loads(deceptive.mutation_delta.entries[0])
    assert desc["op"] == "strip_awaits"

    invariant = AwaitingSurfaceIntactInvariant()
    assert invariant.holds(_ctx(parent=broken, candidate=deceptive.candidate_isr)) is False

    # the genuine repair preserves the awaiting surface
    repair = TransitionRestorationOperator().propose(broken, _observation())
    assert invariant.holds(_ctx(parent=broken, candidate=repair.candidate_isr)) is True


def test_deceptive_control_absent_from_default_ensemble():
    broken = _drop_resolution_edge(_isr(resolving=True))
    population = FSMRepairVariation().generate(broken, _observation(), population_size=8, seed=0)
    assert all(c.operator_id != "test_deletion" for c in population)


# -- end-to-end (Docker-gated): autonomous repair round ----------------------

@pytest.mark.skipif(not docker_available(), reason="R2.9.2 gate requires Docker")
def test_r29_2_autonomous_variation_repairs_defect_and_records(tmp_path):
    known_good_isr = _isr(resolving=True)
    broken_isr = _drop_resolution_edge(known_good_isr)
    sandbox = RealBackendSandbox(backend=FastAPIHexagonalBackend())

    broken_candidate = sandbox.build(broken_isr, workspace=str(tmp_path / "broken"))
    broken_hash_before = broken_candidate.artifact_hash
    broken_run = sandbox.run_tests(broken_candidate)
    observation = sandbox.classifier.classify(sandbox.to_evidence(broken_run))
    assert observation is not None, f"expected a failure, got clean run: {broken_run}"

    known_good_candidate = sandbox.build(known_good_isr, workspace=str(tmp_path / "kg"))
    known_good_run = sandbox.run_tests(known_good_candidate)
    assert known_good_run.exit_code == 0

    ensemble = FSMRepairVariation(targeted_operators=(
        TransitionRestorationOperator(TransitionRestoration()),
        NullMutation(),
        TestDeletionMutation(),
        GuardRelaxationOperator(),
        ActionInjectionOperator(),
    ))
    ledger = EvolutionLedger()
    result = AutonomousRepairCoordinator(
        sandbox=sandbox,
        gate=CandidateGate.default(),
        variation=ensemble,
        selection=DeterministicComplexityPreference(),
        crossover=NullCrossover(),
        ledger=ledger,
    ).run(
        defective_isr=broken_isr,
        broken_artifact=broken_candidate,
        broken_run=broken_run,
        baseline_isr=known_good_isr,
        baseline_artifact=known_good_candidate,
        baseline_run=known_good_run,
        observation=observation,
        population_size=8,
        seed=0,
        protected_invariants=(
            BrokenTreeIntactInvariant(broken_hash_before),
            AwaitingSurfaceIntactInvariant(),
        ),
    )

    by_id = {s.candidate.candidate_id: s for s in result.population}
    repair = next(s for s in result.population if s.candidate.operator_id == "transition_restoration")
    deceptive = next(s for s in result.population if s.candidate.operator_id == "test_deletion")
    null = next(s for s in result.population if s.candidate.operator_id == "null_mutation")

    # (a) the engine selected the genuine repair through the shared boundary
    assert result.selected_candidate_id == repair.candidate.candidate_id
    assert repair.feasible
    # (b) recompilation reproduces the artifact (CausalGate fresh-recompile)
    causal = next(r for r in repair.verdict.gate_results if r.gate_id == "causal")
    assert causal.passed and causal.evidence["fresh_recompile_matches"] is True
    # (c) null candidate generated, then rejected at target_failure
    assert not null.feasible
    assert not any(r.gate_id == "target_failure" and r.passed for r in null.verdict.gate_results)
    # (d) deceptive candidate rejected at the identity layer (never accepted)
    assert not deceptive.feasible
    invariant = next(r for r in deceptive.verdict.gate_results if r.gate_id == "invariant")
    assert not invariant.passed
    assert "awaiting_surface_intact" in invariant.evidence["violations"]
    # (e) multi-objective fitness only -- no scalar ConstructiveObjective
    for scored in result.population:
        assert isinstance(scored.fitness, FitnessVector)
        assert scored.fitness.get("correctness") in (0.0, 1.0)
    # (f) every candidate evaluated and the decision recorded on the causal ledger
    assert set(by_id) == {s.candidate.candidate_id for s in result.population}
    assert len(result.population) == len(by_id)
    assert ledger.latest_selection_id
    payload = ledger.get_selection(ledger.latest_selection_id).payload
    assert payload["selected_candidate_id"] == repair.candidate.candidate_id
    assert {c["candidate_id"] for c in payload["candidates"]} == set(by_id)
    assert ledger.verify_selection_chain()
    # (g) seed replayability: generation is a pure function of (ISR, observation,
    # seed) -- proven hermetically above. Decision determinism here is a pure
    # function of the population and the run outcomes; a second full round is
    # deliberately NOT re-run inside this Docker-gated test (it doubles the
    # container load and only re-measures Docker stability, not the engine).
    replay_population = ensemble.generate(broken_isr, observation, 8, 0)
    assert [c.candidate_id for c in replay_population] == [s.candidate.candidate_id for s in result.population]