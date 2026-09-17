from app.engine.capability_semantics import plan_capabilities, plan_from_architecture
from app.engine.genome import Genome


ARCHITECTURE = {
    "services": ["users"],
    "auth": "api_key",
    "database": "sqlite",
    "cache_enabled": True,
    "rate_limiting": False,
    "cors_enabled": False,
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


def test_capability_plan_is_backend_neutral():
    plan = plan_from_architecture(ARCHITECTURE)

    assert "services" in plan.requested
    assert "cache" in plan.implemented
    assert plan.unmapped == ()
    assert not hasattr(plan, "framework")
    assert not hasattr(plan, "language")


def test_unmapped_capability_is_preserved_as_semantic_state():
    genome = Genome({**ARCHITECTURE, "middleware": ["custom"]})
    plan = plan_capabilities(genome)

    assert "middleware" in plan.requested
    assert "middleware" in plan.unmapped
    assert not plan.is_implemented("middleware")
    assert plan.requires("middleware")


def test_plan_does_not_mutate_architecture():
    architecture = dict(ARCHITECTURE)
    before = dict(architecture)

    plan_from_architecture(architecture)

    assert architecture == before
