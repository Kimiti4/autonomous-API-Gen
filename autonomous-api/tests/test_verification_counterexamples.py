from app.engine.verification_counterexamples import (
    derive_repair_strategies, derive_verification_counterexample,
    select_repair_strategy,
)

def counterexample():
    return derive_verification_counterexample(
        counterexample_id="CX-1", obligation_id="AO-1",
        verification_id="verify-1", implementation_ids=("impl:auth",),
        observed_failure="observed invariant mismatch", evidence_ids=("ev-1",),
        expected="deny", observed="allow")

def test_counterexample_is_evidence_bounded():
    x = counterexample()
    assert x.implementation_ids == ("impl:auth",)
    assert x.evidence_ids == ("ev-1",)

def test_strategies_are_explicit_and_bounded():
    r = derive_repair_strategies(
        counterexample(), candidate_operators=("tighten-rule", "add-check"),
        rationale_by_operator={"tighten-rule": "enforce failed condition",
                               "add-check": "reject observed invalid path"},
        required_verification_ids=("verify-1",))
    assert r.complete
    assert len(r.strategies) == 2
    assert all(s.bounded for s in r.strategies)

def test_missing_rationale_fails_closed():
    r = derive_repair_strategies(
        counterexample(), candidate_operators=("tighten-rule",),
        rationale_by_operator={}, required_verification_ids=("verify-1",))
    assert not r.complete
    assert "missing-repair-rationale:tighten-rule" in r.findings

def test_missing_verification_blocks_completion():
    r = derive_repair_strategies(
        counterexample(), candidate_operators=("tighten-rule",),
        rationale_by_operator={"tighten-rule": "fix failed condition"},
        required_verification_ids=())
    assert not r.complete
    assert "missing-repair-verification" in r.findings

def test_unknown_strategy_is_never_guessed():
    r = derive_repair_strategies(
        counterexample(), candidate_operators=("tighten-rule",),
        rationale_by_operator={"tighten-rule": "fix"}, required_verification_ids=("verify-1",))
    try:
        select_repair_strategy(r, strategy_id="CX-1:unknown")
        assert False
    except ValueError as exc:
        assert str(exc) == "repair-strategy-not-admitted"
