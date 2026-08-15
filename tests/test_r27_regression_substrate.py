"""R2.7 -- precise regression substrate (Docker-free unit coverage).

Covers the new evidence model (TestExecution / Baseline / RegressionClass /
RegressionResult), content-based test identity, the pytest -v parser, the
set-difference classifier, and the RegressionGate's per-test path plus its
aggregate-only fallback (R2.6 compatibility).
"""
from __future__ import annotations

import pytest

from tiannara.application.evolution.candidate_gate import (
    GateContext,
    RegressionGate,
    classify_regression,
)
from tiannara.application.evolution.mutation_operators import MutationCandidate
from tiannara.application.evolution.ledger import stable_isr_hash
from tiannara.domain.models.evidence import (
    REGRESSION_REJECT_CLASSES,
    Baseline,
    RegressionClass,
    RegressionResult,
    TestExecution,
    TestOutcome,
    TestRunResult,
)
from tiannara.domain.services.test_identity import (
    hash_test_body,
    parse_pytest_verbose,
)
from tiannara.application.evolution.compiler_sandbox import hash_run


# -- helpers --------------------------------------------------------------------

def _te(test_id: str, outcome: TestOutcome, content_hash: str = "body",
        flaky: bool = False) -> TestExecution:
    return TestExecution(
        test_id=test_id, outcome=outcome, content_hash=content_hash, flaky=flaky
    )


def _run(tests: tuple[TestExecution, ...], exit_code: int = 0) -> TestRunResult:
    failed = sum(1 for t in tests if t.outcome in (TestOutcome.FAILED, TestOutcome.ERROR))
    passed = exit_code == 0
    return TestRunResult(
        passed=passed, exit_code=exit_code,
        total_tests=len(tests), failed_tests=failed,
        tests=tests,
    )


# -- model / baseline immutability ---------------------------------------------

def test_baseline_is_frozen_and_content_pinned():
    tests = (_te("t::a", TestOutcome.PASSED), _te("t::b", TestOutcome.PASSED))
    base = Baseline.from_run(tests, environment_fingerprint="fp", baseline_id="b1")
    assert base.tests == tests
    assert base.content_hash  # non-empty, content-pinned
    # A second baseline over the same tests pins the same hash.
    assert Baseline.from_run(tests).content_hash == base.content_hash
    # Frozen: cannot mutate.
    with pytest.raises(Exception):
        base.baseline_id = "x"  # type: ignore[misc]


def test_baseline_different_tests_different_hash():
    a = Baseline.from_run((_te("t::a", TestOutcome.PASSED),))
    b = Baseline.from_run((_te("t::b", TestOutcome.PASSED),))
    assert a.content_hash != b.content_hash


# -- pytest -v parser ----------------------------------------------------------

def test_parse_pytest_verbose_extracts_per_test_outcomes():
    logs = (
        "============================= test session starts ==============================\n"
        "collected 3 items\n\n"
        "slug/tests/test_x.py::test_a PASSED [ 33%]\n"
        "slug/tests/test_x.py::TestClass::test_b FAILED [ 66%]\n"
        "slug/tests/test_x.py::test_c SKIPPED [100%]\n"
        "\n"
        "=============================== 1 failed, 1 passed, 1 skipped in 0.12s ===============================\n"
    )
    out = parse_pytest_verbose(logs)
    ids = [t.test_id for t in out]
    assert ids == [
        "slug/tests/test_x.py::test_a",
        "slug/tests/test_x.py::TestClass::test_b",
        "slug/tests/test_x.py::test_c",
    ]
    assert {t.outcome for t in out} == {
        TestOutcome.PASSED, TestOutcome.FAILED, TestOutcome.SKIPPED
    }
    assert out[0].attempt == 0
    assert all(t.flaky is False for t in out)


def test_parse_ignores_summary_and_collection_lines():
    logs = "collected 1 item\n= 1 passed in 0.05s =\nslug/t.py::test_x PASSED [100%]\n"
    out = parse_pytest_verbose(logs)
    assert len(out) == 1
    assert out[0].test_id == "slug/t.py::test_x"


# -- content-based test identity ----------------------------------------------

def _write_test(tree: Path, rel: str, body: str) -> str:
    path = tree / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return str(path)


