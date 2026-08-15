"""
Evolution Engine gateway.
"""

from __future__ import annotations

from typing import Dict, Protocol

from ..utils import deterministic_id, utcnow
from .models import EvolutionFeedbackBundle, EvolutionSubmissionResult


class EvolutionGateway(Protocol):
    """Abstract gateway to the Evolution Engine."""

    def submit_feedback(
        self,
        bundle: EvolutionFeedbackBundle,
    ) -> EvolutionSubmissionResult:
        ...


class InMemoryEvolutionGateway:
    """In-memory gateway for tests and local development."""

    def __init__(self) -> None:
        self.submissions: Dict[str, EvolutionSubmissionResult] = {}

    def submit_feedback(
        self,
        bundle: EvolutionFeedbackBundle,
    ) -> EvolutionSubmissionResult:
        submission_id = deterministic_id(
            "evolution_submission",
            {
                "bundle_id": bundle.id,
                "scope": bundle.scope,
            },
        )

        if bundle.requires_governance:
            status = "PENDING_GOVERNANCE"
            reason = "Feedback bundle requires governance review."
        else:
            status = "ACCEPTED"
            reason = "Feedback bundle accepted for evolution consideration."

        result = EvolutionSubmissionResult(
            submission_id=submission_id,
            status=status,
            reason=reason,
            submitted_at=utcnow().isoformat(),
        )

        self.submissions[submission_id] = result

        return result
