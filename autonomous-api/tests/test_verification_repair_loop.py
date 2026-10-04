import pytest
from app.engine.transaction_verification import CandidateVerification, TransactionVerificationConfig
from app.engine.verification_repair_loop import execute_verification_repair_loop


class D:
    def __init__(self, value): self.disposition = type("X", (), {"value": value})()


class V:
    def __init__(self, value, results=()):
        self.disposition = D(value)
        self.results = results
        self.evidence_digests = ("e",) if value == "PASS" else ()


def test_passing_verification_does_not_repair():
    called = []
    out = execute_verification_repair_loop(
        V("PASS"), repair_executor=lambda _: called.append(1),
        verification_config=None, verification_root=".", repair_candidates={}, max_attempts=1,
    )
    assert out.repaired is False
    assert called == []


def test_invalid_limit_fails_closed():
    with pytest.raises(ValueError, match="invalid-verification-repair-limit"):
        execute_verification_repair_loop(
            V("PASS"), repair_executor=lambda _: None,
            verification_config=None, verification_root=".", repair_candidates={}, max_attempts=0,
        )


def test_failed_loop_requires_real_failure_results():
    with pytest.raises(ValueError, match="missing-verification-failure"):
        execute_verification_repair_loop(
            V("FAIL"), repair_executor=lambda _: None,
            verification_config=None, verification_root=".", repair_candidates={}, max_attempts=1,
        )
