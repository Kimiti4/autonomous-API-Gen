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

    unsupported = {
        "cache": genome.cache_enabled,
        "tracing": genome.tracing_enabled,
        "circuit_breaker": genome.circuit_breaker,
        "retry_policy": bool(genome.retry_policy),
        "timeout_config": bool(genome.timeout_config),
        "backends": bool(genome.backends),
        "middleware": bool(genome.middleware),
        "security_policies": bool(genome.security_policies),
        "logging_level": bool(genome.logging_level),
    }
    reasons = {
        "cache": "No cache implementation is emitted by builder.py.",
        "tracing": "No tracing instrumentation is emitted by builder.py.",
        "circuit_breaker": "No circuit-breaker implementation is emitted by builder.py.",
        "retry_policy": "Retry policy is represented but not lowered into generated request execution.",
        "timeout_config": "Timeout configuration is represented but not lowered into generated request execution.",
        "backends": "Backend descriptors are represented but external cache/queue backends are not generated.",
        "middleware": "Arbitrary middleware selections are represented but not lowered.",
        "security_policies": "Security-policy descriptors are not independently lowered into enforcement code.",
        "logging_level": "Logging level is represented but no generated logging configuration is emitted.",
    }
    for name, requested in unsupported.items():
        add(name, requested, False, reasons[name])
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
