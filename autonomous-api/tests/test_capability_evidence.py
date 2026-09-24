from app.engine.capability_evidence import inspect_artifact, summarize
from app.engine.builder import build_genome_output
from app.engine.genome import Genome


def _genome(**overrides):
    data = {
        "genome_id": "evidence-test",
        "services": ["users"],
        "auth": "api_key",
        "database": "sqlite",
        "cache_enabled": False,
        "rate_limiting": False,
        "cors_enabled": True,
        "api_version": "v1",
        "security_score": 1.0,
        "openapi_version": "3.0.0",
        "health_endpoints": True,
        "metrics_endpoints": False,
        "tracing_enabled": False,
        "circuit_breaker": False,
        "retry_policy": {},
        "timeout_config": {},
        "backends": [],
        "middleware": [],
        "security_policies": [],
    }
    data.update(overrides)
    return Genome(data)


def test_supported_capabilities_require_artifact_evidence(tmp_path):
    genome = _genome()
    build_genome_output(genome, str(tmp_path))
    evidence = inspect_artifact(genome, str(tmp_path))
    assert evidence["services"]["verified"]
    assert evidence["database"]["verified"]
    assert evidence["authentication"]["verified"]
    assert evidence["cors"]["verified"]
    assert evidence["health_endpoints"]["verified"]
    assert evidence["api_version"]["verified"]
    assert summarize(evidence)["failed_or_unverified"] == []


def test_health_selection_must_match_generated_artifact(tmp_path):
    genome = _genome(health_endpoints=False)
    build_genome_output(genome, str(tmp_path))
    evidence = inspect_artifact(genome, str(tmp_path))
    assert not evidence["health_endpoints"]["requested"]
    assert not evidence["health_endpoints"]["verified"]
    assert evidence["health_endpoints"]["checks"]["selection_fidelity"]


def test_rate_limiting_and_metrics_are_lowered(tmp_path):
    genome = _genome(rate_limiting=True, metrics_endpoints=True)
    build_genome_output(genome, str(tmp_path))
    evidence = inspect_artifact(genome, str(tmp_path))
    assert evidence["rate_limiting"]["verified"]
    assert evidence["metrics_endpoints"]["verified"]
    assert summarize(evidence)["failed_or_unverified"] == []


def test_disabled_metrics_and_rate_limiting_are_not_emitted(tmp_path):
    genome = _genome(rate_limiting=False, metrics_endpoints=False, health_endpoints=False)
    build_genome_output(genome, str(tmp_path))
    evidence = inspect_artifact(genome, str(tmp_path))
    assert not evidence["rate_limiting"]["requested"]
    assert not evidence["metrics_endpoints"]["requested"]
    assert not evidence["health_endpoints"]["requested"]
    assert evidence["health_endpoints"]["checks"]["selection_fidelity"]


def test_unsupported_requested_capability_never_becomes_verified(tmp_path):
    genome = _genome(backends=["cache"])
    try:
        build_genome_output(genome, str(tmp_path))
    except ValueError:
        return
    raise AssertionError("requested unmapped capability must fail closed at compile")


def test_oauth2_is_not_mislabeled_as_supported_authentication(tmp_path):
    genome = _genome(auth="oauth2")
    try:
        build_genome_output(genome, str(tmp_path))
    except ValueError:
        return
    raise AssertionError("unsupported OAuth2 generation must fail closed")


def test_timeout_is_lowered_and_disabled_timeout_is_absent(tmp_path):
    genome = _genome(timeout_config={"request_timeout": 0.5})
    build_genome_output(genome, str(tmp_path))
    evidence = inspect_artifact(genome, str(tmp_path))
    assert evidence["timeout_config"]["verified"]
    assert evidence["timeout_config"]["checks"]["wait_for"]

    disabled = _genome(timeout_config={})
    disabled_dir = tmp_path / "disabled"
    build_genome_output(disabled, str(disabled_dir))
    disabled_evidence = inspect_artifact(disabled, str(disabled_dir))
    assert not disabled_evidence["timeout_config"]["requested"]
    assert disabled_evidence["timeout_config"]["checks"]["selection_fidelity"]


def test_invalid_timeout_is_rejected_during_generation(tmp_path):
    genome = _genome(timeout_config={"request_timeout": 0})
    try:
        build_genome_output(genome, str(tmp_path))
    except ValueError:
        return
    raise AssertionError("non-positive request timeout must fail closed")


def test_materialized_artifact_has_content_addressed_manifest(tmp_path):
    genome = _genome()
    build_genome_output(genome, str(tmp_path))
    import json
    manifest = json.loads((tmp_path / "artifact-manifest.json").read_text())
    assert manifest["artifact_digest"]
    assert manifest["architecture_hash"]
    assert manifest["files"]["main.py"]


def test_materialization_rejects_path_traversal(tmp_path):
    from app.engine.backends import materialize
    from app.engine.backend_contract import CompiledArtifact
    artifact = CompiledArtifact(
        backend_id="test",
        files={"../escape.py": "print('escape')"},
        metadata={"architecture_hash": "test"},
    )
    try:
        materialize(artifact, str(tmp_path / "candidate"))
    except ValueError as exc:
        assert "escapes output directory" in str(exc)
    else:
        raise AssertionError("path traversal must fail closed")

def test_verified_artifact_promotion_rejects_tampering(tmp_path):
    from app.engine.backends import promote_verified_artifact
    genome = _genome()
    source = tmp_path / "candidate"
    destination = tmp_path / "promoted"
    build_genome_output(genome, str(source))
    import json
    manifest = json.loads((source / "artifact-manifest.json").read_text())
    (source / "main.py").write_text("# tampered\n")
    try:
        promote_verified_artifact(str(source), str(destination), expected_digest=manifest["artifact_digest"])
    except ValueError as exc:
        assert "digest" in str(exc)
    else:
        raise AssertionError("tampered verified artifact must not be promoted")


def test_logging_level_is_bound_to_generated_artifact(tmp_path):
    genome = _genome(logging_level="WARNING")
    build_genome_output(genome, str(tmp_path))
    evidence = inspect_artifact(genome, str(tmp_path))
    assert evidence["logging_level"]["verified"]
    assert evidence["logging_level"]["checks"]["configured_level"]


def test_go_authentication_defaults_fail_closed():
    from app.engine.backends import GoHTTPBackend
    from app.engine.backend_contract import make_compilation_request
    genome = _genome(auth="api_key")
    request = make_compilation_request(genome.encode(), GoHTTPBackend.target)
    artifact = GoHTTPBackend().compile(request)
    source = artifact.files["main.go"]
    assert "generated-api-key" not in source
    assert "API_KEY is not configured" in source
    assert "generated-user" not in GoHTTPBackend._AUTH_BASIC
    assert "generated-pass" not in GoHTTPBackend._AUTH_BASIC
    assert "generated-jwt-secret" not in GoHTTPBackend._AUTH_JWT
