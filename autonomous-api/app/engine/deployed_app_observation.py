"""Governed runtime observation boundary for Bucket 4.2.

Observations describe what a deployed application is doing. They do not become
requirements automatically and never authorize repository or production writes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import blake2b


class ObservationStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class DriftSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class RuntimeObservation:
    deployment_id: str
    observed_revision: str
    environment_fingerprint: str
    status: ObservationStatus
    health_evidence: tuple[str, ...]
    verification_evidence: tuple[str, ...] = ()
    observed_capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.deployment_id:
            raise ValueError("missing-deployment-id")
        if not self.observed_revision:
            raise ValueError("missing-observed-revision")
        if not self.environment_fingerprint:
            raise ValueError("missing-environment-fingerprint")
        if not self.health_evidence:
            raise ValueError("missing-health-evidence")

    @property
    def evidence_complete(self) -> bool:
        return bool(self.health_evidence and self.verification_evidence)

    @property
    def digest(self) -> str:
        canonical = "|".join((
            self.deployment_id,
            self.observed_revision,
            self.environment_fingerprint,
            self.status.value,
            *self.health_evidence,
            *self.verification_evidence,
            *self.observed_capabilities,
        ))
        return blake2b(canonical.encode(), digest_size=32).hexdigest()


@dataclass(frozen=True)
class RuntimeDrift:
    code: str
    severity: DriftSeverity
    description: str
    evidence_refs: tuple[str, ...]
    authoritative_obligation_id: str | None = None

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("missing-drift-code")
        if not self.description:
            raise ValueError("missing-drift-description")
        if not self.evidence_refs:
            raise ValueError("missing-drift-evidence")


@dataclass(frozen=True)
class DeployedMaintenanceAdmission:
    observation_digest: str
    executable: bool
    reasons: tuple[str, ...]
    authorized_obligation_ids: tuple[str, ...]
    production_write_authorized: bool


def assess_deployed_observation(
    observation: RuntimeObservation,
    *,
    baseline_revision: str,
    baseline_environment_fingerprint: str,
    drifts: tuple[RuntimeDrift, ...] = (),
    authorized_obligation_ids: tuple[str, ...] = (),
    explicit_change_authorization: bool = False,
    production_write_authorized: bool = False,
    deployment_access: bool = False,
) -> DeployedMaintenanceAdmission:
    reasons: list[str] = []

    if not baseline_revision:
        reasons.append("missing-baseline-revision")
    if not baseline_environment_fingerprint:
        reasons.append("missing-baseline-environment")
    if observation.observed_revision != baseline_revision:
        reasons.append("runtime-revision-drift")
    if observation.environment_fingerprint != baseline_environment_fingerprint:
        reasons.append("runtime-environment-drift")

    for drift in drifts:
        if drift.authoritative_obligation_id is None:
            reasons.append(f"advisory-drift:{drift.code}")
        elif drift.authoritative_obligation_id not in authorized_obligation_ids:
            reasons.append(f"drift-obligation-not-authorized:{drift.code}")

    if not explicit_change_authorization:
        reasons.append("explicit-change-authorization-required")

    if production_write_authorized and not deployment_access:
        reasons.append("production-write-requires-deployment-access")

    blocking = tuple(r for r in reasons if not r.startswith("advisory-drift:"))
    executable = not blocking and bool(authorized_obligation_ids)

    if not authorized_obligation_ids:
        reasons.append("no-authorized-obligations")
        executable = False

    return DeployedMaintenanceAdmission(
        observation_digest=observation.digest,
        executable=executable,
        reasons=tuple(sorted(set(reasons))),
        authorized_obligation_ids=tuple(sorted(set(authorized_obligation_ids))),
        production_write_authorized=production_write_authorized,
    )


def require_deployed_maintenance_admission(
    admission: DeployedMaintenanceAdmission,
) -> None:
    if not admission.executable:
        raise ValueError(
            admission.reasons[0]
            if admission.reasons
            else "deployed-maintenance-not-admissible"
        )
