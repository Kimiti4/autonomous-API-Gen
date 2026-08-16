"""R2.9.5 -- Adaptive operator scheduling.

Proves the four required properties: adaptation, exploration preservation,
determinism, and no authority escalation -- plus the ledger contract: every
scheduler decision is recorded with the statistics snapshot that produced it.

Credit assignment is immediate-outcome only: an operator is credited with the
outcome of the candidate it produced in the generation that produced it.

Determinism note (Phase-28 provenance debt, tracked for R2.9.7): candidate ISR
hashes inherit ``provenance.parent_hash`` from ``ISR.content_hash``, which
embeds the volatile ``created_at`` stamped by ``with_system``. The base ISR
here carries a FIXED ``created_at`` so generation-0 hashes are reproducible
across processes; generation >= 1 parents are created at run time, so R2.9.5
cross-run determinism is asserted at the scheduler level (allocations,
rationale, termination), which is the phase's contract.
"""
from __future__ import annotations

import dataclasses
import inspect
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from constitutional_architecture.isr.model import (
    ISR,
    ISRProvenance,
    Module,
    StateType,
    System,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)

from tiannara.application.evolution import (
    BudgetAllocation,
    CandidateGate,
    DeterministicComplexityPreference,
    DiversityObserver,
    EvidenceBasedScheduler,
    EvolutionLedger,
    FSMRepairVariation,
    MultiGenerationEvolutionCoordinator,
    OperatorStatistics,
    RandomFSMExploration,
    TransitionRestorationOperator,
    stable_isr_hash,
)
from tiannara.application.evolution.candidate_sandbox import CompiledCandidate
from tiannara.application.evolution.compiler_sandbox import hash_artifact
from tiannara.domain.models.evidence import TestRunResult
from tiannara.domain.models.observation import (
    FailureCategory,
    FailureObservation,
    FailurePhase,
)

COROUTINE = "process_payment"

#: Fixed provenance keeps the base ISR's content_hash (and therefore every
#: generation-0 candidate hash derived from it) reproducible across runs.
_FIXED_PROVENANCE = ISRProvenance(created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))


def _stats(**kwargs):
    return {n: OperatorStatistics(n, a, f, r)
            for n, (a, f, r) in kwargs.items()}


# -- ISR fixtures (deterministic construction, see R2.9.4 note on with_system) -

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
    ), provenance=_FIXED_PROVENANCE)


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


class ScheduledGatedRepairVariation:
    """Honors ``BudgetAllocation`` (like FSMRepairVariation); the repair
    operator is gated until ``seed >= gate`` so statistics accrue and the
    allocation visibly adapts across generations. Cold start defers the whole
    budget to exploration."""

    def __init__(self, gate: int = 1):
        self._repair = TransitionRestorationOperator()
        self._exploration = RandomFSMExploration(max_candidates=8)
        self._gate = gate

    @property
    def operator_ids(self):
        return (self._repair.operator_id, self._exploration.operator_id)

    def generate(self, defective_isr, observation, population_size, seed):
        allocation = BudgetAllocation(
            {
                self._repair.operator_id: 1,
                self._exploration.operator_id: max(0, population_size - 1),
            },
            max(0, population_size - 1), "test",
        )
        return self.generate_scheduled(defective_isr, observation, allocation, seed)

    def generate_scheduled(self, defective_isr, observation, allocation, seed):
        seen = {}
        if not allocation.allocations:
            for c in self._exploration.generate(
                defective_isr, observation, allocation.exploration_reserved, seed
            ):
                seen.setdefault(c.candidate_id, c)
            return tuple(sorted(seen.values(), key=lambda c: c.candidate_id))
        for op_id in sorted(allocation.allocations):
            count = allocation.allocations[op_id]
            if op_id == self._exploration.operator_id:
                for c in self._exploration.generate(
                    defective_isr, observation, count, seed
                ):
                    seen.setdefault(c.candidate_id, c)
            elif seed >= self._gate:
                proposed = self._repair.propose(defective_isr, observation)
                if proposed is not None:
                    seen.setdefault(proposed.candidate_id, proposed)
        return tuple(sorted(seen.values(), key=lambda c: c.candidate_id))


def _make(variation, scheduler=None, ledger=None):
    sandbox = FsmStubSandbox()
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
        operator_scheduler=scheduler,
    )
    return coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run


# -- 1. Adaptation: allocation shifts toward the successful operator ----------

