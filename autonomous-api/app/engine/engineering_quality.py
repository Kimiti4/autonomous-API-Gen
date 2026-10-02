"""Engineering quality profiles for frontend, backend and full-stack compilation.

These profiles define obligations and review dimensions, not a fixed implementation
style. Tiannara may invent implementations when the obligations remain satisfied.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class EngineeringDiscipline(str, Enum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    FULLSTACK = "fullstack"


@dataclass(frozen=True)
class QualityObligation:
    obligation_id: str
    area: str
    statement: str
    verification: tuple[str, ...]


@dataclass(frozen=True)
class EngineeringQualityProfile:
    discipline: EngineeringDiscipline
    obligations: tuple[QualityObligation, ...]
    principles: tuple[str, ...]
    freedom_rules: tuple[str, ...]


_COMMON = (
    "Prefer the simplest design that satisfies the real constraints, not the most familiar template.",
    "Make trade-offs explicit and preserve the ability to replace implementation technology.",
    "Treat security, correctness, accessibility/reliability and operability as design inputs.",
    "Prefer evidence over assumptions and reject unverified claims.",
    "Permit experimentation and novel implementation when contract and quality obligations remain satisfied.",
)

_FRONTEND = (
    QualityObligation("FE-ARCH", "architecture", "Clear boundaries between presentation, state, domain behavior and data access.", ("boundary-analysis",)),
    QualityObligation("FE-UX", "experience", "Flows are coherent, resilient and appropriate to user intent, including empty/loading/error states.", ("journey-test",)),
    QualityObligation("FE-A11Y", "accessibility", "Keyboard, semantics, focus, contrast and assistive-technology behavior are designed and verified.", ("accessibility-test",)),
    QualityObligation("FE-STATE", "state", "State ownership, synchronization and cache invalidation are explicit; unnecessary global state is avoided.", ("state-analysis",)),
    QualityObligation("FE-PERF", "performance", "Rendering, network and asset behavior are considered under realistic workload.", ("performance-test",)),
    QualityObligation("FE-SEC", "security", "Trust boundaries, authorization visibility, sensitive data handling and unsafe client assumptions are reviewed.", ("security-review",)),
    QualityObligation("FE-TEST", "verification", "Critical journeys and component behavior are tested at the appropriate level.", ("unit-test", "journey-test")),
    QualityObligation("FE-RES", "resilience", "The UI degrades predictably under network, API and partial-service failures.", ("failure-test",)),
)

_BACKEND = (
    QualityObligation("BE-DOMAIN", "architecture", "Domain behavior is separated from transport and infrastructure concerns.", ("boundary-analysis",)),
    QualityObligation("BE-CONTRACT", "api", "External contracts are explicit, stable and validated against implementation.", ("contract-test",)),
    QualityObligation("BE-DATA", "data", "Persistence, transactions, constraints, migrations and consistency semantics are deliberate.", ("data-test",)),
    QualityObligation("BE-SEC", "security", "Authentication, authorization, input validation, secrets and trust boundaries are explicit.", ("security-test",)),
    QualityObligation("BE-REL", "reliability", "Timeouts, retries, idempotency, failure handling and recovery semantics are designed.", ("failure-test",)),
    QualityObligation("BE-PERF", "performance", "Concurrency, latency, throughput and resource behavior are considered and measured.", ("load-test",)),
    QualityObligation("BE-OBS", "operations", "Logs, metrics, traces, health and diagnosability are part of the service design.", ("observability-test",)),
    QualityObligation("BE-TEST", "verification", "Unit, integration, contract, state and failure tests cover material behavior.", ("test-plan",)),
)

_FULLSTACK = (
    QualityObligation("FS-FLOW", "integration", "Frontend, API, backend, data and operational flows form one coherent system.", ("end-to-end-test",)),
    QualityObligation("FS-CONTRACT", "integration", "Shared contracts prevent drift across layers and clients.", ("cross-layer-contract-test",)),
    QualityObligation("FS-SEC", "security", "Security boundaries remain coherent across browser/client, API, services and persistence.", ("cross-layer-security-test",)),
    QualityObligation("FS-FAIL", "reliability", "Failure behavior remains understandable across asynchronous and synchronous boundaries.", ("failure-injection-test",)),
    QualityObligation("FS-OPERATE", "operations", "The generated system can be observed, diagnosed, tested and evolved after deployment.", ("production-readiness-test",)),
    QualityObligation("FS-EVOLVE", "evolution", "Changes preserve contracts, traceability and backward-compatibility obligations where required.", ("regression-test",)),
)


def quality_profile(discipline: EngineeringDiscipline) -> EngineeringQualityProfile:
    if discipline is EngineeringDiscipline.FRONTEND:
        obligations = _FRONTEND
    elif discipline is EngineeringDiscipline.BACKEND:
        obligations = _BACKEND
    else:
        obligations = _FULLSTACK + _FRONTEND + _BACKEND
    return EngineeringQualityProfile(
        discipline, obligations, _COMMON,
        (
            "Implementation style, framework, language and decomposition may vary.",
            "Multiple valid designs may satisfy the same obligations.",
            "Novel solutions are admissible when their risks and behavior are testable.",
            "Do not optimize for template similarity; optimize for requirements, evidence and system quality.",
        ),
    )


def review_quality(
    discipline: EngineeringDiscipline,
    satisfied_obligations: Iterable[str],
) -> tuple[str, ...]:
    profile = quality_profile(discipline)
    satisfied = set(satisfied_obligations)
    return tuple(
        f"unsatisfied engineering obligation: {o.obligation_id}"
        for o in profile.obligations if o.obligation_id not in satisfied
    )
