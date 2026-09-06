import copy
import random
from app.engine.genome import Genome


SERVICES = [
    "auth", "users", "payments", "analytics", "notifications", "search",
    "files", "admin", "products", "orders", "inventory", "reports"
]
AUTH_OPTIONS = ["jwt", "oauth2", "api_key", "basic"]
DATABASE_OPTIONS = ["postgres", "sqlite", "mysql"]
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
API_VERSIONS = ["v1", "v2", "v3"]
OPENAPI_VERSIONS = ["3.0.0", "3.1.0"]


def _bounded_float(value, minimum, maximum):
    return max(minimum, min(float(value), maximum))


def _mutate_retry_policy(policy):
    result = copy.deepcopy(policy)
    result["max_attempts"] = random.randint(1, 6)
    result["base_delay"] = random.uniform(0.05, 2.0)
    result["max_delay"] = random.uniform(max(result["base_delay"], 1.0), 30.0)
    result["backoff_multiplier"] = random.uniform(1.0, 3.0)
    return result


def _mutate_timeout_config(config):
    return {
        "connect_timeout": random.uniform(1.0, 30.0),
        "read_timeout": random.uniform(1.0, 60.0),
        "write_timeout": random.uniform(1.0, 60.0),
        "request_timeout": random.uniform(5.0, 120.0),
    }


def mutate(genome: Genome, mutation_rate: float = 0.2) -> Genome:
    """Mutate the complete evolvable genome.

    Derived structures such as backends and security policies are rebuilt from
    their parent genes, avoiding stale state after a gene changes.
    """
    if not 0.0 <= mutation_rate <= 1.0:
        raise ValueError("mutation_rate must be between 0 and 1")

    data = copy.deepcopy(genome.encode())

    if random.random() < mutation_rate:
        current = set(data["services"])
        if len(current) > 2 and random.random() < 0.5:
            current.remove(random.choice(sorted(current)))
        elif len(current) < 6:
            available = sorted(set(SERVICES) - current)
            if available:
                current.add(random.choice(available))
        data["services"] = sorted(current)

    if random.random() < mutation_rate:
        data["auth"] = random.choice(AUTH_OPTIONS)
    if random.random() < mutation_rate:
        data["database"] = random.choice(DATABASE_OPTIONS)
    if random.random() < mutation_rate:
        data["cache_enabled"] = not data["cache_enabled"]
    if random.random() < mutation_rate:
        data["rate_limiting"] = not data["rate_limiting"]
    if random.random() < mutation_rate:
        data["cors_enabled"] = not data["cors_enabled"]
    if random.random() < mutation_rate:
        data["logging_level"] = random.choice(LOG_LEVELS)
    if random.random() < mutation_rate:
        data["api_version"] = random.choice(API_VERSIONS)
    if random.random() < mutation_rate:
        data["openapi_version"] = random.choice(OPENAPI_VERSIONS)
    if random.random() < mutation_rate:
        data["health_endpoints"] = not data["health_endpoints"]
    if random.random() < mutation_rate:
        data["metrics_endpoints"] = not data["metrics_endpoints"]
    if random.random() < mutation_rate:
        data["tracing_enabled"] = not data["tracing_enabled"]
    if random.random() < mutation_rate:
        data["circuit_breaker"] = not data["circuit_breaker"]
    if random.random() < mutation_rate:
        data["retry_policy"] = _mutate_retry_policy(data.get("retry_policy", {}))
    if random.random() < mutation_rate:
        data["timeout_config"] = _mutate_timeout_config(data.get("timeout_config", {}))

    # These are derived from cache/services/auth and must not remain stale.
    child = Genome(genome_data=data)
    child.backends = child._generate_backends()
    child.middleware = child._generate_middleware()
    child.security_policies = child._generate_security_policies()
    child.metrics = type(child.metrics)()
    child.lineage = {
        "operator": "mutation",
        "parent_ids": [genome.genome_id],
        "mutation_rate": mutation_rate,
    }
    return child
