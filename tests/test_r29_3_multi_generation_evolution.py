"""R2.9.3 -- Multi-generation evolution.

Proves evolution over time: deterministic generation identity and lineage,
fresh evaluation per generation (no stale evidence), Pareto selection with
deterministic tie-break, convergence (including a genuine two-generation
convergence via generation-gated repair availability), observe-only diversity
(the monoculture diagnostic), the full per-generation ledger event chain,
replay determinism, all termination modes, and the constitutional rule that
evolutionary bookkeeping never contaminates the ISR.

The end-to-end Docker test proves the standard FSM defect converges through
the real R2.8 boundary; everything else runs hermetically against a faithful
stub sandbox that models the FSM substrate exactly (await-marker codegen,
exit-code/test outcomes derived from the ISR's resolving transitions).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

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
    CandidateGate,
    DeterministicComplexityPreference,
    DiversityObserver,
    EvolutionLedger,
    FSMRepairVariation,
    MultiGenerationEvolutionCoordinator,
    NullMutation,
    RandomFSMExploration,
    TerminationReason,
    TransitionRestorationOperator,
    docker_available,
    derive_generation_id,
    stable_isr_hash,
)
from tiannara.application.evolution.candidate_sandbox import CompiledCandidate
from tiannara.application.evolution.compiler_sandbox import hash_artifact
from tiannara.application.evolution.mutation_operators import MutationCandidate, MutationOperator
from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend
from tiannara.domain.models.evidence import TestRunResult
from tiannara.domain.models.observation import (
    FailureCategory,
    FailureObservation,
    FailurePhase,
)

COROUTINE = "process_payment"


# -- ISR fixtures -------------------------------------------------------------

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


def _observation(coro: str = COROUTINE) -> FailureObservation:
    diagnostic = f"coroutine '{coro}' was never awaited"
    return FailureObservation(
        execution_id="exec-1", backend_id="stub", phase=FailurePhase.TEST,
        category=FailureCategory.TEST_FAILURE, exit_code=1,
        command=["pytest", "-W", "error::RuntimeWarning", "-q"],
        diagnostics=(diagnostic,),
        evidence_hash="obs-hash",
        stderr_excerpt=f"RuntimeWarning: {diagnostic}",
    )


def _has_resolution(isr: ISR, coroutine: str = COROUTINE) -> bool:
    """Faithful substrate predicate: a state awaiting ``coroutine`` is resolved
    iff a transition with that trigger exists in the same workflow."""
    for module in isr.system.modules:
        for wf in module.workflows:
            awaiting = [s for s in wf.states if s.metadata.get("awaits") == coroutine]
            if awaiting and not any(t.trigger == coroutine for t in wf.transitions):
                return False
    return True


class FsmStubSandbox:
    """Faithful hermetic model of the FSM substrate (no Docker).

    ``build`` writes the await-marker codegen (exactly what the real backend's
    ``async_resolution_module`` emits) and hashes it deterministically; the
    fresh-recompile binding of the CausalGate therefore holds. ``run_tests``
    derives exit code / pass count from the artifact's markers, mirroring the
    real ``-W error::RuntimeWarning`` behavior: unresolved awaits fail.
    """

    def __init__(self, coroutine: str = COROUTINE):
        self._coroutine = coroutine
        self._artifact_isr: dict[str, ISR] = {}
        self.build_count = 0
        self.run_count = 0

    def build(self, isr: ISR, workspace: str | None = None) -> CompiledCandidate:
        self.build_count += 1
        root = Path(workspace) if workspace else Path(tempfile.mkdtemp(prefix="stub-"))
        (root / "generated.py").write_text(self._codegen(isr), encoding="utf-8")
        artifact = CompiledCandidate(
            source_root=str(root),
            compile_ok=True,
            artifact_hash=hash_artifact(root),
        )
        self._artifact_isr[artifact.artifact_hash] = isr
        return artifact

    def run_tests(self, artifact: CompiledCandidate) -> TestRunResult:
        self.run_count += 1
        isr = self._artifact_isr.get(artifact.artifact_hash)
        repaired = isr is not None and _has_resolution(isr, self._coroutine)
        return TestRunResult(
            passed=repaired,
            exit_code=0 if repaired else 1,
            total_tests=1,
            failed_tests=0 if repaired else 1,
            pass_count=1 if repaired else 0,
            duration_seconds=1.0,
        )

    def _codegen(self, isr: ISR) -> str:
        lines = []
        for module in isr.system.modules:
            for wf in module.workflows:
                for state in wf.states:
                    coroutine = state.metadata.get("awaits")
                    if not coroutine:
                        continue
                    if any(t.trigger == coroutine for t in wf.transitions):
                        lines.append(f"    await {coroutine}()")
                    else:
                        lines.append(f"    {coroutine}()  # fire-and-forget")
        if not lines:
            return ""
        return "\n".join(lines) + "\n"


# -- harness ------------------------------------------------------------------

def _build_harness(variation, sandbox: FsmStubSandbox, ledger=None,
                   stagnation_window: int = 3):
    known_good = _isr(resolving=True)
    defective = _drop_resolution_edge(known_good)
    observation = _observation()

    baseline_artifact = sandbox.build(known_good)
    baseline_run = sandbox.run_tests(baseline_artifact)
    broken_artifact = sandbox.build(defective)
    broken_run = sandbox.run_tests(broken_artifact)
    assert not broken_run.passed

    coordinator = MultiGenerationEvolutionCoordinator(
        sandbox=sandbox,
        gate=CandidateGate.default(),
        variation=variation,
        selection=DeterministicComplexityPreference(),
        ledger=ledger,
        diversity_observer=DiversityObserver(),
        stagnation_window=stagnation_window,
    )
    return coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run


# -- purpose-built variations -------------------------------------------------

class GatedRepairVariation:
    """Withholds the targeted repair until generation >= restore_from_generation.

    The coordinator calls ``generate(current_isr, observation, population_size,
    seed + index)``, so the generation index is observable through the seed
    argument (harness runs use seed=0). Generations below the gate propose only
    causally-inert exploration hypotheses -- the search must survive them via
    elite advancement, then converge once the repair is available.
    """

    def __init__(self, restore_from_generation: int = 1):
        self._gate = restore_from_generation

    def generate(self, defective_isr, observation, population_size, seed):
        generation = seed  # seed == run_seed(0) + index
        operators: list[MutationOperator] = []
        if generation >= self._gate:
            operators = [TransitionRestorationOperator(), NullMutation()]
        exploration = RandomFSMExploration()
        seen = {}
        for op in operators:
            proposed = op.propose(defective_isr, observation)
            if proposed is not None:
                seen.setdefault(proposed.candidate_id, proposed)
        for candidate in exploration.generate(
            defective_isr, observation, population_size, seed
        ):
            seen.setdefault(candidate.candidate_id, candidate)
        return tuple(sorted(seen.values(), key=lambda c: c.candidate_id))[:population_size]


class MonocultureVariation:
    """Proposes the same restoration candidate N times (pre-dedup duplicate
    population) -- the entropy-0 / high-duplicate-rate diagnostic."""

    def __init__(self, copies: int = 6):
        self._copies = copies

    def generate(self, defective_isr, observation, population_size, seed):
        candidate = TransitionRestorationOperator().propose(defective_isr, observation)
        if candidate is None:
            return ()
        return (candidate,) * self._copies


class IdentityVariation:
    """Proposes only candidates identical to the current parent (restraint) --
    the elite equals the parent, so no progress is possible."""

    def generate(self, defective_isr, observation, population_size, seed):
        null = NullMutation().propose(defective_isr, observation)
        return (null,)


class AlwaysInfeasibleVariation:
    """Proposes structurally different but causally-inert candidates every
    generation -- evaluated, always infeasible, elite always advances.

    Post Phase-28 identity migration, elite advancement must be ARCHITECTURAL:
    a seed-unique trigger guarantees the proposed edge is semantically new in
    every generation (provenance stamping can no longer fabricate novelty).
    """

    def generate(self, defective_isr, observation, population_size, seed):
        exploration = RandomFSMExploration(
            trigger_pool=(f"explore-{seed}",), max_candidates=1,
        )
        return exploration.generate(defective_isr, observation, 1, seed)


class LineageForgingVariation:
    """Proposes a valid repair whose declared parent is NOT the current parent
    -- the lineage check must reject it before evaluation."""

    def __init__(self, wrong_parent: ISR):
        self._wrong_parent = wrong_parent

    def generate(self, defective_isr, observation, population_size, seed):
        candidate = TransitionRestorationOperator().propose(defective_isr, observation)
        if candidate is None:
            return ()
        forged = MutationCandidate(
            candidate_id=candidate.candidate_id,
            operator_id=candidate.operator_id,
            candidate_isr=candidate.candidate_isr,
            parent_isr=self._wrong_parent,
            mutation_delta=candidate.mutation_delta,
            hypothesis=candidate.hypothesis,
        )
        return (forged,)


class DualRepairVariation:
    """Two operators proposing the SAME feasible repair with equal fitness --
    a genuine 2-member Pareto frontier (non-dominated, identical objectives)
    resolved only by the deterministic candidate_id tie-break.

    On the FSM substrate the delta-closure pins a feasible candidate ISR
    uniquely, so a distinct feasible ISR with equal complexity cannot exist;
    the multi-member frontier is therefore exercised at the selection layer
    with two valid proposals of the same repair."""

    def generate(self, defective_isr, observation, population_size, seed):
        repair = TransitionRestorationOperator().propose(defective_isr, observation)
        if repair is None:
            return ()
        clone = MutationCandidate(
            candidate_id=f"alt_restoration:{stable_isr_hash(repair.candidate_isr)[:12]}",
            operator_id="alt_restoration",
            candidate_isr=repair.candidate_isr,
            parent_isr=repair.parent_isr,
            mutation_delta=repair.mutation_delta,
            hypothesis=repair.hypothesis,
        )
        return (repair, clone)


class SingleRepairVariation:
    """Lean variation for the Docker-gated end-to-end: proposes ONLY the
    targeted repair. Proves real-substrate convergence (feasible at gen 0)
    while bounding the container budget to broken + baseline + repair
    (compile + recompile + run)."""

    def generate(self, defective_isr, observation, population_size, seed):
        repair = TransitionRestorationOperator().propose(defective_isr, observation)
        return (repair,) if repair is not None else ()


# -- tests --------------------------------------------------------------------

def test_generation_identity_and_lineage_chain():
    sandbox = FsmStubSandbox()
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _build_harness(
        AlwaysInfeasibleVariation(), sandbox
    )
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=3, population_size=4, seed=0,
    )
    assert state.termination_reason is TerminationReason.GENERATION_LIMIT
    assert state.generation_count == 3
    for i, gen in enumerate(state.generations):
        assert gen.generation_id == derive_generation_id(state.evolution_id, i, gen.parent_isr_hash)
        assert gen.parent_generation_id == (state.generations[i - 1].generation_id if i else None)
        assert gen.diversity.population_size >= 0
        assert isinstance(gen.population_snapshot.candidate_ids, tuple)
    # unbroken lineage: each generation's parent hash is the previous selected hash
    for i in range(1, state.generation_count):
        assert state.generations[i].parent_isr_hash == state.generations[i - 1].selected_isr_hash
    assert state.generations[0].parent_isr_hash == stable_isr_hash(defective)


def test_converges_in_two_generations_via_elite_advancement():
    """The known FSM defect survives a search across generations: gen 0 has no
    feasible candidate (repair withheld), the elite is advanced; gen 1 proposes
    the repair and converges."""
    sandbox = FsmStubSandbox()
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _build_harness(
        GatedRepairVariation(restore_from_generation=1), sandbox
    )
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=4, population_size=6, seed=0,
    )
    assert state.succeeded
    assert state.termination_reason is TerminationReason.SUCCESS
    assert state.generation_count >= 2
    assert state.final_isr_hash is not None
    assert _has_resolution(defective) is False
    # gen 0 advanced an elite (no feasible candidate) -- recorded, not hidden
    assert state.generations[0].feasible_count == 0
    assert state.generations[0].elite_advanced
    assert state.generations[0].selected_isr_hash is not None
    # lineage is the thread
    assert state.generations[1].parent_isr_hash == state.generations[0].selected_isr_hash


def test_standard_defect_converges_in_single_generation():
    """With the full default variation the one-shot repair is available at gen 0
    -- the substrate's truth: feasible implies resolved."""
    sandbox = FsmStubSandbox()
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _build_harness(
        FSMRepairVariation(), sandbox
    )
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=5, population_size=8, seed=0,
    )
    assert state.succeeded
    assert state.generation_count == 1
    assert state.generations[0].feasible_count >= 1
    assert state.generations[0].selected_isr_hash == state.final_isr_hash


