"""Governed maintenance hand-off from a verified repair report.

This adapter records evidence from the existing repair-report pipeline. It does not
execute mutations, write repositories, or deploy applications.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from constitutional_architecture.governance.trusted_evidence_resolution import (  # noqa: E402
    EvidenceBinding,
    GovernedTrustedEvidenceService,
    TrustBoundary,
)

from .deployed_app_observation import (
    DeployedMaintenanceAdmission,
    RuntimeObservation,
)
from certification.orchestration.implir_ingress_guard import (  # noqa: E402
    IsrIngressAuthority,
    assert_trusted_maintenance_ingress,
)

from .governed_maintenance_record import (
    GovernedMaintenanceRecord,
    validate_maintenance_record,
)


@dataclass(frozen=True)
class GovernedMaintenanceEvent:
    event_type: str
    status: str
    observation_digest: str
    obligation_id: str
    patch_digest: str
    repair_report_digest: str
    evidence: tuple[str, ...]
    digest: str


def _normalized_evidence_refs(item: dict[str, Any]) -> tuple[str, ...]:
    refs = item.get("evidence_refs", item.get("evidence_ref", item.get("evidence")))
    if isinstance(refs, str):
        refs = (refs,)
    if not isinstance(refs, (tuple, list)):
        return ()
    return tuple(str(r).strip() for r in refs if isinstance(r, str) and str(r).strip())


def record_verified_maintenance(
    observation: RuntimeObservation,
    admission: DeployedMaintenanceAdmission,
    *,
    obligation_id: str,
    authorization_ref: str,
    repair_report: Any,
    production_write_requested: bool = False,
    trust_boundary: TrustBoundary = TrustBoundary.PRODUCTION,
    evidence_service: GovernedTrustedEvidenceService | None = None,
    trusted_candidate_id: str | None = None,
    require_runtime_evidence: bool = True,
    artifact_sha256: str = "",
    ingress_authority: str = IsrIngressAuthority.ISR_REVISION.value,
) -> tuple[GovernedMaintenanceRecord, GovernedMaintenanceEvent]:
    """Create a maintenance record only from a valid, passing repair report."""
    if not admission.executable:
        raise ValueError("maintenance-admission-not-executable")
    if observation.digest != admission.observation_digest:
        raise ValueError("observation-digest-mismatch")
    if not callable(getattr(repair_report, "verify_digest", None)) or not repair_report.verify_digest():
        raise ValueError("repair-report-digest-invalid")
    if not repair_report.patch_digest or not str(repair_report.patch_digest).strip():
        raise ValueError("repair-report-missing-patch-digest")
    if repair_report.source_revision != observation.observed_revision:
        raise ValueError("repair-report-source-revision-mismatch")
    assert_trusted_maintenance_ingress(
        ingress_authority,
        governed_lineage_ref=str(repair_report.source_revision),
        production_write_requested=production_write_requested,
    )
    if not repair_report.verification:
        raise ValueError("repair-report-verification-missing")
    if any(not isinstance(item, dict) or item.get("passed") is not True for item in repair_report.verification):
        raise ValueError("repair-report-verification-failed")
    if not repair_report.regressions:
        raise ValueError("repair-report-regression-evidence-missing")
    if any(
        not isinstance(item, dict) or not isinstance(item.get("detected"), bool)
        for item in repair_report.regressions
    ):
        raise ValueError("repair-report-regression-evidence-malformed")
    if any(item["detected"] for item in repair_report.regressions):
        raise ValueError("repair-report-regression-detected")
    for item in repair_report.regressions:
        refs = item.get("evidence_refs", item.get("evidence_ref", item.get("evidence")))
        if isinstance(refs, str):
            refs = (refs,)
        if not isinstance(refs, (tuple, list)) or not refs or any(
            not isinstance(ref, str) or not ref.strip() for ref in refs
        ):
            raise ValueError("repair-report-regression-evidence-reference-missing")
    if repair_report.residuals:
        raise ValueError("repair-report-has-residuals")

    if trust_boundary is TrustBoundary.PRODUCTION:
        service = evidence_service or GovernedTrustedEvidenceService.require_for_boundary(
            TrustBoundary.PRODUCTION,
        )
        if service is None:
            raise ValueError("trusted-evidence-service-required")
        cand = (trusted_candidate_id or repair_report.selected_candidate_id or "").strip()
        if not cand:
            raise ValueError("trusted-evidence-candidate-required")
        binding = EvidenceBinding(
            candidate_id=cand,
            artifact_sha256=str(artifact_sha256 or "").strip(),
            source_revision=str(repair_report.source_revision or "").strip(),
        )
        all_refs: list[str] = []
        for item in repair_report.verification:
            ref_tuple = _normalized_evidence_refs(item)
            if not ref_tuple:
                raise ValueError("repair-report-verification-evidence-missing")
            all_refs.extend(ref_tuple)
        for item in repair_report.regressions:
            ref_tuple = _normalized_evidence_refs(item)
            if not ref_tuple:
                raise ValueError("repair-report-regression-evidence-reference-missing")
            all_refs.extend(ref_tuple)
        service.resolve_evidence(
            all_refs,
            binding=binding,
            require_runtime=require_runtime_evidence,
        )

    evidence: list[str] = []
    for index, item in enumerate(repair_report.verification):
        refs = item.get("evidence_refs", item.get("evidence_ref", item.get("evidence")))
        if isinstance(refs, str):
            refs = (refs,)
        if not isinstance(refs, (tuple, list)) or not refs or any(
            not isinstance(ref, str) or not ref.strip() for ref in refs
        ):
            raise ValueError("repair-report-verification-evidence-missing")
        evidence.extend(f"verification:{index}:{ref.strip()}" for ref in refs)

    record = GovernedMaintenanceRecord(
        observation_digest=observation.digest,
        obligation_id=obligation_id,
        patch_digest=str(repair_report.patch_digest),
        verification_evidence=tuple(evidence),
        authorization_ref=authorization_ref,
        production_write_requested=production_write_requested,
    )
    validate_maintenance_record(record, admission)

    payload = {
        "event_type": "governed-maintenance-recorded",
        "status": "verified",
        "observation_digest": record.observation_digest,
        "obligation_id": record.obligation_id,
        "patch_digest": record.patch_digest,
        "repair_report_digest": repair_report.digest,
        "evidence": list(record.verification_evidence),
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    event = GovernedMaintenanceEvent(
        event_type=payload["event_type"],
        status=payload["status"],
        observation_digest=record.observation_digest,
        obligation_id=record.obligation_id,
        patch_digest=record.patch_digest,
        repair_report_digest=repair_report.digest,
        evidence=record.verification_evidence,
        digest=digest,
    )
    return record, event
