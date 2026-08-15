"""
Learning safety interlocks.
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List

from ..evolution_integration.models import EvolutionFeedbackBundle
from ..utils import utcnow
from .models import (
    EvidenceQualityReport,
    LearningGovernancePolicy,
    SafetyReport,
)


class LearningSafetyEngine:
    """Evaluates safety controls for learning-driven evolution."""

    def __init__(self, policy: LearningGovernancePolicy) -> None:
        self.policy = policy

        self.submission_events: Dict[str, deque] = {}

    def evaluate(
        self,
        bundle: EvolutionFeedbackBundle,
        quality: EvidenceQualityReport,
        kill_switch_active: bool,
    ) -> SafetyReport:
        blockers: List[str] = []
        warnings: List[str] = []

        required_human_approval = False

        if kill_switch_active:
            blockers.append("kill_switch_active")

        if not quality.passed:
            blockers.append("evidence_quality_failed")

        if quality.poisoning_indicators:
            warnings.extend(quality.poisoning_indicators)

        if bundle.requires_governance:
            required_human_approval = True
            warnings.append("bundle_requires_governance")

        for pressure in bundle.objective_pressures.values():
            if (
                pressure.objective == "security_posture"
                and pressure.severity == "CRITICAL"
                and self.policy.critical_security_requires_approval
            ):
                required_human_approval = True
                warnings.append("critical_security_pressure")

            if (
                pressure.pressure >= self.policy.high_pressure_threshold
                and self.policy.high_pressure_requires_approval
            ):
                required_human_approval = True
                warnings.append("high_operational_pressure")

        if not self._submission_rate_ok(bundle.scope):
            blockers.append("submission_rate_limit_exceeded")

        allowed = len(blockers) == 0

        return SafetyReport(
            bundle_id=bundle.id,
            allowed=allowed,
            required_human_approval=required_human_approval,
            blockers=blockers,
            warnings=warnings,
            kill_switch_active=kill_switch_active,
        )

    def record_submission(self, scope: str) -> None:
        now = utcnow()

        events = self.submission_events.setdefault(scope, deque())

        events.append(now)

        self._prune(scope)

    def _submission_rate_ok(self, scope: str) -> bool:
        self._prune(scope)

        events = self.submission_events.get(scope, deque())

        return len(events) < self.policy.max_submissions_per_hour

    def _prune(self, scope: str) -> None:
        events = self.submission_events.get(scope)

        if not events:
            return

        now = utcnow()

        while events and (now - events[0]).total_seconds() > 3600:
            events.popleft()
