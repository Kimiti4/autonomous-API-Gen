"""R2.9.4 -- Anti-monoculture.

Evidence-first: proves monoculture is DETECTED (with thresholds validated by
the R2.9.4 evidence run over real diversity trajectories), the intervention
restores diversity, and the intervention never compromises multi-objective
selection or the R2.8 boundary -- diversity is a population-health
constraint, never a fitness objective, and injected candidates traverse the
identical evaluation path as the rest of the population.
"""
from __future__ import annotations

import inspect
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
    AwaitingSurfaceIntactInvariant,
    CandidateGate,
    DeterministicComplexityPreference,
    DeterministicDiversityInjection,
    DiversityDiagnostics,
    DiversityObserver,
    EvolutionLedger,
    FSMRepairVariation,
    MonocultureDetector,
    MonocultureThresholds,
    MultiGenerationEvolutionCoordinator,
    NullMutation,
    RandomFSMExploration,
    TestDeletionMutation,
    TerminationReason,
    TransitionRestorationOperator,
    stable_isr_hash,
)
from tiannara.application.evolution.anti_monoculture import MonocultureDiagnostic
from tiannara.application.evolution.candidate_sandbox import CompiledCandidate
from tiannara.application.evolution.compiler_sandbox import hash_artifact
from tiannara.application.evolution.evolution_state import DiversityMetrics
from tiannara.application.evolution.mutation_operators import MutationCandidate
from tiannara.domain.models.evidence import TestRunResult
from tiannara.domain.models.observation import (
    FailureCategory,
    FailureObservation,
    FailurePhase,
)

COROUTINE = "process_payment"

#: The perturbed sub-seed the injection policy uses; variation ensembles that
#: want to stay monocultural below it and diversify above it key on this.
_PERTURB = 10_000


# -- ISR fixtures (same faithful substrate as R2.9.3) -------------------------

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
    # NOTE: constructed directly (NOT isr.with_system(...)) -- with_system
    # stamps provenance.parent_hash from ISR.content_hash, which embeds the
    # volatile created_at timestamp, making the broken ISR's stable hash
    # non-reproducible across processes. Direct construction keeps the
    # replay/determinism tests hermetic without touching the Phase 28 model.
    return ISR(system=System(
        id=isr.system.id, name=isr.system.name, description=isr.system.description,
        modules=(broken_module,), deployment=isr.system.deployment,
        metadata=isr.system.metadata, global_policies=isr.system.global_policies,
        constraints=isr.system.constraints,
    ), version=isr.version, provenance=isr.provenance)


def _observation() -> FailureObservation:
    diagnostic = f"coroutine '{COROUTINE}' was never awaited"
    return FailureObservation(
        execution_id="exec-1", backend_id="stub", phase=FailurePhase.TEST,
        category=FailureCategory.TEST_FAILURE, exit_code=1,
        command=["pytest", "-W", "error::RuntimeWarning", "-q"],
        diagnostics=(diagnostic,),
        evidence_hash="obs-hash",
        stderr_excerpt=f"RuntimeWarning: {diagnostic}",
    )


def _has_resolution(isr: ISR) -> bool:
    for module in isr.system.modules:
        for wf in module.workflows:
            awaiting = [s for s in wf.states if s.metadata.get("awaits") == COROUTINE]
            if awaiting and not any(t.trigger == COROUTINE for t in wf.transitions):
                return False
    return True


class FsmStubSandbox:
    """Faithful hermetic FSM substrate (identical contract to R2.9.3's stub)."""

    def __init__(self):
        self._artifact_isr: dict[str, ISR] = {}

    def build(self, isr: ISR, workspace: str | None = None) -> CompiledCandidate:
        root = Path(workspace) if workspace else Path(tempfile.mkdtemp(prefix="stub-"))
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
        (root / "generated.py").write_text("\n".join(lines) + "\n" if lines else "", encoding="utf-8")
        artifact = CompiledCandidate(
            source_root=str(root), compile_ok=True, artifact_hash=hash_artifact(root),
        )
        self._artifact_isr[artifact.artifact_hash] = isr
        return artifact

    def run_tests(self, artifact: CompiledCandidate) -> TestRunResult:
        isr = self._artifact_isr.get(artifact.artifact_hash)
        repaired = isr is not None and _has_resolution(isr)
        return TestRunResult(
            passed=repaired, exit_code=0 if repaired else 1,
            total_tests=1, failed_tests=0 if repaired else 1,
            pass_count=1 if repaired else 0, duration_seconds=1.0,
        )


# -- purpose-built variation ensembles ----------------------------------------

