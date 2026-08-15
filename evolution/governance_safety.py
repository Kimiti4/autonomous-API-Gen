"""
Evolutionary safety interlocks.

Safety interlocks verify that an evolved candidate has sufficient evidence
before promotion can be considered.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from .models import utcnow
from .utils import deterministic_id


class SafetyIssue(BaseModel):
    """A safety issue discovered during interlock evaluation."""

    severity: Literal[
        "ERROR",
        "WARNING",
    ]

    code: str
    message: str


class SafetyInterlockPolicy(BaseModel):
    """Policy controlling safety interlocks."""

    require_simulation_passed: bool = True
    require_verification_valid: bool = True
    require_fitness_passed: bool = True

    require_compiler_evidence: bool = False
    require_feedback_evidence: bool = False

    require_pareto_selection: bool = True
    require_rollback_plan: bool = True

    forbid_critical_incidents: bool = True
    forbid_critical_security_findings: bool = True

    allow_breaking_changes: bool = False

    max_complexity: Optional[float] = Field(default=100.0, ge=0.0)

    fail_on_fitness_constraints: bool = True


class EvolutionEvidence(BaseModel):
    """Evidence collected for an evolved candidate."""

    proposal_id: str
    candidate_id: str

    isr_content_hash: str = ""

    simulation_status: Optional[str] = None
    verification_valid: Optional[bool] = None
    fitness_passed: Optional[bool] = None

    objectives: Dict[str, float] = Field(default_factory=dict)
    constraints: Dict[str, bool] = Field(default_factory=dict)

    compiler_passed: Optional[bool] = None
    feedback_passed: Optional[bool] = None

    critical_incident: bool = False
    critical_security_finding: bool = False

    pareto_selected: bool = False

    complexity: Optional[float] = None

    public_api_removed: bool = False
    breaking_changes_allowed: bool = False

    rollback_plan: Optional[Dict[str, Any]] = None


class SafetyInterlockReport(BaseModel):
    """Report produced by safety interlock evaluation."""

    id: str

    proposal_id: str
    candidate_id: str

    passed: bool

    issues: List[SafetyIssue] = Field(default_factory=list)

    error_count: int = 0
    warning_count: int = 0

    created_at: str


class SafetyInterlockEngine:
    """Evaluates safety interlocks for evolved candidates."""

    def evaluate(
        self,
        evidence: EvolutionEvidence,
        policy: Optional[SafetyInterlockPolicy] = None,
    ) -> SafetyInterlockReport:
        policy = policy or SafetyInterlockPolicy()

        issues: List[SafetyIssue] = []

        def error(code: str, message: str) -> None:
            issues.append(
                SafetyIssue(
                    severity="ERROR",
                    code=code,
                    message=message,
                )
            )

        def warning(code: str, message: str) -> None:
            issues.append(
                SafetyIssue(
                    severity="WARNING",
                    code=code,
                    message=message,
                )
            )

        if policy.require_simulation_passed:
            if evidence.simulation_status != "PASSED":
                error(
                    "SIMULATION_NOT_PASSED",
                    "Candidate simulation did not pass.",
                )

        if policy.require_verification_valid:
            if evidence.verification_valid is not True:
                error(
                    "VERIFICATION_NOT_VALID",
                    "Candidate verification is not valid.",
                )

        if policy.require_fitness_passed:
            if evidence.fitness_passed is not True:
                error(
                    "FITNESS_NOT_PASSED",
                    "Candidate fitness evaluation did not pass.",
                )

        if policy.require_compiler_evidence:
            if evidence.compiler_passed is not True:
                error(
                    "COMPILER_EVIDENCE_MISSING",
                    "Compiler-in-the-loop evidence did not pass.",
                )

        if policy.require_feedback_evidence:
            if evidence.feedback_passed is not True:
                error(
                    "FEEDBACK_EVIDENCE_MISSING",
                    "Production feedback evidence did not pass.",
                )

        if policy.require_pareto_selection:
            if not evidence.pareto_selected:
                error(
                    "NOT_PARETO_SELECTED",
                    "Candidate was not selected through Pareto selection.",
                )

        if policy.require_rollback_plan:
            if not evidence.rollback_plan:
                error(
                    "ROLLBACK_PLAN_MISSING",
                    "Candidate does not have a rollback plan.",
                )

        if policy.forbid_critical_incidents:
            if evidence.critical_incident:
                error(
                    "CRITICAL_INCIDENT_PRESENT",
                    "Critical production incident evidence is present.",
                )

        if policy.forbid_critical_security_findings:
            if evidence.critical_security_finding:
                error(
                    "CRITICAL_SECURITY_FINDING_PRESENT",
                    "Critical security finding evidence is present.",
                )

        if evidence.complexity is not None and policy.max_complexity is not None:
            if evidence.complexity > policy.max_complexity:
                error(
                    "COMPLEXITY_LIMIT_EXCEEDED",
                    "Candidate complexity exceeds the configured limit.",
                )

        breaking_allowed = (
            evidence.breaking_changes_allowed
            or policy.allow_breaking_changes
        )

        if not breaking_allowed and evidence.public_api_removed:
            error(
                "PUBLIC_API_REMOVED",
                "Public API removal detected without breaking-change approval.",
            )

        if policy.fail_on_fitness_constraints:
            for constraint_name, constraint_value in evidence.constraints.items():
                if constraint_value is False:
                    error(
                        f"CONSTRAINT_FAILED:{constraint_name}",
                        f"Fitness constraint failed: {constraint_name}",
                    )

        error_count = sum(1 for issue in issues if issue.severity == "ERROR")
        warning_count = sum(1 for issue in issues if issue.severity == "WARNING")

        passed = error_count == 0

        report_id = deterministic_id(
            "safety_interlock_report",
            {
                "proposal_id": evidence.proposal_id,
                "candidate_id": evidence.candidate_id,
                "error_codes": [
                    issue.code
                    for issue in issues
                    if issue.severity == "ERROR"
                ],
                "warning_codes": [
                    issue.code
                    for issue in issues
                    if issue.severity == "WARNING"
                ],
            },
        )

        return SafetyInterlockReport(
            id=report_id,
            proposal_id=evidence.proposal_id,
            candidate_id=evidence.candidate_id,
            passed=passed,
            issues=issues,
            error_count=error_count,
            warning_count=warning_count,
            created_at=utcnow().isoformat(),
        )
