import random
import uuid
from typing import List, Dict, Any
from dataclasses import dataclass, field

@dataclass
class ServiceBlueprint:
    name: str
    endpoints: List[Dict[str, Any]] = field(default_factory=list)
    schema: Dict[str, Any] = field(default_factory=dict)
    tests: List[Dict[str, Any]] = field(default_factory=list)
    observability: Dict[str, Any] = field(default_factory=dict)
    security: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    performance_score: float = 0.0

@dataclass
class ProductionMetrics:
    openapi_completeness: float = 0.0
    auth_coverage: float = 0.0
    migration_safety: float = 0.0
    observability_coverage: float = 0.0
    latency_estimate: float = 0.0
    error_budget_estimate: float = 0.0
    dependency_risk: float = 0.0
    cloud_cost_estimate: float = 0.0
    test_coverage_score: float = 0.0
    security_score: float = 0.0
    architecture_complexity: float = 0.0
    performance_score: float = 0.0

class Genome:
    """Serializable, evolvable API architecture genome."""
    def __init__(self, genome_data: Dict[str, Any] = None, *, rng=None):
        self.genome_id = str(uuid.uuid4())
        self.metrics = ProductionMetrics()
        self.blueprints_used: List[str] = []
        self.policies_applied: List[str] = []
        self.deployment_target = "docker-compose"
        self.lineage: Dict[str, Any] = {}
        if genome_data:
            self._load(genome_data)
        else:
            self._generate_random_genome(rng or random)

    def _load(self, data):
        self.genome_id = data.get("genome_id", self.genome_id)
        self.services = data.get("services", [])
        self.auth = data.get("auth", "jwt")
        self.database = data.get("database", "postgres")
        self.cache_enabled = data.get("cache_enabled", False)
        self.rate_limiting = data.get("rate_limiting", False)
        self.cors_enabled = data.get("cors_enabled", True)
        self.logging_level = data.get("logging_level", "INFO")
        self.api_version = data.get("api_version", "v1")
        self.security_score = data.get("security_score", 1.0)
        self.openapi_version = data.get("openapi_version", "3.0.0")
        self.health_endpoints = data.get("health_endpoints", True)
        self.metrics_endpoints = data.get("metrics_endpoints", True)
        self.tracing_enabled = data.get("tracing_enabled", False)
        self.circuit_breaker = data.get("circuit_breaker", False)
        self.retry_policy = data.get("retry_policy", {})
        self.timeout_config = data.get("timeout_config", {})
        self.backends = data.get("backends", [])
        self.middleware = data.get("middleware", [])
        self.security_policies = data.get("security_policies", [])
        metrics_data = data.get("metrics")
        if metrics_data: self.metrics = ProductionMetrics(**metrics_data)
        self.blueprints_used = data.get("blueprints_used", [])
        self.policies_applied = data.get("policies_applied", [])
        self.deployment_target = data.get("deployment_target", "docker-compose")
        self.lineage = data.get("lineage", {})

    def _generate_random_genome(self, rng):
        available = ["auth", "users", "payments", "analytics", "notifications", "search", "files", "admin", "products", "orders", "inventory", "reports"]
        self.services = rng.sample(available, rng.randint(2, 6))
        self.auth = rng.choice(["jwt", "oauth2", "api_key", "basic"])
        self.database = rng.choice(["postgres", "sqlite", "mysql"])
        self.cache_enabled = rng.choice([True, False]); self.rate_limiting = rng.choice([True, False]); self.cors_enabled = rng.choice([True, False])
        self.logging_level = rng.choice(["DEBUG", "INFO", "WARNING", "ERROR"]); self.api_version = rng.choice(["v1", "v2", "v3"]); self.security_score = 1.0
        self.openapi_version = rng.choice(["3.0.0", "3.1.0"]); self.health_endpoints = rng.choice([True, False]); self.metrics_endpoints = rng.choice([True, False]); self.tracing_enabled = rng.choice([True, False]); self.circuit_breaker = rng.choice([True, False])
        self.retry_policy = {"max_attempts": rng.randint(2, 5), "base_delay": rng.uniform(0.1, 2.0), "max_delay": rng.uniform(5.0, 30.0), "backoff_multiplier": rng.uniform(1.5, 3.0)}
        self.timeout_config = {"connect_timeout": rng.uniform(5.0, 30.0), "read_timeout": rng.uniform(10.0, 60.0), "write_timeout": rng.uniform(10.0, 60.0), "request_timeout": rng.uniform(30.0, 120.0)}
        self.backends = self._generate_backends(rng); self.middleware = self._generate_middleware(rng); self.security_policies = self._generate_security_policies(rng)

    def _generate_backends(self, rng):
        result = []
        if self.cache_enabled: result.append({"type": "cache", "implementation": rng.choice(["redis", "memcached"]), "connection_pool_size": rng.randint(5, 20)})
        if len(self.services) > 3: result.append({"type": "message_queue", "implementation": rng.choice(["rabbitmq", "kafka"]), "partitions": rng.randint(1, 8)})
        return result

    def _generate_middleware(self, rng):
        return rng.sample(["auth", "caching", "logging", "tracing", "rate_limiting", "circuit_breaker", "retry", "compression", "cors", "security_headers"], rng.randint(2, 6))

    def _generate_security_policies(self, rng):
        policies = []
        if self.auth == "jwt": policies.append({"type": "jwt_validation", "algorithm": rng.choice(["HS256", "RS256"]), "expiration_minutes": rng.randint(60, 1440)})
        if self.rate_limiting: policies.append({"type": "rate_limiting", "requests_per_minute": rng.randint(10, 100), "burst_size": rng.randint(5, 50)})
        return policies

    def encode(self):
        return {"genome_id": self.genome_id, "services": self.services, "auth": self.auth, "database": self.database, "cache_enabled": self.cache_enabled, "rate_limiting": self.rate_limiting, "cors_enabled": self.cors_enabled, "logging_level": self.logging_level, "api_version": self.api_version, "security_score": self.security_score, "openapi_version": self.openapi_version, "health_endpoints": self.health_endpoints, "metrics_endpoints": self.metrics_endpoints, "tracing_enabled": self.tracing_enabled, "circuit_breaker": self.circuit_breaker, "retry_policy": self.retry_policy, "timeout_config": self.timeout_config, "backends": self.backends, "middleware": self.middleware, "security_policies": self.security_policies, "metrics": self.metrics.__dict__, "blueprints_used": self.blueprints_used, "policies_applied": self.policies_applied, "deployment_target": self.deployment_target, "lineage": self.lineage}

    def decode(self, data):
        self._load({**self.encode(), **data})

    def get_production_score(self):
        weights = {"openapi_completeness": .10, "auth_coverage": .15, "migration_safety": .08, "observability_coverage": .12, "latency_estimate": .10, "error_budget_estimate": .10, "dependency_risk": .10, "cloud_cost_estimate": .05, "test_coverage_score": .10, "security_score": .10}
        return round(sum(((1 - min(getattr(self.metrics, k), 1)) if k in {"dependency_risk", "cloud_cost_estimate"} else getattr(self.metrics, k)) * w for k, w in weights.items()), 3)

    def __repr__(self): return f"Genome(id={self.genome_id[:8]}, services={self.services}, auth={self.auth}, production_score={self.get_production_score()})"
