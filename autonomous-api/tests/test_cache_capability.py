import ast

from app.engine.builder import generate_main_app
from app.engine.capability_contract import implementation_report, verified_feature
from app.engine.capability_evidence import inspect_artifact
from app.engine.genome import Genome


def _genome() -> Genome:
    return Genome({
        "genome_id": "cache-test",
        "services": ["users"],
        "auth": "api_key",
        "database": "sqlite",
        "cors_enabled": False,
        "health_endpoints": True,
        "metrics_endpoints": False,
        "tracing_enabled": False,
        "retry_policy": {},
        "timeout_config": {},
        "circuit_breaker": False,
        "cache_enabled": True,
        "backends": [],
        "middleware": [],
        "security_policies": [],
        "logging_level": "",
    })


def test_cache_is_contract_implemented():
    genome = _genome()
    assert verified_feature(genome, "cache")
    report = implementation_report(genome)
    assert "cache" in report["implemented"]
    assert "cache" not in report["unmapped"]


def test_cache_lowerer_emits_bounded_ttl_safe_middleware():
    main = generate_main_app(_genome())
    ast.parse(main)
    assert "class ResponseCacheMiddleware" in main
    assert "CACHE_TTL_SECONDS" in main
    assert "CACHE_MAX_ENTRIES" in main
    assert "sha256(identity).hexdigest()" in main
    assert 'if method not in {"GET", "HEAD"}' in main
    assert 'if method in {"POST", "PUT", "PATCH", "DELETE"}' in main
    assert "_cache_store.clear()" in main
    assert 'app.add_middleware(ResponseCacheMiddleware)' in main
    assert '/__capability_probe__/cache' in main


def test_cache_artifact_evidence(tmp_path):
    artifact = tmp_path
    (artifact / "main.py").write_text(generate_main_app(_genome()), encoding="utf-8")
    (artifact / "security.py").write_text("def require_auth():\n    pass\n", encoding="utf-8")
    (artifact / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    services = artifact / "services"
    services.mkdir()
    (services / "users.py").write_text("router = None\n", encoding="utf-8")

    evidence = inspect_artifact(_genome(), str(artifact))
    assert evidence["cache"]["verified"]
    assert all(evidence["cache"]["checks"].values())
