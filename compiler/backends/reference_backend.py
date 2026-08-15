"""
Reference compiler backend.

This backend does not generate a full production framework implementation.

It provides a real, testable reference backend that compiles ISR into
technology-neutral documentation and compilation manifests.

Production backends such as FastAPI, Spring Boot, Terraform, Kubernetes,
React, or Go Fiber should implement the same backend contract.
"""

from __future__ import annotations

from typing import Any

from ..models import (
    BackendCapabilities,
    BackendManifest,
    CompilationContext,
    CompilationOutput,
    ValidationReport,
)
from ..sdk.base import CompilerBackendBase
from ..sdk.artifacts import CompilationOutputBuilder


class ReferenceBackend(CompilerBackendBase):
    """Technology-neutral reference compiler backend."""

    def __init__(self) -> None:
        self.manifest = BackendManifest(
            backend_id="reference.summary",
            name="Reference Summary Backend",
            version="0.1.0",
            description=(
                "Reference backend that compiles ISR into technology-neutral "
                "summary documentation and compilation manifests."
            ),
            capabilities=BackendCapabilities(
                supported_targets=["documentation"],
                languages=["technology-neutral"],
                frameworks=[],
                artifact_types=["markdown", "json"],
                deployment_targets=["filesystem"],
                maturity="reference",
            ),
            entrypoint="compiler.backends.reference_backend:ReferenceBackend",
        )
        self.config = {}

    def validate_configuration(self, config: dict[str, Any]) -> ValidationReport:
        """Default configuration validation — accepts any config."""
        return ValidationReport(valid=True, issues=[])

    def compile(self, context: CompilationContext) -> CompilationOutput:
        """Compile ISR into reference artifacts."""

        from ..validation import validate_isr_payload
        from ..errors import ISRValidationError

        isr = context.isr

        isr_report = validate_isr_payload(isr)

        if not isr_report.valid:
            raise ISRValidationError("ISR validation failed.", isr_report)

        plan = context.plan

        builder = CompilationOutputBuilder()

        builder.add_markdown_artifact(
            path="README.md",
            content=self._readme(isr, plan),
        )

        builder.add_markdown_artifact(
            path="docs/architecture-summary.md",
            content=self._architecture_summary(isr),
        )

        compilation_manifest = {
            "plan": plan.model_dump(mode="json"),
            "isr_id": isr.get("isr_id"),
            "isr_version": isr.get("version"),
            "backend_id": self.manifest.backend_id,
            "backend_version": self.manifest.version,
        }

        builder.add_json_artifact(
            path="manifest/compilation.json",
            payload=compilation_manifest,
        )

        builder.add_log(
            "reference.summary backend produced architecture summary artifacts."
        )

        # Ensure deterministic artifact ordering (sorted by path).
        return builder.build(sort_artifacts=True)

    def _readme(self, isr: dict[str, Any], plan) -> str:
        return "\n".join(
            [
                "# Compiled ISR Artifact",
                "",
                f"ISR ID: `{isr.get('isr_id')}`",
                f"ISR Version: `{isr.get('version')}`",
                f"System Name: `{isr.get('name')}`",
                "",
                f"Compiled by backend `{plan.backend_id}@{plan.backend_version}`.",
                "",
                "This artifact was compiled from the Intermediate Software Representation.",
                "The ISR remains the architectural source of truth.",
                "",
            ]
        )

    def _architecture_summary(self, isr: dict[str, Any]) -> str:
        lines: list[str] = [
            "# Architecture Summary",
            "",
            f"System: {isr.get('name')}",
            "",
        ]

        domains = isr.get("domains", [])

        if domains:
            lines.append("## Domains")
            lines.append("")

            for domain in domains:
                if not isinstance(domain, dict):
                    continue

                domain_name = domain.get("name", "Unnamed Domain")
                lines.append(f"- {domain_name}")

                services = domain.get("services", [])

                for service in services:
                    if not isinstance(service, dict):
                        continue

                    service_name = service.get("name", "Unnamed Service")
                    lines.append(f"  - {service_name}")

                    apis = service.get("apis", [])

                    for api in apis:
                        api_name = (
                            api
                            if isinstance(api, str)
                            else api.get("name", "Unnamed API")
                        )

                        lines.append(f"    - API: {api_name}")

            lines.append("")

        events = isr.get("events", [])

        if events:
            lines.append("## Events")
            lines.append("")

            for event in events:
                event_name = (
                    event
                    if isinstance(event, str)
                    else event.get("name", "Unnamed Event")
                )

                lines.append(f"- {event_name}")

            lines.append("")

        data_models = isr.get("data_models", [])

        if data_models:
            lines.append("## Data Models")
            lines.append("")

            for data_model in data_models:
                model_name = (
                    data_model
                    if isinstance(data_model, str)
                    else data_model.get("name", "Unnamed Data Model")
                )

                lines.append(f"- {model_name}")

            lines.append("")

        security = isr.get("security")

        if security:
            lines.append("## Security")
            lines.append("")
            lines.append("Security policy present in ISR.")
            lines.append("")

        deployment = isr.get("deployment")

        if deployment:
            lines.append("## Deployment")
            lines.append("")
            lines.append("Deployment policy present in ISR.")
            lines.append("")

        return "\n".join(lines)