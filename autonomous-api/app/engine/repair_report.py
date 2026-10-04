"""Machine-verifiable professional repair report for ESAP repository work."""

from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

@dataclass(frozen=True)
class RepairReport:
    schema_version: str
    report_id: str
    target: str
    source_revision: str
    finding_ids: tuple[str, ...]
    root_causes: tuple[dict[str, Any], ...]
    candidates_considered: tuple[dict[str, Any], ...]
    selected_candidate_id: str | None
    patch_digest: str | None
    verification: tuple[dict[str, Any], ...]
    regressions: tuple[dict[str, Any], ...]
    measurements: tuple[dict[str, Any], ...]
    residuals: tuple[str, ...]
    deployment_ready: bool
    human_deployment_authorization_required: bool
    digest: str

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "report_id": self.report_id,
            "target": self.target,
            "source_revision": self.source_revision,
            "finding_ids": list(self.finding_ids),
            "root_causes": list(self.root_causes),
            "candidates_considered": list(self.candidates_considered),
            "selected_candidate_id": self.selected_candidate_id,
            "patch_digest": self.patch_digest,
            "verification": list(self.verification),
            "regressions": list(self.regressions),
            "measurements": list(self.measurements),
            "residuals": list(self.residuals),
            "deployment_ready": self.deployment_ready,
            "human_deployment_authorization_required": self.human_deployment_authorization_required,
        }

    def verify_digest(self) -> bool:
        return self.digest == sha256(
            json.dumps(self.canonical_payload(), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

def build_repair_report(
    *,
    report_id: str,
    target: str,
    source_revision: str,
    finding_ids: tuple[str, ...],
    root_causes: tuple[dict[str, Any], ...],
    candidates_considered: tuple[dict[str, Any], ...],
    selected_candidate_id: str | None,
    patch_digest: str | None,
    verification: tuple[dict[str, Any], ...],
    regressions: tuple[dict[str, Any], ...],
    measurements: tuple[dict[str, Any], ...],
    residuals: tuple[str, ...],
    deployment_ready: bool,
    human_deployment_authorization_required: bool = True,
) -> RepairReport:
    if deployment_ready and selected_candidate_id is None:
        raise ValueError("deployment-ready-report-without-selected-repair")
    if deployment_ready and residuals:
        raise ValueError("deployment-ready-report-has-residuals")
    payload = {
        "schema_version": "esap.repair-report.v1",
        "report_id": report_id,
        "target": target,
        "source_revision": source_revision,
        "finding_ids": list(finding_ids),
        "root_causes": list(root_causes),
        "candidates_considered": list(candidates_considered),
        "selected_candidate_id": selected_candidate_id,
        "patch_digest": patch_digest,
        "verification": list(verification),
        "regressions": list(regressions),
        "measurements": list(measurements),
        "residuals": list(residuals),
        "deployment_ready": deployment_ready,
        "human_deployment_authorization_required": human_deployment_authorization_required,
    }
    digest=sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return RepairReport(**payload,digest=digest)
