"""
Backend capability validation and matching.
"""

from __future__ import annotations

from ..models import (
    BackendCapabilities,
    CapabilityQuery,
    ValidationIssue,
    ValidationReport,
)


CAPABILITY_FIELDS = (
    "supported_targets",
    "languages",
    "frameworks",
    "artifact_types",
    "deployment_targets",
)


def validate_capabilities(capabilities: BackendCapabilities) -> ValidationReport:
    """Validate backend capability declaration."""

    issues: list[ValidationIssue] = []

    has_capability = False

    for field_name in CAPABILITY_FIELDS:
        values = getattr(capabilities, field_name)

        if not isinstance(values, list):
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    code="CAPABILITY_INVALID_TYPE",
                    message=f"Capability field {field_name} must be a list.",
                    path=f"$.capabilities.{field_name}",
                )
            )
            continue

        for index, value in enumerate(values):
            if not isinstance(value, str) or not value.strip():
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        code="CAPABILITY_INVALID_VALUE",
                        message=(
                            f"Capability field {field_name} contains "
                            "an invalid value."
                        ),
                        path=f"$.capabilities.{field_name}[{index}]",
                    )
                )

        if values:
            has_capability = True

    if not has_capability:
        issues.append(
            ValidationIssue(
                severity="ERROR",
                code="CAPABILITY_EMPTY",
                message="Backend must declare at least one capability.",
                path="$.capabilities",
            )
        )

    if not capabilities.maturity:
        issues.append(
            ValidationIssue(
                severity="WARNING",
                code="CAPABILITY_NO_MATURITY",
                message="Backend maturity is not declared.",
                path="$.capabilities.maturity",
            )
        )

    return ValidationReport(
        valid=all(issue.severity != "ERROR" for issue in issues),
        issues=issues,
    )


def capabilities_match(
    capabilities: BackendCapabilities,
    query: CapabilityQuery,
) -> bool:
    """Return true if capabilities satisfy the query."""

    checks: list[tuple[list[str], list[str]]] = [
        (query.supported_targets, capabilities.supported_targets),
        (query.languages, capabilities.languages),
        (query.frameworks, capabilities.frameworks),
        (query.artifact_types, capabilities.artifact_types),
        (query.deployment_targets, capabilities.deployment_targets),
    ]

    for requested, available in checks:
        if not requested:
            continue

        if not set(requested).issubset(set(available)):
            return False

    return True