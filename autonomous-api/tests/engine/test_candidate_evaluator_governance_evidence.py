from types import SimpleNamespace

from app.engine.backend_contract import CompiledArtifact
from app.engine.backends import materialize
import app.engine.candidate_evaluator as candidate_evaluator


def test_static_candidate_binds_artifact_digest_but_is_not_promotion_verified(tmp_path, monkeypatch):
    def _build(genome, output_dir, *, target):
        artifact = CompiledArtifact(
            backend_id=target.backend_id,
            files={"app/main.py": "def health(): return {'status': 'ok'}\n"},
            metadata={"architecture_hash": "architecture-hash"},
        )
        return materialize(artifact, output_dir)

    monkeypatch.setattr(candidate_evaluator, "build_genome_output", _build)
    monkeypatch.setattr(candidate_evaluator, "inspect_artifact", lambda *_args: {})
    monkeypatch.setattr(candidate_evaluator, "summarize", lambda _value: {})
    monkeypatch.setattr(candidate_evaluator, "calculate_fitness", lambda _genome: 0.9)

    genome = SimpleNamespace(
        genome_id="candidate-static",
        encode=lambda: {"candidate_id": "candidate-static"},
    )
    evidence = candidate_evaluator.evaluate_candidate(
        genome,
        use_docker=False,
        output_dir=str(tmp_path),
    )

    assert evidence["build_ok"] is True
    assert evidence["artifact_compile_ok"] is True
    assert evidence["artifact_digest"].startswith("sha256:")
    assert len(evidence["artifact_digest"]) == len("sha256:") + 64
    assert evidence["evaluation_mode"] == "static"
    assert evidence["runtime_score"] is None
    assert evidence["verification_status"] == "static_only"