def test_deterministic_replay():
    sandbox = FsmStubSandbox()
    kwargs = dict(max_generations=4, population_size=6, seed=77)
    a_coord, *a_rest = _build_harness(GatedRepairVariation(), sandbox)
    b_coord, *b_rest = _build_harness(GatedRepairVariation(), sandbox)
    defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = a_rest

    a = a_coord.run(defective, observation, broken_artifact, broken_run,
                    baseline_artifact, baseline_run, **kwargs)
    b = b_coord.run(defective, observation, broken_artifact, broken_run,
                    baseline_artifact, baseline_run, **kwargs)
    assert a.evolution_id == b.evolution_id
    assert a.termination_reason is b.termination_reason
    assert [g.generation_id for g in a.generations] == [g.generation_id for g in b.generations]
    assert [g.parent_isr_hash for g in a.generations] == [g.parent_isr_hash for g in b.generations]
    assert [g.selected_isr_hash for g in a.generations] == [g.selected_isr_hash for g in b.generations]


def test_evaluation_isolation_no_stale_evidence():
    """Every generation recompiles and re-runs its parent and candidates; the
    stub's build/run counters must reflect fresh work in every generation."""
    sandbox = FsmStubSandbox()
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _build_harness(
        GatedRepairVariation(), sandbox
    )
    builds_before = sandbox.build_count
    runs_before = sandbox.run_count
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=4, population_size=6, seed=0,
    )
    assert state.generation_count >= 2
    for gen in state.generations:
        assert gen.evaluated_count > 0
    # candidate + independent-recompile + (gen>=1) parent rebuild per generation
    assert sandbox.build_count > builds_before
    assert sandbox.run_count > runs_before
    # every evaluated candidate bound to its own generation's fresh evidence
    for gen in state.generations:
        assert gen.evaluated_count == gen.diversity.population_size


