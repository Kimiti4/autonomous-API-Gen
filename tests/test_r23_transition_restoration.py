"""R2.3 -- hermetic spec for the TransitionRestoration operator, sandbox, and
causal ledger.

No real compiler/runtime: a MockRunner simulates the backend+codegen outcome
from the ISR graph (a dropped async-resolution transition => an un-awaited
coroutine warning). The RealFailureClassifier (R2.2) is the only interpreter
of raw output. The chain exercised: broken ISR -> FailureObservation ->
hypothesis -> repaired ISR -> validation -> EvolutionLedger record.
"""
from __future__ import annotations

import pytest

from constitutional_architecture.isr.model import (
    ISR,
    Module,
    System,
    Workflow,
    WorkflowState,
    WorkflowTransition,
    StateType,
)

from tiannara.application.evolution import (
    CandidateSandbox,
    EvolutionLedger,
    EvolutionRecord,
    RepairedCandidate,
    RunResult,
    TransitionRestoration,
    apply_restoration,
    attempt_repair_cycle,
    stable_isr_hash,
)
from tiannara.application.diagnosis.classifier import FailureClassifier, FailureEvidenceInput
from tiannara.domain.models.observation import FailureCategory, FailurePhase

COROUTINE = "process_payment"


def make_obs(coroutine_name: str) -> FailureObservation:
    """Fabricate a TEST_FAILURE observation carrying the coroutine signature
    via the real R2.2 classifier (the classifier remains the only interpreter
    of raw output -- no hand-built observations)."""
    ev = FailureEvidenceInput(
        execution_id="e-1", backend_id="fastapi_hexagonal", phase=FailurePhase.TEST,
        command=("pytest", "-W", "error::RuntimeWarning", "-q"), exit_code=1,
        stdout="FAILED tests/test_api.py::test_async - RuntimeWarning\n1 failed",
        stderr=f"RuntimeWarning: coroutine '{coroutine_name}' was never awaited\n",
    )
    return FailureClassifier().classify(ev)


def _workflow(name: str, coroutine: str, resolving: bool) -> Workflow:
    awaiting = WorkflowState(
        id=f"{name}-await", name="awaiting",
        state_type=StateType.INTERMEDIATE, metadata={"awaits": coroutine},
    )
    final = WorkflowState(id=f"{name}-final", name="final", state_type=StateType.FINAL)
    transitions = ()
    if resolving:
        transitions = (
            WorkflowTransition(
                id=f"resolve-{coroutine}", name=f"resolve {coroutine}",
                from_state_id=awaiting.id, to_state_id=final.id, trigger=coroutine,
            ),
        )
    return Workflow(id=name, name=name, states=(awaiting, final), transitions=transitions)


def _system(workflows) -> System:
    return System(
        id="sys", name="OrderSystem",
        modules=(Module(id="m", name="M", workflows=tuple(workflows)),),
    )


def _isr(workflows) -> ISR:
    return ISR(system=_system(workflows))


class MockRunner:
    """Simulates backend+codegen: an unresolved awaited coroutine surfaces as
    `RuntimeWarning: coroutine '<name>' was never awaited` under the warning flag."""

    @staticmethod
    def _unresolved_names(isr: ISR) -> list[str]:
        names: list[str] = []
        for module in isr.system.modules:
            for wf in module.workflows:
                for st in wf.states:
                    name = st.metadata.get("awaits")
                    if name and not any(t.trigger == name for t in wf.transitions):
                        names.append(name)
        return names

    def __call__(self, isr: ISR) -> RunResult:
        names = self._unresolved_names(isr)
        if names:
            return RunResult(
                execution_id="exec-broken",
                backend_id="fastapi_hexagonal",
                exit_code=1,
                stdout=(
                    "==================== test session starts ====================\n"
                    "collected 1 item\n\ntest_orders.py::test_handles_payment FAILED\n"
                    "!!!!!!!!!!!!!!!! 1 failed in 0.05s !!!!!!!!!!!!!!!!!\n"
                ),
                stderr=(
                    f"RuntimeWarning: coroutine '{names[0]}' was never awaited\n"
                    f"  gc: coroutine '{names[0]}' was never awaited\n"
                ),
            )
        return RunResult(
            execution_id="exec-ok", backend_id="fastapi_hexagonal",
            exit_code=0, stdout="3 passed in 0.1s", stderr="",
        )


def _sandbox() -> CandidateSandbox:
    return CandidateSandbox(MockRunner())


def test_known_good_isr_passes_under_warning_flag():
    isr = _isr([_workflow("order", COROUTINE, resolving=True)])
    assert _sandbox().run_tests(isr) is None


def test_broken_isr_yields_test_failure_with_coroutine_signature():
    isr = _isr([_workflow("order", COROUTINE, resolving=False)])
    obs = _sandbox().run_tests(isr)
    assert obs is not None
    assert obs.category is FailureCategory.TEST_FAILURE
    assert f"coroutine '{COROUTINE}' was never awaited" in obs.stderr_excerpt


