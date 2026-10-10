"""Evidence linkage for a governed deployed-app maintenance action.

This module validates a record only; it does not apply patches, write repositories,
or deploy applications.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.engine.deployed_app_observation import DeployedMaintenanceAdmission


@dataclass(frozen=True)
class GovernedMaintenanceRecord:
    observation_digest: str
    obligation_id: str
    patch_digest: str
    verification_evidence: tuple[str, ...]
    authorization_ref: str
    production_write_requested: bool = False


def validate_maintenance_record(
    record: GovernedMaintenanceRecord,
    admission: DeployedMaintenanceAdmission,
) -> None:
    """Fail closed unless the proposed action is traceable to admitted authority."""
    if not admission.executable:
        raise ValueError("maintenance-admission-not-executable")
    if not record.observation_digest:
        raise ValueError("missing-observation-digest")
    if record.observation_digest != admission.observation_digest:
        raise ValueError("observation-digest-mismatch")
    if not record.obligation_id:
        raise ValueError("missing-obligation-id")
    if record.obligation_id not in admission.authorized_obligation_ids:
        raise ValueError("obligation-not-authorized")
    if not record.patch_digest:
        raise ValueError("missing-patch-digest")
    if not record.verification_evidence or any(not item.strip() for item in record.verification_evidence):
        raise ValueError("missing-verification-evidence")
    if not record.authorization_ref.strip():
        raise ValueError("missing-authorization-reference")
    if record.production_write_requested and not admission.production_write_authorized:
        raise ValueError("production-write-not-authorized")
