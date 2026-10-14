from certification.campaign.runner import _run_independent_verifier


class PassingVerifier:
    def verify(self, candidate_dir, plan_hash, plan_path):
        return True


class FalseVerifier:
    def verify(self, candidate_dir, plan_hash, plan_path):
        return False


class NoneVerifier:
    def verify(self, candidate_dir, plan_hash, plan_path):
        return None


class RaisingVerifier:
    def verify(self, candidate_dir, plan_hash, plan_path):
        raise RuntimeError("verifier unavailable")


def test_missing_verifier_fails_closed():
    passed, detail = _run_independent_verifier(None, "/candidate", "hash", "/plan")
    assert passed is False
    assert "no independent verifier" in detail


def test_explicit_true_is_required():
    assert _run_independent_verifier(PassingVerifier(), "/candidate", "hash", "/plan")[0] is True
    assert _run_independent_verifier(FalseVerifier(), "/candidate", "hash", "/plan")[0] is False
    assert _run_independent_verifier(NoneVerifier(), "/candidate", "hash", "/plan")[0] is False


def test_verifier_exception_fails_closed():
    passed, detail = _run_independent_verifier(RaisingVerifier(), "/candidate", "hash", "/plan")
    assert passed is False
    assert "RuntimeError" in detail
