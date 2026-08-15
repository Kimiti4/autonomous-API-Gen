"""
Compiler validation framework.

This module validates:
- ISR payloads before compilation
- Backend compilation output after compilation
"""

from __future__ import annotations

from typing import Any

from .models import CompilationOutput, ValidationIssue, ValidationReport


def validate_isr_payload(isr: dict[str, Any]) -> ValidationReport:
    """
    Validate a minimal ISR compilation payload.

    The full ISR schema should be enforced by the ISR subsystem.
    The compiler performs defensive pre-compilation validation.
    """

    issues: list[ValidationIssue] = []

    if not isinstance(isr, dict):
        issues.append(
            ValidationIssue(
                severity="ERROR",
                code="ISR_NOT_OBJECT",
                message="ISR payload must be an object.",
                path="$",
            )
        )

        return ValidationReport(valid=False, issues=issues)

    required_fields = {
        "isr_id": str,
        "version": str,
        "name": str,
    }

    for field_name, field_type in required_fields.items():
        value = isr.get(field_name)

        if value is None:
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    code="ISR_MISSING_FIELD",
                    message=f"ISR payload is missing required field: {field_name}",
                    path=f"$.{field_name}",
                )
            )
            continue

        if not isinstance(value, field_type):
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    code="ISR_INVALID_FIELD_TYPE",
                    message=f"ISR field {field_name} must be {field_type.__name__}.",
                    path=f"$.{field_name}",
                )
            )

    domains = isr.get("domains")

    if domains is not None and not isinstance(domains, list):
        issues.append(
            ValidationIssue(
                severity="ERROR",
                code="ISR_INVALID_DOMAINS",
                message="ISR domains must be a list.",
                path="$.domains",
            )
        )

    services = isr.get("services")

    if services is not None and not isinstance(services, list):
        issues.append(
            ValidationIssue(
                severity="ERROR",
                code="ISR_INVALID_SERVICES",
                message="ISR services must be a list.",
                path="$.services",
            )
        )

    apis = isr.get("apis")

    if apis is not None and not isinstance(apis, list):
        issues.append(
            ValidationIssue(
                severity="ERROR",
                code="ISR_INVALID_APIS",
                message="ISR APIs must be a list.",
                path="$.apis",
            )
        )

    return ValidationReport(
        valid=len(issues) == 0,
        issues=issues,
    )


def validate_compilation_output(output: CompilationOutput) -> ValidationReport:
    """Validate output returned by a compiler backend."""

    issues: list[ValidationIssue] = []

    if not output.artifacts:
        issues.append(
            ValidationIssue(
                severity="ERROR",
                code="NO_ARTIFACTS",
                message="Backend produced no artifacts.",
                path="$.artifacts",
            )
        )

    for index, artifact in enumerate(output.artifacts):
        artifact_path = f"$.artifacts[{index}].path"

        if not artifact.path:
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    code="ARTIFACT_MISSING_PATH",
                    message="Artifact path is required.",
                    path=artifact_path,
                )
            )
            continue

        if ".." in artifact.path:
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    code="ARTIFACT_UNSAFE_PATH",
                    message="Artifact path must not contain parent traversal.",
                    path=artifact_path,
                )
            )

        if artifact.path == "artifact-manifest.json":
            issues.append(
                ValidationIssue(
                    severity="ERROR",
                    code="ARTIFACT_RESERVED_PATH",
                    message="artifact-manifest.json is reserved for the packager.",
                    path=artifact_path,
                )
            )

    return ValidationReport(
        valid=len(issues) == 0,
        issues=issues,
    )