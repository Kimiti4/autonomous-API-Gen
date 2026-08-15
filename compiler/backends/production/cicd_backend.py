"""
CI/CD compiler backend.

Compiles ISR into a GitHub Actions CI/CD workflow.
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
from .isr_helpers import project_name, project_slug


WORKFLOW = """name: CI

on:
  push:
    branches:
      - main
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r dev-requirements.txt

      - name: Run tests
        run: pytest -q

  build_container:
    runs-on: ubuntu-latest
    needs: test

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Build container
        run: docker build -t {slug}-app:latest .
"""


class GitHubActionsBackend(CompilerBackendBase):
    """Compiles ISR into GitHub Actions artifacts."""

    def __init__(self) -> None:
        self.manifest = BackendManifest(
            backend_id="cicd.github_actions",
            name="GitHub Actions CI/CD Backend",
            version="0.1.0",
            description="Compiles ISR into CI/CD workflow artifacts.",
            capabilities=BackendCapabilities(
                supported_targets=["ci_cd"],
                languages=["YAML"],
                frameworks=["GitHub Actions"],
                artifact_types=["workflow"],
                deployment_targets=["github-actions"],
                maturity="production",
            ),
            entrypoint=(
                "compiler.backends.production.cicd_backend:"
                "GitHubActionsBackend"
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

        builder.add_artifact(
            path=".github/workflows/ci.yml",
            content=WORKFLOW.replace("{slug}", slug),
            content_type="text/yaml",
        )

        builder.add_markdown_artifact(
            path="docs/cicd.md",
            content="\n".join(
                [
                    "# CI/CD",
                    "",
                    f"Project: {project_name(isr)}",
                    "",
                    "Generated CI/CD pipeline:",
                    "",
                    "- Run tests",
                    "- Build container image",
                    "",
                ]
            ),
        )

        builder.add_log("Compiled GitHub Actions CI/CD artifacts.")

        return builder.build()