class CollapsingVariation:
    """A variation ensemble that monocultures unless diversity is injected.

    Generation seeds (< _PERTURB) propose six identical identity candidates;
    the injection sub-seed (seed + _PERTURB) unlocks distinct exploration
    candidates. This mirrors the evidence run: the SAME operator can either
    collapse (identical ISRs) or diversify (distinct ISRs), and only the
    genotype signal tells them apart.
    """

    def generate(self, defective_isr, observation, population_size, seed):
        if seed < _PERTURB:
            null = NullMutation().propose(defective_isr, observation)
            return (null,) * 6
        return RandomFSMExploration().generate(defective_isr, observation, 4, seed)


class CollapsingDeceptiveVariation:
    """Collapses at generation seeds; injects a DECEPTIVE (test-deletion)
    candidate at the injection sub-seed. The R2.8 boundary must reject the
    injected deception -- there is no separate evaluation route."""

    def generate(self, defective_isr, observation, population_size, seed):
        if seed < _PERTURB:
            null = NullMutation().propose(defective_isr, observation)
            return (null,) * 6
        deceptive = TestDeletionMutation().propose(defective_isr, observation)
        return (deceptive,) if deceptive is not None else ()


class GatedRepairVariation:
    """Collapses at gen 0 (six copies of ONE infeasible exploration ISR --
    a monoculture whose elite differs from the parent, so the search advances),
    offers the genuine repair from gen 1 onward, and explores at the perturbed
    injection seeds. Proves the intervention restores diversity WITHOUT
    delaying or breaking repair."""

    def generate(self, defective_isr, observation, population_size, seed):
        if seed >= _PERTURB:
            return RandomFSMExploration().generate(defective_isr, observation, 4, seed)
        if seed >= 1:
            repair = TransitionRestorationOperator().propose(defective_isr, observation)
            return (repair,) * 6 if repair is not None else ()
        explorer = RandomFSMExploration(max_candidates=1).generate(
            defective_isr, observation, 1, seed
        )
        return (explorer[0],) * 6


class RepairCopiesVariation:
    """Repair-copy collapse at generation seeds (the MonocultureVariation
    shape); distinct exploration at the perturbed injection seeds so the
    injected candidates are genuinely different."""

    def generate(self, defective_isr, observation, population_size, seed):
        if seed < _PERTURB:
            repair = TransitionRestorationOperator().propose(defective_isr, observation)
            return (repair,) * 6 if repair is not None else ()
        return RandomFSMExploration().generate(defective_isr, observation, 4, seed)


# -- harness ------------------------------------------------------------------

def _make(variation, sandbox=None, policy=None, ledger=None):
    sandbox = sandbox or FsmStubSandbox()
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
        preservation_policy=policy,
    )
    return coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run


def _metrics(entropy, dup_rate, size=8):
    return DiversityMetrics(size, size, size, {"op": size}, entropy, 0.0, dup_rate)


def _distinct_candidates(count: int, parent: ISR, seed: int = 1):
    return list(RandomFSMExploration(max_candidates=count).generate(
        parent, _observation(), count, seed
    ))


# -- 1-3. detection + diagnostic (the evidence phase) -------------------------

def test_monoculture_detected_on_entropy_collapse():
    detector = MonocultureDetector()
    assert detector.is_monoculture(_metrics(entropy=0.0, dup_rate=1.0)) is True
    assert detector.is_monoculture(_metrics(entropy=0.4, dup_rate=0.0)) is True
    assert detector.is_monoculture(_metrics(entropy=0.6, dup_rate=0.8)) is True


def test_no_monoculture_when_diverse():
    detector = MonocultureDetector()
    assert detector.is_monoculture(_metrics(entropy=2.5, dup_rate=0.1)) is False
    assert detector.is_monoculture(_metrics(entropy=1.0, dup_rate=0.0)) is False
    # a single candidate is small, not monocultural
    assert detector.is_monoculture(_metrics(entropy=0.0, dup_rate=0.0, size=1)) is False


def test_diagnostic_reports_collapse_evidence():
    trajectory = [
        _metrics(entropy=2.0, dup_rate=0.1),   # gen 0 healthy
        _metrics(entropy=0.3, dup_rate=0.8),   # gen 1 collapsing
        _metrics(entropy=0.0, dup_rate=1.0),   # gen 2 collapsed
    ]
    diag = DiversityDiagnostics().diagnose(trajectory)
    assert diag.monoculture_detected is True
    assert diag.first_monoculture_generation == 1
    assert diag.min_entropy == 0.0
    assert diag.max_duplicate_rate == 1.0
    assert diag.generations_analyzed == 3
    assert diag.severity == "total_collapse"


