from app.engine.capability_contract import implementation_report
from app.engine.genome import Genome


def test_unimplemented_features_are_reported_as_unmapped():
    genome = Genome({
        "services": ["users"],
        "auth": "jwt",
        "database": "postgres",
        "cache_enabled": True,
        "rate_limiting": True,
        "tracing_enabled": True,
        "health_endpoints": False,
    })
    report = implementation_report(genome)

    assert "cache" in report["unmapped"]
    assert "rate_limiting" in report["unmapped"]
    assert "tracing" in report["unmapped"]
    assert "health_endpoints" not in report["unmapped"]
    assert report["coverage"] < 1.0


def test_supported_baseline_is_fully_mapped():
    genome = Genome({
        "services": ["users"],
        "auth": "jwt",
        "database": "postgres",
        "cors_enabled": True,
        "health_endpoints": True,
        "openapi_version": "3.0.0",
        "api_version": "v1",
        "cache_enabled": False,
        "rate_limiting": False,
        "metrics_endpoints": False,
        "tracing_enabled": False,
        "circuit_breaker": False,
        "retry_policy": {},
        "timeout_config": {},
        "backends": [],
        "middleware": [],
        "security_policies": [],
    })
    report = implementation_report(genome)
    assert report["unmapped"] == []
    assert report["coverage"] == 1.0


def test_oauth2_is_not_mislabeled_as_jwt_implementation():
    genome = Genome({"services": ["users"], "auth": "oauth2", "database": "postgres"})
    report = implementation_report(genome)
    assert "authentication" in report["unmapped"]