def test_lineage_break_rejected():
    sandbox = FsmStubSandbox()
    wrong_parent = _isr(resolving=True)  # NOT the current (defective) parent
    ledger = EvolutionLedger()
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _build_harness(
        LineageForgingVariation(wrong_parent), sandbox, ledger=ledger
    )
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=2, population_size=4, seed=0,
    )
    assert state.termination_reason is TerminationReason.LINEAGE_BREAK
    # the forged candidate was rejected at the lineage gate before evaluation
    rejected = [e for e in ledger.events()
                if e.event_type.value == "candidate_rejected"
                and e.payload.get("reason") == "lineage_break"]
    assert len(rejected) == 1


def test_diversity_observed_not_selected_on():
    sandbox = FsmStubSandbox()
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _build_harness(
        FSMRepairVariation(), sandbox
    )
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=3, population_size=8, seed=0,
    )
    for gen in state.generations:
        d = gen.diversity
        assert d.population_size > 0
        assert d.unique_isr_count <= d.population_size
        assert d.unique_delta_count <= d.population_size
        assert 0.0 <= d.genotype_entropy
        assert 0.0 <= d.duplicate_rate <= 1.0
        assert d.mutation_operator_distribution
    # the repair still wins despite any diversity signal (selection unaffected)
    assert state.succeeded


