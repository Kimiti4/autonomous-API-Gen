"""R2.6 -- competitive evolution (Pareto selection over a candidate ensemble).

Proves the Evolution Engine searches a frontier rather than patching once. The
engine must (a) select the correct repair, (b) generate and reject the null
candidate at target_failure, (c) record every candidate's verdict. Skipped when
Docker is absent.
"""
from __future__ import annotations

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

from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend
from tiannara.application.evolution import (
    BrokenTreeIntactInvariant,
    CandidateGate,
    CompetitiveEvolutionCoordinator,
    DeterministicComplexityPreference,
    EvolutionLedger,
    RealBackendSandbox,
    TransitionRestoration,
    TransitionRestorationOperator,
    NullMutation,
    docker_available,
    hash_artifact,
)
from tiannara.application.evolution.candidate_gate import CandidateVerdict
from tiannara.application.evolution.competitive_evolution import (
    ScoredCandidate,
    pareto_frontier,
)
from tiannara.application.evolution.fitness import FitnessVector
from tiannara.application.evolution.mutation_operators import (
    EMPTY_DELTA,
    MutationCandidate,
)

COROUTINE = "process_payment"


def _workflow(resolving: bool) -> Workflow:
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
                from_state_id=awaited.id, to_state_id=final.id, trigger=COROUTINE,
            ),
        )
    return Workflow(id="order", name="order", states=(awaited, final), transitions=transitions)


def _isr(resolving: bool) -> ISR:
    return ISR(system=System(
        id="sys", name="OrderSystem",
        modules=(Module(id="m", name="M", workflows=(_workflow(resolving),)),),
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


def _fitness(**kw) -> FitnessVector:
    base = {
        "correctness": 0.0, "regression_safety": 0.0,
        "structural_validity": 0.0, "causal_validity": 0.0,
        "invariant_compliance": 0.0, "complexity_efficiency": 0.0,
    }
    base.update(kw)
    return FitnessVector.from_dict(base)


def _scored(cid: str, feasible: bool, fitness: FitnessVector) -> ScoredCandidate:
    isr = ISR(system=System(id="s", name="S", modules=()))
    cand = MutationCandidate(
        candidate_id=cid, operator_id="test", candidate_isr=isr,
        parent_isr=isr, mutation_delta=EMPTY_DELTA, hypothesis="t",
    )
    verdict = CandidateVerdict(accept=feasible, gate_results=(),
                               candidate_hash="", parent_hash="")
    return ScoredCandidate(cand, verdict, fitness, feasible)


@pytest.mark.skipif(not docker_available(), reason="R2.6 gate requires Docker")
def test_r26_competitive_evolution_chooses_correct_repair(tmp_path):
    known_good_isr = _isr(resolving=True)
    broken_isr = _drop_resolution_edge(known_good_isr)
    sandbox = RealBackendSandbox(backend=FastAPIHexagonalBackend())
    operator = TransitionRestoration()

    broken_candidate = sandbox.build(broken_isr, workspace=str(tmp_path / "broken"))
    broken_hash_before = broken_candidate.artifact_hash
    assert broken_candidate.artifact_hash == hash_artifact(broken_candidate.source_root)
    broken_run = sandbox.run_tests(broken_candidate)
    observation = sandbox.classifier.classify(sandbox.to_evidence(broken_run))
    assert observation is not None, f"expected a failure, got clean run: {broken_run}"
    assert operator.extract_coroutine_name(observation) == COROUTINE

    known_good_candidate = sandbox.build(known_good_isr, workspace=str(tmp_path / "kg"))
    known_good_run = sandbox.run_tests(known_good_candidate)
    assert known_good_run.exit_code == 0

    ensemble = (TransitionRestorationOperator(operator), NullMutation())
    gate = CandidateGate.default()
    ledger = EvolutionLedger()

    decision = CompetitiveEvolutionCoordinator(
        sandbox=sandbox, gate=gate, operators=ensemble,
        selection=DeterministicComplexityPreference(), ledger=ledger,
    ).run(
        broken_isr=broken_isr,
        broken_artifact=broken_candidate,
        broken_run=broken_run,
        baseline_isr=known_good_isr,
        baseline_artifact=known_good_candidate,
        baseline_run=known_good_run,
        observation=observation,
        protected_invariants=(BrokenTreeIntactInvariant(broken_hash_before),),
    )

    repair = next(s for s in decision.candidates if s.candidate.operator_id == "transition_restoration")
    null = next(s for s in decision.candidates if s.candidate.operator_id == "null_mutation")

    # (a) the engine selected the genuine repair
    assert decision.selected_candidate_id == repair.candidate.candidate_id
    assert repair.feasible
    # (b) null candidate generated, then rejected at target_failure
    assert null.candidate.operator_id == "null_mutation"
    assert not null.feasible
    assert not any(r.gate_id == "target_failure" and r.passed for r in null.verdict.gate_results)
    # (c) Pareto frontier is the single feasible repair (thin frontier expected)
    assert decision.pareto_frontier_ids == (repair.candidate.candidate_id,)
    # (d) every candidate recorded (auditable reasoning)
    assert len(decision.candidates) == 2
    assert ledger.latest_selection_id
    sel = ledger.get_selection(ledger.latest_selection_id)
    assert sel is not None
    payload = sel.payload
    assert {c["candidate_id"] for c in payload["candidates"]} == {
        repair.candidate.candidate_id, null.candidate.candidate_id
    }
    assert payload["selected_candidate_id"] == repair.candidate.candidate_id
    payload_by_id = {c["candidate_id"]: c for c in payload["candidates"]}
    null_payload = payload_by_id[null.candidate.candidate_id]
    assert not any(g["gate"] == "target_failure" and g["passed"] for g in null_payload["gate_results"])
    assert ledger.verify_selection_chain()


def test_r26_pareto_frontier_and_selection_machinery():
    a = _scored("a", feasible=True, fitness=_fitness(correctness=1.0, complexity_efficiency=0.5))
    b = _scored("b", feasible=False, fitness=_fitness(correctness=0.5, complexity_efficiency=0.9))
    frontier = pareto_frontier([a, b])
    assert [c.candidate.candidate_id for c in frontier] == ["a"]
    c = _scored("c", feasible=True, fitness=_fitness(correctness=1.0, complexity_efficiency=0.9))
    frontier2 = pareto_frontier([a, c])
    assert set(x.candidate.candidate_id for x in frontier2) == {"a", "c"}
    strat = DeterministicComplexityPreference()
    chosen = strat.select(frontier2)
    assert chosen is not None
    assert chosen.candidate.candidate_id == "c"
    assert strat.select(frontier2).candidate.candidate_id == "c"
