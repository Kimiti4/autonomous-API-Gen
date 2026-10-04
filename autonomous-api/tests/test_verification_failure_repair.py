import pytest

from app.engine.verification_failure_repair import (
    build_verification_repair_request,
    extract_verification_failures,
)


class E:
    def __init__(self, digest):
        self.evidence_digest = digest


class R:
    def __init__(self, vid, kind, passed, reason, digest="e1"):
        self.verification_id = vid
        self.kind = kind
        self.passed = passed
        self.reason = reason
        self.evidence = E(digest)


class K:
    value = "TEST"


def test_failed_executable_verification_becomes_repair_request():
    from app.engine.repair_coevolution import RepairCandidate
    candidate = RepairCandidate("m1", "r1", "backend", "fix", ("test",))
    request = build_verification_repair_request(
        (R("backend:test", K(), False, "exit=1"),),
        repair_candidates={"backend:test": candidate},
    )
    assert request.candidate == candidate
    assert request.failures[0].evidence_digests == ("e1",)


def test_passing_verification_produces_no_repair_request():
    with pytest.raises(ValueError, match="missing-verification-failure"):
        build_verification_repair_request(
            (R("backend:test", K(), True, ""),),
            repair_candidates={},
        )


def test_failure_without_operator_fails_closed():
    with pytest.raises(ValueError, match="missing-verification-repair-mutation"):
        build_verification_repair_request(
            (R("backend:test", K(), False, "exit=1"),),
            repair_candidates={},
        )
