import os

from app.engine.backend_contract import PYTHON_FASTAPI, make_compilation_request
from app.engine.backends import GoHTTPBackend, compile_architecture
from app.engine.candidate_evaluator import evaluate_candidate
from app.engine.evolution import EvolutionEngine
from app.engine.genome import Genome


ARCHITECTURE = {
    "services": ["users", "orders"],
    "auth": "api_key",
    "database": "sqlite",
    "cache_enabled": False,
    "rate_limiting": False,
    "cors_enabled": True,
    "logging_level": "",
    "api_version": "v1",
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


def test_same_architecture_compiles_through_both_targets():
    python_artifact = compile_architecture(make_compilation_request(ARCHITECTURE, PYTHON_FASTAPI))
    go_artifact = compile_architecture(make_compilation_request(ARCHITECTURE, GoHTTPBackend.target))

    assert python_artifact.metadata["backend_id"] == "python-fastapi"
    assert go_artifact.metadata["backend_id"] == "go-nethttp"
    assert python_artifact.metadata["architecture_hash"] == go_artifact.metadata["architecture_hash"]
    assert "main.py" in python_artifact.files
    assert "main.go" in go_artifact.files
    assert python_artifact.files != go_artifact.files


def test_artifact_provenance_is_deterministic_and_backend_specific():
    request = make_compilation_request(ARCHITECTURE, GoHTTPBackend.target)
    first = compile_architecture(request)
    second = compile_architecture(request)

    assert first.metadata == second.metadata
    assert first.metadata["backend_id"] == "go-nethttp"
    assert first.metadata["language"] == "go"
    assert first.metadata["framework"] == "net/http"
    assert first.metadata["architecture_schema"] == request.architecture_schema
    assert len(first.metadata["architecture_hash"]) == 64


def test_go_candidate_uses_same_candidate_evaluation_boundary_without_python_runtime_assumptions(tmp_path):
    result = evaluate_candidate(
        Genome(ARCHITECTURE),
        use_docker=True,
        output_dir=str(tmp_path),
        target=GoHTTPBackend.target,
    )

    assert result["backend_id"] == "go-nethttp"
    assert result["build_ok"] is True
    assert result["evaluation_mode"] == "static"
    assert result["static_score"] is not None
    assert result["error"] is None


def test_evolution_engine_accepts_explicit_backend_target():
    engine = EvolutionEngine(target=GoHTTPBackend.target)
    assert engine.target == GoHTTPBackend.target
    assert engine.target.backend_id == "go-nethttp"


def test_synchronous_evolution_uses_explicit_backend_target(monkeypatch):
    supported = Genome(ARCHITECTURE)

    class FixedPopulation:
        def __init__(self, size):
            self.individuals = [supported for _ in range(size)]

        def select_parents(self, fitness_scores, num_parents=2):
            return self.individuals[:num_parents]

        def replace(self, individuals):
            self.individuals = list(individuals)

    monkeypatch.setattr("app.engine.evolution.Population", FixedPopulation)

    engine = EvolutionEngine(target=GoHTTPBackend.target)
    result = engine.run_synchronous(generations=1, population_size=2)

    assert result["backend_id"] == "go-nethttp"
    assert result["build_error"] is None
    assert result["best_genome"] is not None
    assert result["output_path"] is not None
    assert os.path.isdir(result["output_path"])
