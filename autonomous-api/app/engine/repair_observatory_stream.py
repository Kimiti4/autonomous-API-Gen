"""Observable repair-report stream contract for the ESAP Observatory."""

from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

@dataclass(frozen=True)
class RepairObservatoryEvent:
    event_type: str
    sequence: int
    report_id: str
    status: str
    payload: dict[str, Any]
    digest: str

def build_repair_observatory_event(report_view: Any, *, sequence: int) -> RepairObservatoryEvent:
    if sequence < 0:
        raise ValueError("invalid-observatory-sequence")
    payload={
        "report_id":report_view.report_id,
        "target":report_view.target,
        "status":report_view.status,
        "selected_candidate_id":report_view.selected_candidate_id,
        "finding_count":report_view.finding_count,
        "verification_passed":report_view.verification_passed,
        "regression_free":report_view.regression_free,
        "deployment_ready":report_view.deployment_ready,
        "human_authorization_required":report_view.human_authorization_required,
        "residuals":list(report_view.residuals),
        "report_digest":report_view.report_digest,
    }
    canonical=json.dumps(payload,sort_keys=True,separators=(",",":"))
    digest=sha256(f"repair-report|{sequence}|{canonical}".encode()).hexdigest()
    return RepairObservatoryEvent("repair-report",sequence,report_view.report_id,
        report_view.status,payload,digest)

def serialize_repair_observatory_event(event: RepairObservatoryEvent) -> str:
    return json.dumps({
        "event_type":event.event_type,"sequence":event.sequence,
        "report_id":event.report_id,"status":event.status,
        "payload":event.payload,"digest":event.digest,
    },sort_keys=True,separators=(",",":"))