def test_content_hash_same_body_different_name():
    """Rename (gutting evasion vector #1): same body, different name -> same hash."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tree:
        body = "def test_a():\n    assert 1 + 1 == 2\n"
        _write_test(Path(tree), "svc/tests/test_x.py", body)
        h_name_a = hash_test_body(tree, "svc/tests/test_x.py::test_a")
        body_b = body.replace("test_a", "test_b")
        _write_test(Path(tree), "svc/tests/test_y.py", body_b)
        h_name_b = hash_test_body(tree, "svc/tests/test_y.py::test_b")
    assert h_name_a and h_name_b
    assert h_name_a == h_name_b  # identical body, different name -> identical identity


def test_content_hash_gutting_detected():
    """Gutting (evasion #2): same name, assertion removed -> different hash."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tree:
        full = "def test_a():\n    assert 1 + 1 == 2\n    assert 2 + 2 == 4\n"
        gutted = "def test_a():\n    assert 1 + 1 == 2\n"
        _write_test(Path(tree), "svc/tests/test_x.py", full)
        h_full = hash_test_body(tree, "svc/tests/test_x.py::test_a")
        _write_test(Path(tree), "svc/tests/test_x.py", gutted)
        h_gutted = hash_test_body(tree, "svc/tests/test_x.py::test_a")
    assert h_full and h_gutted
    assert h_full != h_gutted


def test_content_hash_empty_when_no_tree():
    assert hash_test_body(None, "svc/tests/test_x.py::test_a") == ""


# -- classify_regression -------------------------------------------------------

def test_regression_preserved_pass_accepted():
    base = _run((_te("t::a", TestOutcome.PASSED, content_hash="h"),
                 _te("t::b", TestOutcome.PASSED, content_hash="h")))
    cand = _run((_te("t::a", TestOutcome.PASSED, content_hash="h"),
                _te("t::b", TestOutcome.PASSED, content_hash="h")))
    res = classify_regression(base, cand)
    assert res.accept
    assert res.class_counts[RegressionClass.PRESERVED_PASS.value] == 2
    assert res.precision == "per_test"


def test_regression_regressed_failure_rejects():
    base = _run((_te("t::a", TestOutcome.PASSED, "h"),))
    cand = _run((_te("t::a", TestOutcome.FAILED, "h"),), exit_code=1)
    res = classify_regression(base, cand)
    assert not res.accept
    assert RegressionClass.REGRESSED_FAILURE in {
        RegressionClass(k) for k in res.class_counts
    }
    assert res.regressed == ("t::a",)


def test_regression_removed_test_rejects():
    base = _run((_te("t::a", TestOutcome.PASSED, "h"),
                 _te("t::b", TestOutcome.PASSED, "h")))
    cand = _run((_te("t::a", TestOutcome.PASSED, "h"),))
    res = classify_regression(base, cand)
    assert not res.accept
    assert res.vanished == ("t::b",)
    assert RegressionClass.REMOVED_TEST in REGRESSION_REJECT_CLASSES


def test_regression_new_failure_rejects():
    base = _run((_te("t::a", TestOutcome.PASSED, "h"),))
    cand = _run((_te("t::a", TestOutcome.PASSED, "h"),
                 _te("t::new", TestOutcome.FAILED, "h")), exit_code=1)
    res = classify_regression(base, cand)
    assert not res.accept
    assert RegressionClass.NEW_FAILURE in {RegressionClass(k) for k in res.class_counts}


def test_regression_new_skip_rejects():
    base = _run((_te("t::a", TestOutcome.PASSED, "h"),))
    cand = _run((_te("t::a", TestOutcome.PASSED, "h"),
                 _te("t::new", TestOutcome.SKIPPED, "h")))
    res = classify_regression(base, cand)
    assert not res.accept
    assert RegressionClass.NEW_SKIP in REGRESSION_REJECT_CLASSES


def test_regression_persisting_failure_rejects():
    base = _run((_te("t::a", TestOutcome.FAILED, "h"),), exit_code=1)
    cand = _run((_te("t::a", TestOutcome.FAILED, "h"),), exit_code=1)
    res = classify_regression(base, cand)
    assert not res.accept
    assert res.persisting == ("t::a",)


def test_regression_new_error_rejects():
    base = _run((_te("t::a", TestOutcome.PASSED, "h"),))
    cand = _run((_te("t::a", TestOutcome.PASSED, "h"),
                 _te("t::boom", TestOutcome.ERROR, "h")), exit_code=1)
    res = classify_regression(base, cand)
    assert not res.accept
    assert RegressionClass.NEW_ERROR in {RegressionClass(k) for k in res.class_counts}


def test_regression_flake_rejects():
    base = _run((_te("t::a", TestOutcome.PASSED, "h"),))
    cand = _run((_te("t::a", TestOutcome.PASSED, "h", flaky=True),))
    res = classify_regression(base, cand)
    assert not res.accept
    assert res.flake == ("t::a",)


def test_regression_content_gutting_rejects():
    """Same name, body gutted (assertion removed), still passes -> reject."""
    base = _run((_te("t::a", TestOutcome.PASSED, content_hash="FULL"),))
    cand = _run((_te("t::a", TestOutcome.PASSED, content_hash="GUTTED"),))
    res = classify_regression(base, cand)
    assert not res.accept
    assert res.gutting == ("t::a",)
    assert RegressionClass.CONTENT_GUTTING in REGRESSION_REJECT_CLASSES


def test_regression_resolved_failure_accepted():
    base = _run((_te("t::a", TestOutcome.FAILED, "h"),), exit_code=1)
    cand = _run((_te("t::a", TestOutcome.PASSED, "h"),))
    res = classify_regression(base, cand)
    assert res.accept
    assert res.class_counts[RegressionClass.RESOLVED_FAILURE.value] == 1


def test_regression_aggregate_fallback_preserves_r26_behavior():
    """No per-test outcomes -> pass-count comparison (R2.6 semantics)."""
    base = TestRunResult(passed=True, exit_code=0, total_tests=3, failed_tests=0, tests=())
    # Same count -> accept.
    res = classify_regression(base, TestRunResult(passed=True, exit_code=0,
                                                  total_tests=3, failed_tests=0, tests=()))
    assert res.accept
    assert res.precision == "aggregate_only"
    # Candidate drops a passing test -> reject.
    res2 = classify_regression(base, TestRunResult(passed=True, exit_code=0,
                                                   total_tests=2, failed_tests=0, tests=()))
    assert not res2.accept


def test_regression_counts_consistent_with_verdict():
    base = _run((_te("a", TestOutcome.PASSED, "h"), _te("b", TestOutcome.PASSED, "h")))
    cand = _run((_te("a", TestOutcome.PASSED, "h"), _te("b", TestOutcome.FAILED, "h")),
                exit_code=1)
    res = classify_regression(base, cand)
    assert not res.accept
    assert sum(res.class_counts.values()) == 2


# -- RegressionGate integration ------------------------------------------------

def _ctx(candidate_run, baseline_run) -> GateContext:
    isr = ISR_stub()
    return GateContext(
        candidate_isr=isr, candidate_artifact=None,
        candidate_run=candidate_run, baseline_run=baseline_run,
        baseline_artifact=None,
        observation=None, mutation=_stub_mutation(),
        parent_isr=isr, independent_recompile_hash="x", broken_artifact_hash="x",
    )


def ISR_stub():
    from constitutional_architecture.isr.model import (
        ISR, System, Module, Workflow, WorkflowState, WorkflowTransition, StateType,
    )
    aw = WorkflowState(id="aw", name="a", state_type=StateType.INTERMEDIATE,
                       metadata={"awaits": "process_payment"})
    fin = WorkflowState(id="fin", name="fin", state_type=StateType.FINAL)
    wf = Workflow(id="wf", name="wf", states=(aw, fin), transitions=())
    return ISR(system=System(id="s", name="S",
                             modules=(Module(id="m", name="M", workflows=(wf,)),)))


def _stub_mutation() -> MutationCandidate:
    isr = ISR_stub()
    return MutationCandidate(
        candidate_id="test", operator_id="test", candidate_isr=isr,
        parent_isr=isr, mutation_delta=__import__(
            "tiannara.application.evolution.mutation_operators",
            fromlist=["EMPTY_DELTA"]).EMPTY_DELTA,
        hypothesis="h",
    )


def test_regression_gate_per_test_rejects_gutting():
    gate = RegressionGate()
    base = _run((_te("t::a", TestOutcome.PASSED, "FULL"),))
    cand = _run((_te("t::a", TestOutcome.PASSED, "GUTTED"),))
    res = gate.evaluate(_ctx(cand, base))
    assert not res.passed
    assert "gutting" in res.reason or "regressed" in res.reason


def test_regression_gate_aggregate_fallback_when_no_tests():
    """Empty tests -> degrades to pass-count comparison (R2.6 green path)."""
    gate = RegressionGate()
    base = TestRunResult(passed=True, exit_code=0, total_tests=3, failed_tests=0)
    cand = TestRunResult(passed=True, exit_code=0, total_tests=3, failed_tests=0)
    res = gate.evaluate(_ctx(cand, base))
    assert res.passed
    assert res.evidence["precision"] == "aggregate-only (per-test outcomes not exposed by TestRunResult)"


# -- hash_run determinism ------------------------------------------------------

def test_hash_run_is_deterministic_and_includes_tests():
    run = _run((_te("t::a", TestOutcome.PASSED, "h"), _te("t::b", TestOutcome.PASSED, "h")))
    assert hash_run(run) == hash_run(run)
    # Adding a test changes the hash.
    run2 = _run((_te("t::a", TestOutcome.PASSED, "h"),
                 _te("t::b", TestOutcome.PASSED, "h"),
                 _te("t::c", TestOutcome.PASSED, "h")))
    assert hash_run(run) != hash_run(run2)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
