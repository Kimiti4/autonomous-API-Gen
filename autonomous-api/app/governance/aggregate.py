"""CandidateGovernanceRecord aggregate — the fold of a candidate's
governance event log. Pure; no storage or framework imports.

Temporal model: state at any point is the fold up to that event index.
"""
from __future__ import annotations

from typing import Optional

from app.core.contracts.governance import (
    Certification,
    GateOutcome,
    GovernanceDecision,
    LifecycleState,
)


class CandidateGovernanceState:
    """Materialized per-candidate governance record."""

    __slots__ = (
        "candidate_id", "current_state", "decisions",
        "gate_outcomes", "certifications",
    )

    def __init__(self, candidate_id: str) -> None:
        self.candidate_id = candidate_id
        self.current_state: LifecycleState = "proposed"
        self.decisions: list[GovernanceDecision] = []
        self.gate_outcomes: list[GateOutcome] = []
        self.certifications: list[Certification] = []

    # ---- fold -----------------------------------------------------------

    def apply(self, event) -> None:
        name = type(event).__name__
        if name == "GovernanceDecisionMade":
            d = event.decision
            self.decisions.append(d)
            if d.verdict == "approve" and d.authorizesTransition:
                self.current_state = d.toState
        elif name == "GateEvaluated":
            self.gate_outcomes.append(event.outcome)
        elif name == "CertificationGranted":
            self.certifications.append(event.certification)
        elif name == "CertificationRevoked":
            for cert in self.certifications:
                if cert.certificationId == event.certificationId:
                    self.certifications[self.certifications.index(cert)] = (
                        cert.model_copy(
                            update={
                                "revokedAt": event.revokedAt,
                                "revokedBy": event.revokedBy,
                            }
                        )
                    )

    @classmethod
    def fold(cls, candidate_id: str, events: list) -> "CandidateGovernanceState":
        state = cls(candidate_id)
        for event in events:
            state.apply(event)
        return state

    # ---- queries ---------------------------------------------------------

    def latest_decision(self) -> Optional[GovernanceDecision]:
        return self.decisions[-1] if self.decisions else None

    def active_certifications(self) -> list[Certification]:
        return [c for c in self.certifications if c.revokedAt is None]

    def gate_status(self, gate_id: str) -> Optional[str]:
        for outcome in reversed(self.gate_outcomes):
            if outcome.gateId == gate_id:
                return outcome.status
        return None


def fold_generation(events_by_candidate: dict) -> list:
    """Fold every candidate's log into states; returns list of states."""
    return [
        CandidateGovernanceState.fold(cid, events)
        for cid, events in sorted(events_by_candidate.items())
    ]