def test_monoculture_is_measurable():
    sandbox = FsmStubSandbox()
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _build_harness(
        MonocultureVariation(copies=6), sandbox
    )
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=2, population_size=8, seed=0,
    )
    assert state.succeeded
    d = state.generations[0].diversity
    assert d.population_size == 6
    assert d.unique_isr_count == 1
    assert d.duplicate_rate == pytest.approx(1 - 1 / 6)
    assert d.genotype_entropy == 0.0  # the monoculture diagnostic R2.9.4 needs
    assert d.mutation_operator_distribution == {"transition_restoration": 6}


def test_no_feasible_candidates_terminates():
    sandbox = FsmStubSandbox()
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _build_harness(
        IdentityVariation(), sandbox
    )
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=3, population_size=4, seed=0,
    )
    assert state.termination_reason is TerminationReason.NO_FEASIBLE_CANDIDATES
    assert state.generation_count == 1


def test_population_exhaustion_terminates():
    class EmptyVariation:
        def generate(self, defective_isr, observation, population_size, seed):
            return ()

    sandbox = FsmStubSandbox()
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _build_harness(
        EmptyVariation(), sandbox
    )
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=3, population_size=4, seed=0,
    )
    assert state.termination_reason is TerminationReason.POPULATION_EXHAUSTION
    assert state.generation_count == 1


def test_generation_limit_terminates():
    sandbox = FsmStubSandbox()
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _build_harness(
        AlwaysInfeasibleVariation(), sandbox
    )
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=3, population_size=4, seed=0,
    )
    assert state.termination_reason is TerminationReason.GENERATION_LIMIT
    assert state.generation_count == 3


def test_stagnation_detection():
    coordinator, *_ = _build_harness(IdentityVariation(), FsmStubSandbox())
    assert coordinator._is_stagnant([None, None]) is False
    assert coordinator._is_stagnant(["h", "h", "h"]) is True
    assert coordinator._is_stagnant(["h", "h", "g"]) is False


