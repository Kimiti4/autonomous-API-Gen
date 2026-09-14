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
        "logging_level": "INFO",
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
    assert evidence["health_endpoints"]["verified"]


def test_unsupported_requested_capability_never_becomes_verified(tmp_path):
    genome = _genome(rate_limiting=True, metrics_endpoints=True, tracing_enabled=True)
    build_genome_output(genome, str(tmp_path))
    evidence = inspect_artifact(genome, str(tmp_path))
    summary = summarize(evidence)

    assert not evidence["rate_limiting"]["verified"]
    assert not evidence["metrics_endpoints"]["verified"]
    assert not evidence["tracing"]["verified"]
    assert set(["rate_limiting", "metrics_endpoints", "tracing"]).issubset(summary["failed_or_unverified"])


def test_oauth2_is_not_mislabeled_as_supported_authentication(tmp_path):
    genome = _genome(auth="oauth2")
    try:
        build_genome_output(genome, str(tmp_path))
    except ValueError:
        return
    raise AssertionError("unsupported OAuth2 generation must fail closed")
