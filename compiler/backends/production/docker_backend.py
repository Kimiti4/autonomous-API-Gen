"""
Docker deployment compiler backend.

Compiles ISR into Docker Compose and environment templates.
"""

from __future__ import annotations

from ...models import (
    BackendCapabilities,
    BackendManifest,
    CompilationContext,
    CompilationOutput,
    ValidationReport,
)
from ...sdk.artifacts import CompilationOutputBuilder
from ...sdk.base import CompilerBackendBase
from .isr_helpers import iter_data_models, project_name, project_slug


class DockerDeploymentBackend(CompilerBackendBase):
    """Compiles ISR into Docker deployment artifacts."""

    def __init__(self) -> None:
        self.manifest = BackendManifest(
            backend_id="deployment.docker",
            name="Docker Deployment Backend",
            version="0.1.0",
            description="Compiles ISR into Docker deployment artifacts.",
            capabilities=BackendCapabilities(
                supported_targets=["deployment"],
                languages=["Docker"],
                frameworks=["Docker", "Docker Compose"],
                artifact_types=["compose", "environment"],
                deployment_targets=["docker"],
                maturity="production",
            ),
            entrypoint=(
                "compiler.backends.production.docker_backend:"
                "DockerDeploymentBackend"
            ),
        )
        self.config = {}

    def validate_configuration(self, config: dict) -> ValidationReport:
        """Default configuration validation — accepts any config."""
        return ValidationReport(valid=True, issues=[])

    def compile(self, context: CompilationContext) -> CompilationOutput:
        isr = context.isr

        builder = CompilationOutputBuilder()

        slug = project_slug(isr)
        has_database = bool(list(iter_data_models(isr)))

        compose_lines = [
            "services:",
            "  app:",
            f"    image: {slug}-app:latest",
            "    build: .",
            "    ports:",
            '      - "8000:8000"',
            "    environment:",
            f"      - APP_NAME={project_name(isr)}",
            "      - ENVIRONMENT=production",
        ]

        if has_database:
            compose_lines.append("    depends_on:")
            compose_lines.append("      - db")

        if has_database:
            compose_lines.extend(
                [
                    "",
                    "  db:",
                    "    image: postgres:16",
                    "    environment:",
                    f"      - POSTGRES_DB={slug}",
                    f"      - POSTGRES_USER={slug}",
                    "      - POSTGRES_PASSWORD=change-me",
                    "    volumes:",
                    "      - db_data:/var/lib/postgresql/data",
                    "",
                    "volumes:",
                    "  db_data: {}",
                ]
            )

        builder.add_artifact(
            path="docker-compose.yml",
            content="\n".join(compose_lines) + "\n",
            content_type="text/yaml",
        )

        builder.add_artifact(
            path=".env.example",
            content="\n".join(
                [
                    f"APP_NAME={project_name(isr)}",
                    "ENVIRONMENT=production",
                    "DATABASE_URL=postgresql+psycopg://user:password@db:5432/"
                    + slug,
                ]
            )
            + "\n",
            content_type="text/plain",
        )

        builder.add_log("Compiled Docker deployment artifacts.")

        return builder.build()