def test_operator_extracts_name_and_hypotheses_repair():
    isr = _isr([_workflow("order", COROUTINE, resolving=False)])
    obs = _sandbox().run_tests(isr)
    op = TransitionRestoration()
    assert op.extract_coroutine_name(obs) == COROUTINE
    cand = op.hypothesis(obs, isr)
    assert isinstance(cand, RepairedCandidate)
    assert len(cand.repaired_diff) == 1
    assert "restore" in cand.hypothesis and COROUTINE in cand.hypothesis


@pytest.mark.parametrize("scenario", ["unmatched", "ambiguous", "already_present"])
def test_operator_declines_on_unmatched_ambiguous_or_present(scenario):
    if scenario == "unmatched":
        isr = _isr([_workflow("order", COROUTINE, resolving=False)])
        obs = make_obs("other_op")
    elif scenario == "ambiguous":
        isr = _isr([
            _workflow("w1", COROUTINE, resolving=False),
            _workflow("w2", COROUTINE, resolving=False),
        ])
        obs = make_obs(COROUTINE)
    else:
        isr = _isr([_workflow("order", COROUTINE, resolving=True)])
        obs = make_obs(COROUTINE)
    assert TransitionRestoration().hypothesis(obs, isr) is None


def test_repaired_isr_is_new_version_with_provenance():
    broken = _isr([_workflow("order", COROUTINE, resolving=False)])
    cand = TransitionRestoration().hypothesis(_sandbox().run_tests(broken), broken)
    assert cand is not None
    assert stable_isr_hash(cand.repaired_isr) != stable_isr_hash(broken)
    assert cand.repaired_isr.version == broken.version + 1
    assert cand.repaired_isr.provenance.parent_hash == broken.content_hash
    assert stable_isr_hash(cand.repaired_isr) != stable_isr_hash(broken)


def test_original_isr_stays_immutable():
    broken = _isr([_workflow("order", COROUTINE, resolving=False)])
    wf = broken.system.modules[0].workflows[0]
    TransitionRestoration().hypothesis(_sandbox().run_tests(broken), broken)
    assert wf.transitions == ()


def test_repaired_isr_passes_validation():
    broken = _isr([_workflow("order", COROUTINE, resolving=False)])
    cand = TransitionRestoration().hypothesis(_sandbox().run_tests(broken), broken)
    assert _sandbox().run_tests(cand.repaired_isr) is None


def test_repaired_diff_closure_invariant():
    broken = _isr([_workflow("order", COROUTINE, resolving=False)])
    obs = _sandbox().run_tests(broken)
    cand = TransitionRestoration().hypothesis(obs, broken)
    reconstructed = apply_restoration(broken, cand.repaired_diff)
    assert stable_isr_hash(reconstructed) == stable_isr_hash(cand.repaired_isr)


def test_ledger_records_causal_chain_entry():
    broken = _isr([_workflow("order", COROUTINE, resolving=False)])
    sandbox = _sandbox()
    obs = sandbox.run_tests(broken)
    record = attempt_repair_cycle(broken, obs, TransitionRestoration(), sandbox, EvolutionLedger())
    assert record is not None
    assert record.observation_hash == obs.evidence_hash
    assert record.broken_hash == stable_isr_hash(broken)
    assert record.operator == "transition_restoration"
    assert record.repaired_hash != record.broken_hash
    assert record.repaired_diff
    assert record.validation == (("build", "pass"), ("test", "pass"))
    assert record.decision == "accept"
    assert record.fitness_delta == 1.0
    assert record.parent_link == ""
    assert record.observation_hash != record.broken_hash


def test_ledger_hash_chain_links_successive_records(tmp_path):
    ledger = EvolutionLedger(root=str(tmp_path))
    r1 = ledger.append(EvolutionRecord(
        observation_hash="o1", broken_hash="b1", operator="transition_restoration",
        hypothesis="h1", repaired_hash="r1h", repaired_diff=(),
        validation=(("test", "pass"),), fitness_delta=1.0,
    ))
    r2 = ledger.append(EvolutionRecord(
        observation_hash="o2", broken_hash="b2", operator="transition_restoration",
        hypothesis="h2", repaired_hash="r2h", repaired_diff=(),
        validation=(("test", "pass"),), fitness_delta=1.0, parent_link=r1,
    ))
    assert r2 == ledger.latest_id
    first = ledger.get(r1)
    assert first is not None and first.parent_link == ""
    second = ledger.get(r2)
    assert second is not None and second.parent_link == r1
    assert ledger.chain_ok()


def test_attempt_repair_cycle_rejects_when_repair_fails():
    broken = _isr([_workflow("order", COROUTINE, resolving=False)])
    failing = RunResult(
        execution_id="e", backend_id="b", exit_code=1,
        stdout="FAILED tests/t::test_x\n1 failed",
        stderr=f"RuntimeWarning: coroutine '{COROUTINE}' was never awaited\n",
    )
    sandbox = CandidateSandbox(lambda isr: failing)
    obs = sandbox.run_tests(broken)
    assert obs is not None
    ledger = EvolutionLedger()
    record = attempt_repair_cycle(broken, obs, TransitionRestoration(), sandbox, ledger)
    assert record is not None
    assert record.decision == "reject"
    assert record.validation == (("build", "pass"), ("test", "fail"))
    assert record.fitness_delta == 0.0
    assert ledger.length == 1
