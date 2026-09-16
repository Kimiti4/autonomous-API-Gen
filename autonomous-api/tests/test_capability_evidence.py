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
    genome = _genome(cache_enabled=True)
    build_genome_output(genome, str(tmp_path))
    evidence = inspect_artifact(genome, str(tmp_path))
    assert not evidence["cache"]["verified"]
    assert "cache" in summarize(evidence)["failed_or_unverified"]


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