def test_allocation_adapts_to_evidence():
    scheduler = EvidenceBasedScheduler(exploration_floor=0.2)
    stats = _stats(
        transition_restoration=(40, 31, 28),   # strong
        random_fsm_exploration=(40, 7, 3),     # weak
    )
    allocation = scheduler.schedule(stats, population_size=20, seed=1)
    assert allocation.allocations["transition_restoration"] > allocation.allocations["random_fsm_exploration"]


# -- 2. Exploration preservation: no operator monopolizes --------------------

def test_exploration_floor_prevents_monopoly():
    scheduler = EvidenceBasedScheduler(exploration_floor=0.25)
    stats = _stats(
        transition_restoration=(100, 100, 100),  # perfect
        random_fsm_exploration=(100, 0, 0),      # zero success
        guard_relaxation=(100, 0, 0),
    )
    allocation = scheduler.schedule(stats, population_size=20, seed=1)
    assert allocation.allocations["random_fsm_exploration"] > 0
    assert allocation.allocations["guard_relaxation"] > 0
    assert allocation.allocations["transition_restoration"] < 20
    assert allocation.exploration_reserved >= 1


def test_never_tried_operator_receives_budget():
    """Zero-attempt operators are Laplace-attractive: the exploration floor
    reaches operators with no history (no starvation-by-absence)."""
    scheduler = EvidenceBasedScheduler()
    stats = _stats(
        transition_restoration=(0, 0, 0),       # never attempted
        random_fsm_exploration=(40, 0, 0),      # attempted, zero success
    )
    allocation = scheduler.schedule(stats, population_size=10, seed=1)
    assert allocation.allocations["transition_restoration"] > 0
    assert allocation.allocations["transition_restoration"] > allocation.allocations["random_fsm_exploration"]


# -- 3. Determinism: same evidence + seed -> same schedule --------------------

def test_schedule_deterministic():
    scheduler = EvidenceBasedScheduler()
    stats = _stats(a=(10, 5, 4), b=(10, 2, 1), c=(10, 8, 6))
    a1 = scheduler.schedule(stats, 16, seed=5)
    a2 = scheduler.schedule(stats, 16, seed=5)
    assert a1.allocations == a2.allocations
    assert a1.exploration_reserved == a2.exploration_reserved


# -- 4. Cold start: no history -> defer to exploration ------------------------

def test_cold_start_defers_to_exploration():
    scheduler = EvidenceBasedScheduler()
    allocation = scheduler.schedule({}, population_size=10, seed=1)
    assert allocation.allocations == {}
    assert allocation.exploration_reserved == 10
    assert "cold_start" in allocation.rationale
    # pre-seeded zero-attempt entries are also cold start (no evidence yet)
    cold = scheduler.schedule(
        _stats(restoration=(0, 0, 0), exploration=(0, 0, 0)), 10, seed=1
    )
    assert cold.allocations == {}
    assert "cold_start" in cold.rationale


# -- 5. No authority escalation: BudgetAllocation cannot carry authority ------

def test_budget_allocation_cannot_escalate_authority():
    field_names = {f.name for f in dataclasses.fields(BudgetAllocation)}
    forbidden = {"candidate", "fitness", "verdict", "score", "isr", "artifact"}
    leaked = {n for n in field_names for bad in forbidden if bad in n.lower()}
    assert not leaked, f"BudgetAllocation leaks authority: {leaked}"


# -- 6. Scheduler signature has no candidate/fitness inputs -------------------

def test_scheduler_receives_only_evidence():
    params = inspect.signature(EvidenceBasedScheduler.schedule).parameters
    assert set(params) == {"self", "statistics", "population_size", "seed"}


# -- 7. Ledger records the decision with its evidence -------------------------

def test_scheduler_decision_logged_with_evidence():
    ledger = EvolutionLedger()
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
        FSMRepairVariation(),
        scheduler=EvidenceBasedScheduler(),
        ledger=ledger,
    )
    coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=3, population_size=8, seed=42,
    )
    events = [e for e in ledger.events()
              if e.event_type.name == "SCHEDULER_DECISION"]
    assert len(events) >= 1
    for e in events:
        assert "evidence" in e.payload and "rationale" in e.payload
        assert "allocations" in e.payload and "exploration_reserved" in e.payload
    assert ledger.verify_event_chain() is True


# -- 8. Allocation actually changes across generations as evidence accrues ----

