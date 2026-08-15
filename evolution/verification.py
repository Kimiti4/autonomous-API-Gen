"""
Compatibility and constitutional verification engine.
"""

from __future__ import annotations

from typing import Any

from .models import (
    CandidateArchitecture,
    EvolutionProposal,
    SimulationIssue,
    VerificationReport,
    utcnow,
)
from .utils import collect_api_names


class ConstitutionalVerifier:
    """Verifies candidate ISR compatibility and constitutional compliance."""

    def verify(
        self,
        candidate: CandidateArchitecture,
        proposal: EvolutionProposal,
    ) -> VerificationReport:
        issues: list[SimulationIssue] = []

        isr = candidate.isr
        base_isr = proposal.request.base_isr

        required_fields = ("isr_id", "version", "name")

        for field_name in required_fields:
            if not isr.get(field_name):
                issues.append(
                    SimulationIssue(
                        severity="ERROR",
                        code="ISR_MISSING_REQUIRED_FIELD",
                        message=f"ISR is missing required field: {field_name}",
                    )
                )

        if candidate.content_hash == candidate.base_isr_hash:
            issues.append(
                SimulationIssue(
                    severity="ERROR",
                    code="NO_ARCHITECTURAL_CHANGE",
                    message="Candidate ISR is identical to base ISR.",
                )
            )

        evolution_metadata = isr.get("evolution")

        if not evolution_metadata or not evolution_metadata.get("mutations"):
            issues.append(
                SimulationIssue(
                    severity="ERROR",
                    code="MISSING_EVOLUTION_PROVENANCE",
                    message="Candidate ISR does not contain evolution provenance.",
                )
            )

        base_api_names = collect_api_names(base_isr)
        candidate_api_names = collect_api_names(isr)

        removed_apis = base_api_names - candidate_api_names

        if removed_apis:
            severity = (
                "WARNING"
                if proposal.request.allow_breaking_changes
                else "ERROR"
            )

            issues.append(
                SimulationIssue(
                    severity=severity,
                    code="PUBLIC_API_REMOVED",
                    message=(
                        "Public APIs were removed: "
                        + ", ".join(sorted(removed_apis))
                    ),
                )
            )

        valid = all(issue.severity != "ERROR" for issue in issues)

        return VerificationReport(
            candidate_id=candidate.id,
            valid=valid,
            issues=issues,
            created_at=utcnow().isoformat(),
        )
