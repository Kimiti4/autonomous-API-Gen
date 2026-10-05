"""Bucket 3.12 — final governed integration boundary for ESAP.

This module composes the independent Bucket 3 governance decisions into one
fail-closed admission result. It never performs mutations or certification.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Literal

Decision = Literal["ADMIT", "STOP", "REJECT"]


@dataclass(frozen=True)
class IntegrationDecision:
    decision: Decision
    reasons: tuple[str, ...]
    scope_class: str
    impact_bounded: bool
    consistency_ok: bool
    nfr_admissible: bool
    completion_complete: bool
    digest: str

    @property
    def executable(self) -> bool:
        return self.decision == "ADMIT"


class Bucket3IntegrationEngine:
    """Final governance boundary over scope, impact, consistency, NFR and completion."""

    def __init__(self, *, project_id: str) -> None:
        if not project_id.strip():
            raise ValueError("project-id-required")
        self.project_id = project_id

    def evaluate_change(
        self,
        *,
        scope_decision,
        impact_plan,
        consistency_report,
        nfr_assessment,
        completion_state,
    ) -> IntegrationDecision:
        reasons: list[str] = []

        scope_ok = scope_decision.executable
        impact_ok = impact_plan.bounded
        consistency_ok = consistency_report.consistent
        nfr_ok = nfr_assessment.admissible
        complete = completion_state.complete

        if complete:
            reasons.append("project-already-complete")
        if not scope_ok:
            reasons.append("scope-not-executable")
        if not impact_ok:
            reasons.append("mutation-impact-unbounded")
        if not consistency_ok:
            reasons.append("cross-layer-inconsistency")
        if not nfr_ok:
            reasons.append("nfr-admission-failed")

        # Completion is a stop boundary. Even an explicitly authorized new
        # proposal must first create a governed reopened obligation.
        if complete:
            decision: Decision = "STOP"
        elif all((scope_ok, impact_ok, consistency_ok, nfr_ok)):
            decision = "ADMIT"
        else:
            decision = "REJECT"

        payload = {
            "schema_version": "esap.bucket3-integration.v1",
            "project_id": self.project_id,
            "decision": decision,
            "reasons": tuple(reasons),
            "scope_class": scope_decision.classification,
            "impact_bounded": impact_ok,
            "consistency_ok": consistency_ok,
            "nfr_admissible": nfr_ok,
            "completion_complete": complete,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

        return IntegrationDecision(
            decision=decision,
            reasons=tuple(reasons),
            scope_class=scope_decision.classification,
            impact_bounded=impact_ok,
            consistency_ok=consistency_ok,
            nfr_admissible=nfr_ok,
            completion_complete=complete,
            digest=digest,
        )

    def evaluate_completion(self, completion_state) -> IntegrationDecision:
        complete = completion_state.complete
        decision: Decision = "STOP" if complete else "REJECT"
        reasons = ("all-governed-obligations-certified",) if complete else (
            "governed-obligations-remain",
        )
        payload = {
            "schema_version": "esap.bucket3-integration.v1",
            "project_id": self.project_id,
            "decision": decision,
            "reasons": reasons,
            "completion_complete": complete,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return IntegrationDecision(
            decision=decision,
            reasons=reasons,
            scope_class="none",
            impact_bounded=True,
            consistency_ok=True,
            nfr_admissible=True,
            completion_complete=complete,
            digest=digest,
        )
