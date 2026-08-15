"""
Pass 1: Requirements Validation.

Constitutional Role:
- Ensures raw input is complete enough for Pass 2 analysis.
- Detects ambiguity, contradictions, and missing information.
- Scans for forbidden technology terms (Constitutional gate).
- Does NOT interpret meaning. Only validates structure and completeness.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from constitutional_architecture.core.constitution import FORBIDDEN_LEXICON
from constitutional_architecture.core.models.intent import sanitize_forbidden_terms


REQUIRED_SECTIONS = ["problem_description", "target_users", "core_capabilities"]

AMBIGUITY_MARKERS = ["maybe", "possibly", "something like", "not sure", "etc", "and stuff"]

MIN_PROBLEM_LENGTH = 10


@dataclass
class ValidationIssue:
    severity: str  # "error" | "warning" | "info"
    field: str
    message: str
    suggestion: str = ""


@dataclass
class ValidatedRequirement:
    requirement_id: str
    raw_input: str
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    extracted_sections: Dict[str, str] = field(default_factory=dict)
    sanitized_input: str = ""


class RequirementsValidator:
    """Pass 1: Validates raw requirement input for completeness.

    Does NOT produce an IntentModel. Only gates entry to Pass 2.
    """

    def validate(self, requirement_id: str, raw_input: str) -> ValidatedRequirement:
        issues: List[ValidationIssue] = []

        if not raw_input or not raw_input.strip():
            return ValidatedRequirement(
                requirement_id=requirement_id,
                raw_input=raw_input,
                is_valid=False,
                issues=[ValidationIssue(severity="error", field="input", message="Raw input is empty")],
            )

        extracted = self._extract_sections(raw_input)

        word_count = len(raw_input.split())
        if word_count < MIN_PROBLEM_LENGTH:
            issues.append(ValidationIssue(
                severity="warning", field="problem_statement",
                message=f"Input is short ({word_count} words, minimum {MIN_PROBLEM_LENGTH})",
                suggestion="Provide more detail about the problem you are solving.",
            ))

        lower = raw_input.lower()
        for marker in AMBIGUITY_MARKERS:
            if marker in lower:
                issues.append(ValidationIssue(
                    severity="warning", field="clarity",
                    message=f"Ambiguous language detected: '{marker}'",
                    suggestion="Replace with specific, measurable statements.",
                ))

        for term in FORBIDDEN_LEXICON:
            if re.search(rf'\b{re.escape(term)}\b', lower):
                issues.append(ValidationIssue(
                    severity="info", field="technology_neutrality",
                    message=f"Technology reference detected: '{term}'",
                    suggestion="Intent should describe capabilities, not implementations.",
                ))

        sanitized = sanitize_forbidden_terms(raw_input)
        has_errors = any(i.severity == "error" for i in issues)

        return ValidatedRequirement(
            requirement_id=requirement_id,
            raw_input=raw_input,
            is_valid=not has_errors,
            issues=issues,
            extracted_sections=extracted,
            sanitized_input=sanitized,
        )

    def _extract_sections(self, raw_input: str) -> Dict[str, str]:
        """Deterministic section extraction. Advisory only — does not gate validation."""
        sections: Dict[str, str] = {}
        if not raw_input or not raw_input.strip():
            return sections

        lower = raw_input.lower()

        # Every non-empty input gets a problem description
        sections["problem_description"] = raw_input

        if any(kw in lower for kw in ["user", "customer", "admin", "persona", "buyer", "seller", "developer"]):
            sections["target_users"] = raw_input
        if any(kw in lower for kw in ["feature", "capability", "should", "must", "support", "manage", "track", "report"]):
            sections["core_capabilities"] = raw_input

        return sections
