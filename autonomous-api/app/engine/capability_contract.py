"""Genome-to-artifact capability contract.

The evolutionary layer must never receive full credit for a capability that the
current generator cannot actually lower into the generated application.

This module is intentionally conservative: a capability is IMPLEMENTED only
when the current builder has a concrete generated-artifact implementation.
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


# Capabilities currently lowered by builder.py. Keep this list explicit rather
# than inferring support from genome field presence.
IMPLEMENTED_AUTH = {"jwt", "api_key", "basic"}


def assess_genome(genome: Genome) -> list[CapabilityResult]:
    results: list[CapabilityResult] = []

    def add(name: str, requested: bool, implemented: bool, reason: str) -> None:
        results.append(CapabilityResult(name, requested, implemented, reason))

    add("services", bool(genome.services), bool(genome.services),
        "Service routers and SQL models are generated for each selected service.")
    add("database", bool(genome.database), genome.database in {"postgres", "mysql", "sqlite"},
        "Database engine generation exists for PostgreSQL, MySQL and SQLite.")
    add("authentication", bool(genome.auth), genome.auth in IMPLEMENTED_AUTH,
        "JWT, API-key and Basic auth are generated; OAuth2 is not yet a true OAuth2 implementation.")
    add("cors", genome.cors_enabled, genome.cors_enabled,
        "CORS middleware is generated when selected.")
    add("health_endpoints", genome.health_endpoints, genome.health_endpoints,
        "The generator emits /health only when the capability is selected.")
    add("openapi", bool(genome.openapi_version), bool(genome.openapi_version),
        "FastAPI generates OpenAPI; the selected version is represented in the generated app.")
    add("api_version", bool(genome.api_version), bool(genome.api_version),
        "The API version is used in generated route prefixes and application metadata.")

    # These fields exist in the genome but are not lowered by the current
    # generator. They are deliberately fail-closed and must not earn fitness.
    unsupported = {
        "cache": genome.cache_enabled,
        "rate_limiting": genome.rate_limiting,
        "metrics_endpoints": genome.metrics_endpoints,
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
        "rate_limiting": "No generated rate limiter is emitted by builder.py.",
        "metrics_endpoints": "No generated metrics endpoint is emitted by builder.py.",
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
    coverage = len(implemented) / len(requested) if requested else 1.0
    return {
        "coverage": round(coverage, 3),
        "requested": [r.name for r in requested],
        "implemented": [r.name for r in implemented],
        "unmapped": [r.name for r in unmapped],
        "details": {r.name: {"requested": r.requested, "implemented": r.implemented, "reason": r.reason} for r in results},
    }


def verified_feature(genome: Genome, name: str) -> bool:
    """Return True only when the requested capability is actually implemented."""
    for result in assess_genome(genome):
        if result.name == name:
            return result.requested and result.implemented
    return False
