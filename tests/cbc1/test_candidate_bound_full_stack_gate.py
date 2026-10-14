from dataclasses import dataclass

from certification.campaign.runner import _run_candidate_bound_full_stack_verifier


@dataclass
class Result:
    passed: bool
    findings: tuple = ()


class PassingVerifier:
    def __call__(self, frontend, api, backend, effects, consequences):
        return Result(True)


class FailingVerifier:
    def __call__(self, frontend, api, backend, effects, consequences):
        return Result(False, ("effect mismatch",))


class RaisingVerifier:
    def __call__(self, frontend, api, backend, effects, consequences):
        raise RuntimeError("verification unavailable")


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
