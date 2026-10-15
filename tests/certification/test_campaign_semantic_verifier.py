from types import SimpleNamespace

from certification.campaign.runner import _run_semantic_correspondence_verifier


def test_missing_semantic_verifier_fails_closed():
    evidence, detail = _run_semantic_correspondence_verifier(None, {"source": {}}, "candidate")
    assert evidence == {}
    assert "not configured" in detail


def test_missing_semantic_inputs_fail_closed():
    evidence, detail = _run_semantic_correspondence_verifier(object(), None, "candidate")
    assert evidence == {}
    assert "inputs missing" in detail


def test_semantic_verifier_exception_fails_closed():
    class BrokenVerifier:
        def verify_bound(self, inputs, candidate_hash):
            raise RuntimeError("simulated verifier failure")

    evidence, detail = _run_semantic_correspondence_verifier(BrokenVerifier(), {}, "candidate")
    assert evidence == {}
    assert "failed closed" in detail


def test_semantic_verifier_requires_explicit_pass_and_all_hashes():
    class IncompleteVerifier:
        def verify_bound(self, inputs, candidate_hash):
            return SimpleNamespace(
                passed=True, source_hash="source", mapping_hash="", candidate_hash=candidate_hash,
            )

    evidence, detail = _run_semantic_correspondence_verifier(IncompleteVerifier(), {}, "candidate")
    assert evidence["passed"] is False
    assert "missing mapping_hash" in detail


def test_semantic_verifier_rejects_candidate_binding_mismatch():
    class WrongCandidateVerifier:
        def verify_bound(self, inputs, candidate_hash):
            return SimpleNamespace(
                passed=True, source_hash="source", mapping_hash="mapping",
                candidate_hash="stale-candidate",
            )

    evidence, detail = _run_semantic_correspondence_verifier(WrongCandidateVerifier(), {}, "candidate")
    assert evidence["passed"] is False
    assert "binding mismatch" in detail


def test_semantic_verifier_accepts_explicit_complete_matching_evidence():
    class ValidVerifier:
        def verify_bound(self, inputs, candidate_hash):
            return SimpleNamespace(
                passed=True, source_hash="source-sha256", mapping_hash="mapping-sha256",
                candidate_hash=candidate_hash, findings=(),
            )

    evidence, detail = _run_semantic_correspondence_verifier(ValidVerifier(), {"source": "bound"}, "candidate")
    assert evidence == {
        "passed": True, "source_hash": "source-sha256",
        "mapping_hash": "mapping-sha256", "candidate_hash": "candidate",
    }
    assert "passed" in detail
