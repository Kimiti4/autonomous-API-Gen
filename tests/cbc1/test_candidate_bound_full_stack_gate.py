from dataclasses import dataclass

from certification.campaign.runner import _run_candidate_bound_full_stack_verifier


@dataclass
class Result:
    passed: bool
    candidate_hash: str
    findings: tuple = ()


class PassingVerifier:
    def verify_bound(self, inputs, candidate_hash):
        return Result(True, candidate_hash)


class FailingVerifier:
    def verify_bound(self, inputs, candidate_hash):
        return Result(False, candidate_hash, ("effect mismatch",))


class RaisingVerifier:
    def verify_bound(self, inputs, candidate_hash):
        raise RuntimeError("verification unavailable")


class UnboundVerifier:
    def __call__(self, frontend, api, backend, effects, consequences):
        return type("UnboundResult", (), {"passed": True, "findings": ()})()


INPUTS = ("frontend-ir", "api-ir", "backend-ir", (), ())
CANDIDATE_HASH = "a" * 64


def test_missing_full_stack_verifier_fails_closed():
    passed, detail = _run_candidate_bound_full_stack_verifier(
        None, INPUTS, CANDIDATE_HASH
    )
    assert passed is False
    assert "not configured" in detail


def test_missing_or_malformed_ir_inputs_fail_closed():
    assert not _run_candidate_bound_full_stack_verifier(
        PassingVerifier(), None, CANDIDATE_HASH
    )[0]
    assert not _run_candidate_bound_full_stack_verifier(
        PassingVerifier(), ("frontend",), CANDIDATE_HASH
    )[0]


def test_full_stack_verdict_must_explicitly_pass_and_is_candidate_bound():
    passed, detail = _run_candidate_bound_full_stack_verifier(
        PassingVerifier(), INPUTS, CANDIDATE_HASH
    )
    assert passed is True
    assert CANDIDATE_HASH in detail

    passed, detail = _run_candidate_bound_full_stack_verifier(
        FailingVerifier(), INPUTS, CANDIDATE_HASH
    )
    assert passed is False
    assert "effect mismatch" in detail


def test_full_stack_verifier_exception_fails_closed():
    passed, detail = _run_candidate_bound_full_stack_verifier(
        RaisingVerifier(), INPUTS, CANDIDATE_HASH
    )
    assert passed is False
    assert "RuntimeError" in detail


def test_missing_candidate_hash_fails_closed():
    assert not _run_candidate_bound_full_stack_verifier(
        PassingVerifier(), INPUTS, ""
    )[0]



def test_unbound_verifier_cannot_pass_by_echoing_success():
    passed, detail = _run_candidate_bound_full_stack_verifier(
        UnboundVerifier(), INPUTS, CANDIDATE_HASH
    )
    assert passed is False
    assert "verify_bound" in detail


def test_verifier_candidate_hash_mismatch_fails_closed():
    class MismatchedVerifier:
        def verify_bound(self, inputs, candidate_hash):
            return Result(True, "b" * 64)

    passed, detail = _run_candidate_bound_full_stack_verifier(
        MismatchedVerifier(), INPUTS, CANDIDATE_HASH
    )
    assert passed is False
    assert "binding mismatch" in detail