def test_multiple_pareto_candidates_deterministic_tie_break():
    sandbox = FsmStubSandbox()
    a_coord, *rest = _build_harness(DualRepairVariation(), sandbox)
    b_coord, *_ = _build_harness(DualRepairVariation(), FsmStubSandbox())
    defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = rest

    a = a_coord.run(defective, observation, broken_artifact, broken_run,
                    baseline_artifact, baseline_run,
                    max_generations=1, population_size=6, seed=9)
    b = b_coord.run(defective, observation, broken_artifact, broken_run,
                    baseline_artifact, baseline_run,
                    max_generations=1, population_size=6, seed=9)
    gen_a, gen_b = a.generations[0], b.generations[0]
    assert gen_a.frontier_size == 2
    assert gen_a.selected_candidate_id == gen_b.selected_candidate_id


def test_ledger_records_every_generation_event_sequence():
    sandbox = FsmStubSandbox()
    ledger = EvolutionLedger()
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _build_harness(
        GatedRepairVariation(), sandbox, ledger=ledger
    )
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=4, population_size=6, seed=0,
    )
    events = ledger.events()
    types = [e.event_type.value for e in events]
    # the canonical per-generation chain
    for gen in state.generations:
        gid = gen.generation_id
        assert any(t == "candidate_generated" and e.payload.get("generation_id") == gid
                   for e, t in zip(events, types))
        assert any(t == "candidate_evaluated" and e.payload.get("generation_id") == gid
                   for e, t in zip(events, types))
        assert any(t == "gate_evaluated" and e.payload.get("generation_id") == gid
                   for e, t in zip(events, types))
        assert any(t == "generation_completed" and e.payload.get("generation_id") == gid
                   for e, t in zip(events, types))
    assert types[0] == "observation"
    # every event shares the run's environment binding + chain integrity
    assert ledger.verify_event_chain()
    assert ledger.verify_environment_binding()
    # ordering: generated before evaluated before selected before completed
    gid = state.generations[0].generation_id
    order = [t for e, t in zip(events, types) if e.payload.get("generation_id") == gid]
    assert order.index("candidate_generated") < order.index("candidate_evaluated")
    assert order.index("candidate_evaluated") < order.index("candidate_selected")
    assert order.index("candidate_selected") < order.index("generation_completed")


def test_isr_never_contaminated_by_evolution_state():
    sandbox = FsmStubSandbox()
    known_good = _isr(resolving=True)
    defective = _drop_resolution_edge(known_good)
    defective_hash_before = stable_isr_hash(defective)
    coordinator, _, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _build_harness(
        GatedRepairVariation(), sandbox
    )
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=4, population_size=6, seed=0,
    )
    assert state.initial_isr_hash == defective_hash_before
    assert state.generations[0].parent_isr_hash == defective_hash_before
    # the ISR object itself is untouched by the search
    assert stable_isr_hash(defective) == defective_hash_before
    # EvolutionState carries no ISR reference at all
    assert not any(hasattr(g, "candidate_isr") for g in state.generations)


# -- end-to-end (Docker-gated): real substrate convergence --------------------

@pytest.mark.docker_integration
@pytest.mark.skipif(not docker_available(), reason="R2.9.3 gate requires Docker")
def test_r29_3_real_substrate_converges_in_one_generation(tmp_path):
    known_good_isr = _isr(resolving=True)
    defective_isr = _drop_resolution_edge(known_good_isr)
    from tiannara.application.evolution import RealBackendSandbox

    real = RealBackendSandbox(backend=FastAPIHexagonalBackend())
    broken_candidate = real.build(defective_isr, workspace=str(tmp_path / "broken"))
    broken_run = real.run_tests(broken_candidate)
    observation = real.classifier.classify(real.to_evidence(broken_run))
    assert observation is not None

    baseline_candidate = real.build(known_good_isr, workspace=str(tmp_path / "kg"))
    baseline_run = real.run_tests(baseline_candidate)
    assert baseline_run.exit_code == 0

    state = MultiGenerationEvolutionCoordinator(
        sandbox=real,
        gate=CandidateGate.default(),
        variation=SingleRepairVariation(),
        selection=DeterministicComplexityPreference(),
        diversity_observer=DiversityObserver(),
    ).run(
        defective_isr=defective_isr,
        observation=observation,
        broken_artifact=broken_candidate,
        broken_run=broken_run,
        baseline_artifact=baseline_candidate,
        baseline_run=baseline_run,
        max_generations=5,
        population_size=1,
        seed=0,
    )
    assert state.succeeded
    assert state.generation_count == 1
    assert state.generations[0].feasible_count >= 1
    assert state.final_isr_hash is not None