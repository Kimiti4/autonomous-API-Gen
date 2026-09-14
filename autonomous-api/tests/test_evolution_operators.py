import pytest

from app.engine.genome import Genome
from app.core.crossover import crossover
from app.core.mutation import mutate


def make_genome(**overrides):
    data = {
        "services": ["users", "payments"],
        "auth": "jwt",
        "database": "postgres",
        "cache_enabled": True,
        "rate_limiting": True,
        "cors_enabled": False,
        "logging_level": "INFO",
        "api_version": "v2",
        "openapi_version": "3.1.0",
        "health_endpoints": True,
        "metrics_endpoints": True,
        "tracing_enabled": True,
        "circuit_breaker": True,
        "retry_policy": {"max_attempts": 3, "base_delay": 1.0},
        "timeout_config": {"connect_timeout": 5.0, "read_timeout": 10.0, "write_timeout": 10.0},
        "backends": [{"type": "cache", "implementation": "redis"}],
        "middleware": ["auth", "logging"],
        "security_policies": [{"type": "jwt_validation"}],
        "deployment_target": "docker-compose",
    }
    data.update(overrides)
    return Genome(data)


def test_crossover_preserves_all_evolvable_genes():
    parent1 = make_genome(auth="jwt", database="postgres", tracing_enabled=True)
    parent2 = make_genome(auth="api_key", database="mysql", tracing_enabled=False)
    child = crossover(parent1, parent2)

    p1 = parent1.encode()
    p2 = parent2.encode()
    child_data = child.encode()

    for field in child_data:
        if field in {"genome_id", "metrics"}:
            continue
        assert child_data[field] in (p1[field], p2[field])

    assert child.lineage["parent_ids"] == [parent1.genome_id, parent2.genome_id]


def test_mutation_preserves_genome_invariants():
    parent = make_genome()
    child = mutate(parent, mutation_rate=1.0)

    assert 2 <= len(child.services) <= 6
    assert set(child.services).issubset({
        "auth", "users", "payments", "analytics", "notifications", "search",
        "files", "admin", "products", "orders", "inventory", "reports",
    })
    assert child.auth in {"jwt", "oauth2", "api_key", "basic"}
    assert child.database in {"postgres", "sqlite", "mysql"}
    assert child.openapi_version in {"3.0.0", "3.1.0"}
    assert child.retry_policy["max_attempts"] >= 1
    assert child.retry_policy["max_delay"] >= child.retry_policy["base_delay"]
    assert child.timeout_config["connect_timeout"] > 0
    assert child.timeout_config["request_timeout"] > 0
    assert child.lineage["parent_ids"] == [parent.genome_id]


def test_mutation_rejects_invalid_rate():
    with pytest.raises(ValueError):
        mutate(make_genome(), mutation_rate=1.5)