def test_allocation_evolves_with_evidence():
    ledger = EvolutionLedger()
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
        ScheduledGatedRepairVariation(gate=1),
        scheduler=EvidenceBasedScheduler(),
        ledger=ledger,
    )
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=3, population_size=8, seed=42,
    )
    decisions = [e for e in ledger.events()
                 if e.event_type.name == "SCHEDULER_DECISION"]
    assert len(decisions) >= 2
    # generation 0: no history -> cold start
    assert "cold_start" in decisions[0].payload["rationale"]
    # generation 1: accrued evidence -> the never-attempted repair operator
    # (Laplace-attractive) dominates the budget over the failing exploration
    assert decisions[1].payload["rationale"].startswith("evidence:")
    alloc = decisions[1].payload["allocations"]
    assert alloc["transition_restoration"] > alloc["random_fsm_exploration"]
    assert state.succeeded is True


# -- 9. Convergence still holds with scheduling active ------------------------

def test_convergence_preserved_under_scheduling():
    coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
        FSMRepairVariation(),
        scheduler=EvidenceBasedScheduler(),
    )
    state = coordinator.run(
        defective, observation, broken_artifact, broken_run,
        baseline_artifact, baseline_run,
        max_generations=5, population_size=8, seed=42,
    )
    assert state.succeeded is True


# -- 10. Replay determinism with scheduling -----------------------------------

def test_replay_deterministic_with_scheduling():
    """Same evidence + seed -> same schedule, across independent runs. The
    base ISR's fixed provenance makes generation-0 hashes reproducible; the
    scheduler contract (allocations + rationale + termination) is asserted
    for the whole run (see the module determinism note)."""
    def run(ledger):
        coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
            ScheduledGatedRepairVariation(gate=1),
            scheduler=EvidenceBasedScheduler(),
            ledger=ledger,
        )
        return coordinator.run(
            defective, observation, broken_artifact, broken_run,
            baseline_artifact, baseline_run,
            max_generations=3, population_size=8, seed=77,
        )

    ledger_a, ledger_b = EvolutionLedger(), EvolutionLedger()
    a, b = run(ledger_a), run(ledger_b)
    assert a.termination_reason is b.termination_reason
    assert [g.generation_index for g in a.generations] == [g.generation_index for g in b.generations]
    assert [g.diversity.genotype_entropy for g in a.generations] == \
           [g.diversity.genotype_entropy for g in b.generations]
    decisions_a = [e for e in ledger_a.events() if e.event_type.name == "SCHEDULER_DECISION"]
    decisions_b = [e for e in ledger_b.events() if e.event_type.name == "SCHEDULER_DECISION"]
    assert [e.payload["allocations"] for e in decisions_a] == \
           [e.payload["allocations"] for e in decisions_b]
    assert [e.payload["rationale"] for e in decisions_a] == \
           [e.payload["rationale"] for e in decisions_b]
    assert [e.payload["exploration_reserved"] for e in decisions_a] == \
           [e.payload["exploration_reserved"] for e in decisions_b]


def test_replay_generation_zero_hashes_reproducible():
    """With the fixed base provenance, generation-0 candidate hashes are
    reproducible across processes (gen >= 1 stays Phase-28 debt)."""
    def run():
        coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
            FSMRepairVariation(),
            scheduler=EvidenceBasedScheduler(),
        )
        return coordinator.run(
            defective, observation, broken_artifact, broken_run,
            baseline_artifact, baseline_run,
            max_generations=3, population_size=8, seed=5,
        )

    a, b = run(), run()
    assert a.generation_count == 2                     # cold start + repair
    assert a.termination_reason is b.termination_reason
    assert [g.selected_isr_hash for g in a.generations[:1]] == \
           [g.selected_isr_hash for g in b.generations[:1]]


# -- scheduler-None preserves R2.9.4 behavior ---------------------------------

def test_scheduler_none_preserves_behavior():
    def run(scheduler):
        coordinator, defective, observation, broken_artifact, broken_run, baseline_artifact, baseline_run = _make(
            FSMRepairVariation(), scheduler=scheduler,
        )
        return coordinator.run(
            defective, observation, broken_artifact, broken_run,
            baseline_artifact, baseline_run,
            max_generations=5, population_size=8, seed=0,
        )

    plain = run(None)
    assert plain.succeeded is True
    assert plain.generation_count == 1                 # repair wins at gen 0
    assert [g.selected_isr_hash for g in plain.generations] == \
           [g.selected_isr_hash for g in run(None).generations]