def test_diagnostic_empty_and_healthy_trajectories():
    assert DiversityDiagnostics().diagnose([]) == MonocultureDiagnostic(False, None, 0.0, 0.0, 0)
    healthy = DiversityDiagnostics().diagnose([
        _metrics(entropy=2.5, dup_rate=0.0), _metrics(entropy=2.0, dup_rate=0.1),
    ])
    assert healthy.monoculture_detected is False
    assert healthy.severity == "none"


def test_entropy_measures_isr_diversity_not_operator_mix():
    """Evidence correction (R2.9.4): single-operator but distinct-ISR
    populations are healthy; entropy must reflect genotype spread."""
    broken = _drop_resolution_edge(_isr(resolving=True))
    observer = DiversityObserver()
    candidates = _distinct_candidates(4, broken, seed=5)
    assert all(c.operator_id == "random_fsm_exploration" for c in candidates)
    metrics = observer.observe_genotype(candidates)
    assert metrics.genotype_entropy > 0.0            # distinct ISRs, one operator
    assert metrics.duplicate_rate == 0.0
    identical = [candidates[0]] * 4
    collapsed = observer.observe_genotype(identical)
    assert collapsed.genotype_entropy == 0.0         # identical ISRs collapse


def test_thresholds_validated_by_evidence():
    """The R2.9.4 evidence run's separation, locked as a regression guard:
    the healthy full ensemble never flags under the default thresholds; the
    collapsing ensemble -- its control -- always does."""
    detector = MonocultureDetector()
    # healthy operator mixes observed across seeds (evidence script):
    # the full FSM ensemble's generations are never monocultural
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(FSMRepairVariation())
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=3, population_size=6, seed=0,
    )
    for gen in state.generations:
        assert not detector.is_monoculture(gen.diversity)
    # the collapsing ensemble monocultures at generation seeds (the control)
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(CollapsingVariation())
    collapsed = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=2, population_size=6, seed=0,
    )
    assert detector.is_monoculture(collapsed.generations[0].diversity) is True


def test_observe_genotype_is_pre_evaluation():
    broken = _drop_resolution_edge(_isr(resolving=True))
    observer = DiversityObserver()
    candidates = [NullMutation().propose(broken, _observation())] * 3
    metrics = observer.observe_genotype(candidates)
    assert metrics.phenotype_diversity == 0.0        # not yet evaluated
    assert metrics.genotype_entropy == 0.0
    assert metrics.duplicate_rate == pytest.approx(1 - 1 / 3)


# -- 4-8. the intervention ----------------------------------------------------

def test_injection_restores_diversity():
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
        CollapsingVariation(),
        policy=DeterministicDiversityInjection(injection_count=4),
    )
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=2, population_size=6, seed=42,
    )
    gen = state.generations[0]
    # the recorded trajectory reflects the POST-intervention population
    assert gen.diversity.genotype_entropy > 0.0
    assert gen.diversity.unique_isr_count > 1


def test_injected_candidates_traverse_r28_boundary():
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
        CollapsingDeceptiveVariation(),
        policy=DeterministicDiversityInjection(injection_count=3),
    )
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=1, population_size=5, seed=42,
        protected_invariants=(AwaitingSurfaceIntactInvariant(),),
    )
    gen = state.generations[0]
    # the injected deceptive candidate was evaluated and REJECTED by the
    # boundary (invariant violation), not accepted -- no separate route
    assert gen.evaluated_count > 1
    assert gen.feasible_count < gen.evaluated_count
    assert gen.feasible_count == 0


def test_diversity_not_used_as_fitness():
    """Structural guard: the SelectionStrategy never receives DiversityMetrics
    (the selector's signature takes only scored candidates). If a future
    change passes diversity to Pareto or selection, this test must fail --
    that is the guard against scalar collapse."""
    coordinator, *_ = _make(CollapsingVariation())
    params = inspect.signature(coordinator._selection.select).parameters
    assert not any("diversity" in p.lower() for p in params)
    assert not any("metrics" in p.lower() for p in params)


def test_replay_deterministic_with_intervention():
    def run_once():
        coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
            CollapsingVariation(),
            policy=DeterministicDiversityInjection(),
        )
        return coordinator.run(
            defective, observation, broken_artifact, broken_run,
            baseline_artifact, baseline_run,
            max_generations=2, population_size=6, seed=77,
        )

    a, b = run_once(), run_once()
    assert a.evolution_id == b.evolution_id
    assert [g.generation_id for g in a.generations] == [g.generation_id for g in b.generations]
    assert [g.selected_isr_hash for g in a.generations] == [g.selected_isr_hash for g in b.generations]
    assert [g.diversity.genotype_entropy for g in a.generations] == \
           [g.diversity.genotype_entropy for g in b.generations]


