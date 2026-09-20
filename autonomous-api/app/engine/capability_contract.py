"""Genome-to-artifact capability contract.

A capability is IMPLEMENTED only when the current builder has a concrete
lowering. Runtime verification is a separate acceptance gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.engine.genome import Genome


@dataclass(frozen=True)
class CapabilityResult:
    name: str
    requested: bool
    implemented: bool
    reason: str


IMPLEMENTED_AUTH = {"jwt", "api_key", "basic"}
SUPPORTED_DATABASES = {"postgres", "mysql", "sqlite"}
SUPPORTED_MIDDLEWARE = {
    "auth", "caching", "tracing", "rate_limiting",
    "circuit_breaker", "retry", "cors",
}
SUPPORTED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}
SUPPORTED_SECURITY_POLICIES = {"jwt_validation", "rate_limiting"}


def _valid_request_timeout(config: dict[str, Any]) -> bool:
    try:
        value = float(config.get("request_timeout", 0))
    except (TypeError, ValueError):
        return False
    return value > 0


def _valid_retry_policy(config: dict[str, Any]) -> bool:
    try:
        attempts = int(config.get("max_attempts", 0))
        base_delay = float(config.get("base_delay", 0))
        max_delay = float(config.get("max_delay", 0))
        multiplier = float(config.get("backoff_multiplier", 0))
    except (TypeError, ValueError):
        return False
    return attempts >= 2 and base_delay >= 0 and max_delay >= base_delay and multiplier >= 1


def assess_genome(genome: Genome) -> list[CapabilityResult]:
    results: list[CapabilityResult] = []

    def add(name: str, requested: bool, implemented: bool, reason: str) -> None:
        results.append(CapabilityResult(name, requested, implemented, reason))

    add("services", bool(genome.services), bool(genome.services), "Service routers and SQL models are generated.")
    add("database", bool(genome.database), genome.database in SUPPORTED_DATABASES, "Database generation exists for PostgreSQL, MySQL and SQLite.")
    add("authentication", bool(genome.auth), genome.auth in IMPLEMENTED_AUTH, "JWT, API-key and Basic auth are generated; OAuth2 is not yet a true OAuth2 implementation.")
    add("cors", genome.cors_enabled, genome.cors_enabled, "CORS middleware is generated when selected.")
    add("health_endpoints", genome.health_endpoints, genome.health_endpoints, "The generator emits /health only when selected.")
    add("openapi", bool(genome.openapi_version), bool(genome.openapi_version), "FastAPI provides the OpenAPI document.")
    add("api_version", bool(genome.api_version), bool(genome.api_version), "The selected API version is lowered into route prefixes and metadata.")
    add("rate_limiting", genome.rate_limiting, genome.rate_limiting, "A generated process-local request limiter is emitted when selected.")
    add("metrics_endpoints", genome.metrics_endpoints, genome.metrics_endpoints, "A generated Prometheus-compatible /metrics endpoint is emitted when selected.")
    add("tracing", genome.tracing_enabled, genome.tracing_enabled, "OpenTelemetry ASGI instrumentation, SDK provider and trace-id response propagation are generated when selected.")
    timeout_requested = bool(genome.timeout_config)
    timeout_implemented = timeout_requested and _valid_request_timeout(genome.timeout_config)
    add("timeout_config", timeout_requested, timeout_implemented, "A positive request_timeout is lowered into fail-closed request middleware; connect/read/write values are not independently applicable to the generated inbound-only API.")
    retry_requested = bool(genome.retry_policy)
    retry_implemented = retry_requested and _valid_retry_policy(genome.retry_policy)
    add("retry_policy", retry_requested, retry_implemented, "A bounded exponential retry middleware is lowered for idempotent requests and retries only transient 502/503/504 responses.")
    add("circuit_breaker", genome.circuit_breaker, genome.circuit_breaker, "A generated process-local circuit breaker tracks transient failures, opens after a threshold, supports half-open recovery, and fails fast while open.")
    add("cache", genome.cache_enabled, genome.cache_enabled, "A generated bounded process-local response cache supports GET/HEAD hits, TTL expiry, anonymous-only caching, and mutation invalidation; distributed cache backends remain a separate backend capability.")

    add(
        "middleware",
        bool(genome.middleware),
        bool(genome.middleware) and all(item in SUPPORTED_MIDDLEWARE for item in genome.middleware),
        "The FastAPI lowerer supports the declared middleware vocabulary and rejects unknown middleware instead of silently dropping it.",
    )
    policy_types = {policy.get("type") for policy in genome.security_policies if isinstance(policy, dict)}
    policies_valid = all(policy_type in SUPPORTED_SECURITY_POLICIES for policy_type in policy_types)
    jwt_policy_ok = all(
        policy.get("type") != "jwt_validation" or genome.auth == "jwt"
        for policy in genome.security_policies
        if isinstance(policy, dict)
    )
    rate_policy_ok = all(
        policy.get("type") != "rate_limiting" or genome.rate_limiting
        for policy in genome.security_policies
        if isinstance(policy, dict)
    )
    add(
        "security_policies",
        bool(genome.security_policies),
        bool(genome.security_policies) and policies_valid and jwt_policy_ok and rate_policy_ok,
        "JWT-validation and rate-limiting policy descriptors are enforced by the generated authentication/limiter paths; unknown or inconsistent policies fail closed.",
    )
    add(
        "logging_level",
        bool(genome.logging_level),
        genome.logging_level in SUPPORTED_LOG_LEVELS,
        "Standard-library logging configuration is emitted for DEBUG, INFO, WARNING and ERROR.",
    )
    add(
        "backends",
        bool(genome.backends),
        False,
        "External cache/message-queue backend descriptors remain reserved for a backend that can provide their real runtime semantics; they are never represented as implemented by the local FastAPI cache.",
    )
    return results


def implementation_report(genome: Genome) -> dict[str, Any]:
    results = assess_genome(genome)
    requested = [r for r in results if r.requested]
    implemented = [r for r in requested if r.implemented]
    unmapped = [r for r in requested if not r.implemented]
    return {
        "coverage": round(len(implemented) / len(requested), 3) if requested else 1.0,
        "requested": [r.name for r in requested],
        "implemented": [r.name for r in implemented],
        "unmapped": [r.name for r in unmapped],
        "details": {r.name: {"requested": r.requested, "implemented": r.implemented, "reason": r.reason} for r in results},
    }


def verified_feature(genome: Genome, name: str) -> bool:
    for result in assess_genome(genome):
        if result.name == name:
            return result.requested and result.implemented
    return False
