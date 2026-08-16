"""R2.10.3-D — reliability & resilience primitive (required behavior under failure).

The strictest boundary yet: reliability must express WHAT must remain true
when the system encounters failure, and be STRUCTURALLY incapable of
expressing HOW a technology achieves it. Retry counts, backoff strategies,
replica counts, restart policies, probes, queue names, and replication
commands are compiler/backend/deployment realizations — never ISR semantics.

The construct declares:
  * failure modes that matter (WHAT fails, never how it is handled)
  * required recovery behavior (WHAT must happen; a backend may realize
    EVENTUAL_RECOVERY by retry, queue replay, supervisor restart, or replica
    failover, provided the declared contract holds)
  * degradation policy (acceptable service STATE under failure)
  * preservation invariants (what must hold during degraded operation)
  * dependency constraints (semantic coupling declarations)
  * recovery deadlines as semantic durations — composing with the temporal
    primitive's duration semantics without embedding timer machinery in
    either primitive (the failure -> degraded -> recovery deadline ->
    restored sequence remains expressible via temporal EVENT_ORDERING)

Targets are explicit ISR identities (capabilities, modules, services) —
never inferred modules.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import TYPE_CHECKING, Any, Optional

from constitutional_architecture.isr.semantics.projection import canonical_form, canonicalize

if TYPE_CHECKING:
    from constitutional_architecture.isr.model.isr import ISR


class ReliabilityValidationError(ValueError):
    """A reliability requirement violates its construction or structural contract."""


@unique
class FailureMode(str, Enum):
    """WHAT fails. Never how it is handled."""

    TRANSIENT_DEPENDENCY_FAILURE = "TRANSIENT_DEPENDENCY_FAILURE"
    PERMANENT_DEPENDENCY_FAILURE = "PERMANENT_DEPENDENCY_FAILURE"
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"
    PARTIAL_CAPACITY_LOSS = "PARTIAL_CAPACITY_LOSS"
    DATA_INTEGRITY_VIOLATION = "DATA_INTEGRITY_VIOLATION"
    CASCADE_FAILURE = "CASCADE_FAILURE"


@unique
class RecoveryBehavior(str, Enum):
    """WHAT must happen. Never the mechanism. A backend may realize
    EVENTUAL_RECOVERY by retry, queue replay, or failover, so long as the
    declared contract holds."""

    EVENTUAL_RECOVERY = "EVENTUAL_RECOVERY"
    IMMEDIATE_FAILOVER = "IMMEDIATE_FAILOVER"
    GRACEFUL_DEGRADATION = "GRACEFUL_DEGRADATION"
    CONTROLLED_SHUTDOWN = "CONTROLLED_SHUTDOWN"


@unique
class DegradationPolicy(str, Enum):
    """Acceptable service STATE under failure — semantic, not mechanism."""

    NO_DEGRADATION = "NO_DEGRADATION"
    PARTIAL_SERVICE = "PARTIAL_SERVICE"
    READ_ONLY_SERVICE = "READ_ONLY_SERVICE"
    DEGRADED_THROUGHPUT = "DEGRADED_THROUGHPUT"


@dataclass(frozen=True)
class RecoveryObjective:
    """Required behavior + semantic deadline for one failure mode.

    ``max_recovery_duration_ms`` is a semantic duration sharing the temporal
    primitive's duration semantics; neither primitive carries timer machinery.
    ``max_data_loss_tolerance`` is a free-form semantic declaration (e.g.
    "none", "5 minutes of writes") — never a storage command.
    """

    failure_mode: FailureMode
    required_behavior: RecoveryBehavior
    max_recovery_duration_ms: Optional[int] = None
    max_data_loss_tolerance: Optional[str] = None

    def __post_init__(self) -> None:
        if (
            self.max_recovery_duration_ms is not None
            and self.max_recovery_duration_ms < 0
        ):
            raise ReliabilityValidationError(
                "recovery duration must be non-negative"
            )


@dataclass(frozen=True)
class ReliabilityRequirement:
    """Required system behavior under failure. Semantic intent only.

    No retry counts, no backoff strategies, no replica counts, no restart
    policies, no probes, no queue names, no replication commands. Those are
    compiler/backend/deployment realizations of the contract declared here.

    ``target_refs`` name explicit ISR identities (business capabilities,
    modules, services) that the requirement protects; ``failure_modes`` name
    WHAT the requirement guards against; ``preservation_invariants`` declare
    what must remain true during degraded operation; ``dependency_constraints``
    declare semantic coupling (e.g. "recovery of X must precede recovery of Y").
    """

    requirement_id: str
    target_refs: tuple[str, ...]  # protected components/capabilities (by id)
    failure_modes: tuple[FailureMode, ...]  # what must survive
    recovery_objectives: tuple[RecoveryObjective, ...] = ()
    degradation_policy: Optional[DegradationPolicy] = None
    preservation_invariants: tuple[str, ...] = ()  # hold during degradation
    dependency_constraints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.requirement_id:
            raise ReliabilityValidationError("requirement_id is required")
        if not self.target_refs:
            raise ReliabilityValidationError(
                "target_refs required: reliability must protect something explicit"
            )
        if not self.failure_modes:
            raise ReliabilityValidationError(
                "failure_modes required: reliability must name what it guards against"
            )


# -- mechanism lint (the dangerous boundary) ---------------------------------

RELIABILITY_MECHANISM_TERMS: frozenset[str] = frozenset({
    # orchestration / process mechanisms
    "kubernetes", "k8s", "docker", "systemd", "supervisor", "restart_policy",
    # retry/backoff mechanisms (NOT the semantic recovery behavior)
    "retry_count", "max_retries", "backoff", "exponential_backoff",
    # resilience patterns as implementation classes
    "circuit_breaker", "bulkhead",
    # replication / failover mechanisms
    "replica_count", "replication_config", "failover_config",
    # probes / queue / db mechanisms
    "liveness_probe", "readiness_probe", "queue_name", "database_replica",
})


def reliability_mechanism_hits(
    requirement: ReliabilityRequirement,
) -> tuple[str, ...]:
    """Which mechanism terms (if any) leaked into a requirement's semantic form.

    The terms collide with MECHANISMS, not semantic behaviors: ``failover_config``
    is rejected while ``IMMEDIATE_FAILOVER`` (a behavior) is fine; ``retry_count``
    is rejected while ``EVENTUAL_RECOVERY`` is fine. That asymmetry is the point.
    """
    lowered = canonicalize(requirement).lower()
    return tuple(term for term in RELIABILITY_MECHANISM_TERMS if term in lowered)


def assert_reliability_technology_agnostic(
    requirement: ReliabilityRequirement,
) -> None:
    """Gate: no implementation mechanism may leak into the semantic representation."""
    hits = reliability_mechanism_hits(requirement)
    if hits:
        raise ReliabilityValidationError(
            f"reliability '{requirement.requirement_id}' couples to "
            f"mechanism(s): {hits}"
        )


# -- structural validation (pre-execution) -----------------------------------

def _target_ids(system: Any) -> set[str]:
    """Explicit ISR identities a requirement may protect.

    Business capabilities (R2.10.3-B), modules, and services. Reliability
    targets are always declared identities — never inferred modules.
    """
    ids = {capability.capability_id for capability in system.business_capabilities}
    for module in system.modules:
        ids.add(module.id)
        ids.update(service.id for service in module.services)
    return ids


def validate_system_reliability_constraints(system: Any) -> tuple[str, ...]:
    """Structural validation for one system's reliability requirements.

    Rejects, pre-execution: duplicate requirement ids, dangling target refs
    (must name an existing capability/module/service), recovery objectives
    addressing failure modes the requirement does not declare, and
    contradictory recovery requirements (the same failure mode demanding
    two different required behaviors). Empty tuple means valid.
    """
    errors: list[str] = []
    target_ids = _target_ids(system)
    seen: set[str] = set()
    for requirement in system.reliability_requirements:
        if requirement.requirement_id in seen:
            errors.append(
                f"duplicate reliability requirement id '{requirement.requirement_id}'"
            )
        seen.add(requirement.requirement_id)
        for target_ref in requirement.target_refs:
            if target_ref not in target_ids:
                errors.append(
                    f"reliability requirement '{requirement.requirement_id}' "
                    f"targets unknown identity '{target_ref}'"
                )
        declared = set(requirement.failure_modes)
        behavior_by_mode: dict[FailureMode, RecoveryBehavior] = {}
        for objective in requirement.recovery_objectives:
            if objective.failure_mode not in declared:
                errors.append(
                    f"reliability requirement '{requirement.requirement_id}' "
                    f"recovery objective addresses undeclared failure mode "
                    f"'{objective.failure_mode.value}'"
                )
            if objective.failure_mode in behavior_by_mode:
                if behavior_by_mode[objective.failure_mode] != objective.required_behavior:
                    errors.append(
                        f"reliability requirement '{requirement.requirement_id}' "
                        f"demands contradictory recovery for failure mode "
                        f"'{objective.failure_mode.value}'"
                    )
            else:
                behavior_by_mode[objective.failure_mode] = objective.required_behavior
    return tuple(errors)


# -- projection (semantics only) ---------------------------------------------

def project_reliability_requirements(isr: Any) -> tuple[dict[str, Any], ...]:
    """Backend-independent semantic projection of reliability requirements.

    Returns required behavior under failure (failure modes, recovery
    objectives, degradation policy, preservation invariants, dependency
    constraints). Never Kubernetes manifests, retry policies, replica
    counts, or probe configs — those are compiler-backend realizations of
    the contract declared here.
    """
    return tuple(
        canonical_form(requirement)
        for requirement in getattr(isr.system, "reliability_requirements", ())
    )