def test_policy_is_replaceable():
    def run(policy):
        coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
            CollapsingVariation(), policy=policy,
        )
        return coordinator.run(
            defective, observation, broken_artifact, broken_run,
            baseline_artifact, baseline_run,
            max_generations=1, population_size=6, seed=42,
        )

    state_none = run(None)          # R2.9.3 behavior preserved
    state_inj = run(DeterministicDiversityInjection())
    assert state_none.generations[0].diversity.unique_isr_count == 1
    assert state_inj.generations[0].diversity.unique_isr_count > 1
    assert state_inj.generations[0].diversity.unique_isr_count >= \
           state_none.generations[0].diversity.unique_isr_count


def test_no_intervention_when_diverse():
    broken = _drop_resolution_edge(_isr(resolving=True))
    policy = DeterministicDiversityInjection()
    diverse = _distinct_candidates(6, broken, seed=2)
    metrics = _metrics(entropy=2.5, dup_rate=0.0, size=6)
    result = policy.apply(diverse, metrics, lambda n, s: [], seed=1)
    assert list(result) == diverse                   # unchanged


def test_injection_is_deterministic_and_seeded():
    broken = _drop_resolution_edge(_isr(resolving=True))
    policy = DeterministicDiversityInjection(injection_count=4)
    monoculture = [NullMutation().propose(broken, _observation())] * 6
    metrics = _metrics(entropy=0.0, dup_rate=1 - 1 / 6, size=6)

    def generate_more(count, sub_seed):
        return RandomFSMExploration().generate(broken, _observation(), count, sub_seed)

    a = list(policy.apply(monoculture, metrics, generate_more, seed=3))
    b = list(policy.apply(monoculture, metrics, generate_more, seed=3))
    assert [stable_isr_hash(c.candidate_isr) for c in a] == \
           [stable_isr_hash(c.candidate_isr) for c in b]
    assert len(a) == 1 + 4                           # culled 6 -> 1, injected 4
    c = list(policy.apply(monoculture, metrics, generate_more, seed=3 + 1))
    assert [stable_isr_hash(x.candidate_isr) for x in c] != \
           [stable_isr_hash(x.candidate_isr) for x in a]   # perturbed seed -> new region


# -- 9-10. restraint and convergence ------------------------------------------

def test_convergence_preserved_under_intervention():
    """The anti-monoculture intervention did not break repair: a gen-0
    collapse is injected with exploration (and fails), yet the genuine repair
    wins through the boundary the moment it becomes available at gen 1."""
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
        GatedRepairVariation(),
        policy=DeterministicDiversityInjection(),
    )
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=5, population_size=8, seed=0,
    )
    assert state.succeeded is True
    assert state.generation_count >= 2               # collapsed gen 0, repaired gen 1
    collapsed_gen = state.generations[0]
    assert collapsed_gen.diversity.unique_isr_count > 1     # intervention fired
    assert collapsed_gen.feasible_count == 0                # injection did not launder
    repair_gen = state.generations[1]
    assert repair_gen.feasible_count >= 1                   # repair still wins
    assert repair_gen.diversity.unique_isr_count > 1        # intervention active at gen 1 too


def test_monoculture_repaired_population_still_converges():
    """MonocultureVariation-style run WITH the policy active: the culled
    repair survives (first copy kept), injected exploration is evaluated but
    the repair alone is feasible -- SUCCESS at gen 0."""

    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
        RepairCopiesVariation(),
        policy=DeterministicDiversityInjection(injection_count=4),
    )
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=3, population_size=8, seed=0,
    )
    assert state.succeeded is True
    gen = state.generations[0]
    assert gen.feasible_count >= 1
    assert gen.evaluated_count >= 2                 # injected candidates were evaluated
    assert gen.diversity.unique_isr_count >= 2


def test_ledger_records_preservation_intervention():
    ledger = EvolutionLedger()
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
        CollapsingVariation(),
        policy=DeterministicDiversityInjection(),
        ledger=ledger,
    )
    coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=1, population_size=6, seed=42,
    )
    preserved = [e for e in ledger.events()
                 if e.payload.get("note") == "diversity preservation applied"]
    assert len(preserved) == 1
    assert ledger.verify_event_chain()