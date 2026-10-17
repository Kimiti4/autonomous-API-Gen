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


def test_default_independent_process_verifier_binds_disk_contents_to_candidate_hash(tmp_path):
    import hashlib
    import json
    from pathlib import Path

    from certification.campaign.plan_builder import build_artifacts_for
    from certification.campaign.runner import _IndependentProcessVerifier
    from certification.corpus.corpus import default_corpus
    from compiler.composition import build_backend_registry

    workload = default_corpus()[0]
    artifacts = build_artifacts_for(workload)
    backend = build_backend_registry().get("python-fastapi")
    repository = backend.compile(artifacts.plan)
    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir()
    for relative_path, body in repository.files.items():
        destination = candidate_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(body, encoding="utf-8")

    expected_paths = sorted(set(backend.element_paths(artifacts.plan).values()))
    plan_hash = hashlib.sha256(json.dumps(expected_paths).encode("utf-8")).hexdigest()
    plan_path = tmp_path / "independent-plan.json"
    plan_path.write_text(json.dumps({
        "expected_paths": expected_paths,
        "candidate_hash": repository.content_hash,
        "backend_name": backend.identity().name,
        "plan": artifacts.plan.model_dump(mode="json"),
    }), encoding="utf-8")

    verifier = _IndependentProcessVerifier()
    passed = verifier.verify(str(candidate_dir), plan_hash, str(plan_path))
    assert passed.passed is True
    assert passed.payload is not None
    assert passed.payload["candidate_match"] is True

    target = candidate_dir / expected_paths[0]
    target.write_text(target.read_text(encoding="utf-8") + "\n# mutation", encoding="utf-8")
    failed = verifier.verify(str(candidate_dir), plan_hash, str(plan_path))
    assert failed.passed is False
    assert "candidate_match" in failed.detail
    assert "stdout_tail=" in failed.detail



def test_structured_verifier_failure_preserves_diagnostics():
    from certification.campaign.runner import (
        _IndependentVerificationResult,
        _run_independent_verifier,
    )

    class DiagnosticVerifier:
        def verify(self, candidate_dir, plan_hash, plan_path):
            return _IndependentVerificationResult(
                False,
                "exit_code=2; missing_or_false=['candidate_match']; stderr_tail='hash mismatch'",
                {"candidate_match": False},
            )

    passed, detail = _run_independent_verifier(
        DiagnosticVerifier(), "/candidate", "hash", "/plan"
    )
    assert passed is False
    assert "candidate_match" in detail
    assert "hash mismatch" in detail


def test_truthy_non_boolean_verifier_result_never_passes():
    class TruthyVerifier:
        def verify(self, candidate_dir, plan_hash, plan_path):
            return {"passed": True}

    passed, detail = _run_independent_verifier(
        TruthyVerifier(), "/candidate", "hash", "/plan"
    )
    assert passed is False
    assert "explicit True" in detail



def test_independent_process_verifier_preserves_timeout_diagnostics(monkeypatch, tmp_path):
    import subprocess

    import certification.campaign.runner as runner

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(
            cmd=args[0], timeout=60, output="partial verifier output",
            stderr="verifier still running",
        )

    monkeypatch.setattr(runner.subprocess, "run", timeout)
    result = runner._IndependentProcessVerifier().verify(
        str(tmp_path), "candidate-hash", str(tmp_path / "plan.json")
    )
    assert result.passed is False
    assert "timed out after 60s" in result.detail
    assert "partial verifier output" in result.detail
    assert "verifier still running" in result.detail


def test_independent_process_verifier_preserves_start_error(monkeypatch, tmp_path):
    import certification.campaign.runner as runner

    def cannot_start(*args, **kwargs):
        raise OSError("executable unavailable")

    monkeypatch.setattr(runner.subprocess, "run", cannot_start)
    result = runner._IndependentProcessVerifier().verify(
        str(tmp_path), "candidate-hash", str(tmp_path / "plan.json")
    )
    assert result.passed is False
    assert "could not start" in result.detail
    assert "executable unavailable" in result.detail
