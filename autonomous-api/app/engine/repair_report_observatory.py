"""Observable repair-report projection for the ESAP Observatory."""

from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

@dataclass(frozen=True)
class ObservatoryRepairView:
    report_id: str
    target: str
    status: str
    selected_candidate_id: str | None
    finding_count: int
    verification_passed: bool
    regression_free: bool
    deployment_ready: bool
    human_authorization_required: bool
    residuals: tuple[str, ...]
    report_digest: str

def project_repair_report(report: Any) -> ObservatoryRepairView:
    verification=list(report.verification)
    regressions=list(report.regressions)
    passed=all(bool(x.get("passed",False)) for x in verification) if verification else False
    regression_free=not any(bool(x.get("detected",False)) for x in regressions)
    if report.deployment_ready and (not passed or not regression_free or report.residuals):
        raise ValueError("invalid-deployment-ready-repair-report")
    status=("deployment-ready" if report.deployment_ready else
            "blocked" if report.residuals or not passed or not regression_free else "validated")
    return ObservatoryRepairView(
        report.report_id,report.target,status,report.selected_candidate_id,
        len(report.finding_ids),passed,regression_free,report.deployment_ready,
        report.human_deployment_authorization_required,tuple(report.residuals),
        report.digest,
    )

def serialize_observatory_repair_view(view: ObservatoryRepairView) -> str:
    payload={k:getattr(view,k) for k in (
        "report_id","target","status","selected_candidate_id","finding_count",
        "verification_passed","regression_free","deployment_ready",
        "human_authorization_required","residuals","report_digest")}
    payload["residuals"]=list(view.residuals)
    return json.dumps(payload,sort_keys=True,separators=(",",":"))
