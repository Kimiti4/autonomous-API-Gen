import ast

from app.engine.builder import generate_main_app
from app.engine.capability_contract import implementation_report, verified_feature
from app.engine.capability_evidence import inspect_artifact
from app.engine.genome import Genome


def _genome() -> Genome:
    return Genome({
        "genome_id": "circuit-test",
        "services": ["users"],
        "auth": "api_key",
        "database": "sqlite",
        "cors_enabled": False,
        "health_endpoints": True,
        "metrics_endpoints": False,
        "tracing_enabled": False,
        "retry_policy": {},
        "timeout_config": {},
        "circuit_breaker": True,
        "backends": [],
        "middleware": [],
        "security_policies": [],
        "logging_level": "",
    })


def test_circuit_breaker_is_contract_implemented():
    genome = _genome()
    assert verified_feature(genome, "circuit_breaker")
    report = implementation_report(genome)
    assert "circuit_breaker" in report["implemented"]
    assert "circuit_breaker" not in report["unmapped"]


def test_circuit_breaker_lowerer_emits_executable_state_machine():
    main = generate_main_app(_genome())
    ast.parse(main)
    assert "class CircuitBreakerMiddleware" in main
    assert 'self.state = "CLOSED"' in main
    assert 'self.state = "OPEN"' in main
    assert 'self.state = "HALF_OPEN"' in main
    assert 'app.add_middleware(CircuitBreakerMiddleware)' in main
    assert '"Circuit open"' in main
    assert '/__capability_probe__/circuit-breaker' in main


def test_circuit_breaker_artifact_evidence(tmp_path):
    artifact = tmp_path
    (artifact / "main.py").write_text(generate_main_app(_genome()), encoding="utf-8")
    (artifact / "security.py").write_text("def require_auth():\n    pass\n", encoding="utf-8")
    (artifact / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    services = artifact / "services"
    services.mkdir()
    (services / "users.py").write_text("router = None\n", encoding="utf-8")

    evidence = inspect_artifact(_genome(), str(artifact))
    assert evidence["circuit_breaker"]["verified"]
    assert all(evidence["circuit_breaker"]["checks"].values())
