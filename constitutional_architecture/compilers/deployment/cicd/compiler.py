"""
Phase 15 — CI/CD & Deployment Bundle Compiler (Meta-Compiler)
Inspects the SystemDeploymentBundle — which contains source, infrastructure,
database, operational intelligence, runtime policies, documentation, and tests —
and compiles the GitHub Actions pipeline and Docker Compose wiring that bind
them into a single deployable, production-ready artifact.

This is a meta-compiler: it reads only produced artifacts (bundles and their
exposed interfaces), never the ISR or Genome, preserving the responsibility
boundary of deployment.

Constitutional Alignment:
- "Treat every framework and platform as a compiler backend."
- Deployment is a stage of the compilation pipeline, not a collection of templates.
"""

from __future__ import annotations

from typing import Any, Dict, List

from constitutional_architecture.compilers.deployment.base import DeploymentMetaCompiler
from constitutional_architecture.core.models.bundle import (
    ArtifactType, CompilationBundle, CompilationManifest, SystemDeploymentBundle,
)


class CICDDeploymentCompiler(DeploymentMetaCompiler):
    def compile_system(
        self,
        bundle: SystemDeploymentBundle,
        context: Dict[str, Any],
    ) -> CompilationBundle:
        project = bundle.project_name or context.get("project_name", "generated-system")

        has_backend = self._has(bundle, "fastapi_hexagonal")
        has_infra = self._has(bundle, "terraform_aws")
        has_db = self._has(bundle, "postgres_alembic")
        has_ops = self._has(bundle, "operational_intelligence_v1")
        has_tests = self._has(bundle, "pytest_layered")

        backend_port = self._interface(bundle, "fastapi_hexagonal", "backend_port", 8000)
        prometheus_port = self._interface(bundle, "operational_intelligence_v1", "prometheus_port", 9090)
        grafana_port = self._interface(bundle, "operational_intelligence_v1", "grafana_port", 3001)
        deploy_cmd = self._interface(bundle, "terraform_aws", "deployment_cmd", "terraform apply")

        files: Dict[str, str] = {}

        files[".github/workflows/deploy.yml"] = self._generate_workflow(
            project, has_tests, has_infra, has_db, has_backend, deploy_cmd,
        )
        files["docker-compose.yml"] = self._generate_compose(
            project, has_backend, has_db, has_ops, backend_port, prometheus_port, grafana_port,
        )

        pipeline_manifest = CompilationManifest(
            artifact_type=ArtifactType.CI_CD_PIPELINE,
            domain="cicd",
            files={".github/workflows/deploy.yml": files[".github/workflows/deploy.yml"]},
            metadata={"platform": "github_actions", "project": project},
        )
        runtime_manifest = CompilationManifest(
            artifact_type=ArtifactType.CONFIGURATION,
            domain="deployment",
            files={"docker-compose.yml": files["docker-compose.yml"]},
            metadata={"orchestration": "docker_compose"},
        )

        return CompilationBundle(
            compiler_id="github_actions_compose",
            target_technology="cicd",
            manifests=[pipeline_manifest, runtime_manifest],
            exposed_interfaces={
                "deploy_platform": "github_actions",
                "deploy_artifact": "docker-compose.yml",
                "deploy_cmd": "docker compose up -d",
            },
        )

    # ─── Bundle inspection (artifact-level only) ────────────────────────────

    @staticmethod
    def _has(bundle: SystemDeploymentBundle, compiler_id: str) -> bool:
        return compiler_id in bundle.bundles

    @staticmethod
    def _interface(
        bundle: SystemDeploymentBundle,
        compiler_id: str,
        key: str,
        default: Any,
    ) -> Any:
        comp_bundle = bundle.bundles.get(compiler_id)
        if comp_bundle is None:
            return default
        return comp_bundle.exposed_interfaces.get(key, default)

    # ─── GitHub Actions pipeline ────────────────────────────────────────────

    def _generate_workflow(
        self,
        project: str,
        has_tests: bool,
        has_infra: bool,
        has_db: bool,
        has_backend: bool,
        deploy_cmd: str,
    ) -> str:
        test_steps = ""
        if has_tests:
            test_steps = (
                "      - name: Run compiled test suite\n"
                "        run: |\n"
                "          pip install pytest hypothesis httpx\n"
                "          pytest tests/\n"
            )

        deploy_steps = ""
        if has_infra:
            deploy_steps += (
                "      - name: Provision infrastructure\n"
                "        run: |\n"
                "          terraform init\n"
                f"          {deploy_cmd}\n"
            )
        if has_db:
            deploy_steps += (
                "      - name: Apply database migrations\n"
                "        run: alembic upgrade head\n"
            )
        if has_backend:
            deploy_steps += (
                "      - name: Deploy application stack\n"
                "        run: docker compose up -d\n"
            )

        jobs: List[str] = []
        jobs.append("jobs:")

        if has_tests:
            jobs.append("  test:")
            jobs.append("    runs-on: ubuntu-latest")
            jobs.append("    steps:")
            jobs.append("      - uses: actions/checkout@v4")
            jobs.append('      - uses: actions/setup-python@v5')
            jobs.append('        with:')
            jobs.append('          python-version: "3.12"')
            jobs.append("      - name: Run compiled test suite")
            jobs.append("        run: |")
            jobs.append("          pip install pytest hypothesis httpx")
            jobs.append("          pytest tests/")

        if has_backend:
            build_needs = "    needs: test\n" if has_tests else ""
            jobs.append("  build:")
            jobs.append("    runs-on: ubuntu-latest")
            if has_tests:
                jobs.append("    needs: test")
            jobs.append("    steps:")
            jobs.append("      - uses: actions/checkout@v4")
            jobs.append("      - name: Build images")
            jobs.append("        run: docker compose build")

        if deploy_steps:
            jobs.append("  deploy:")
            jobs.append("    runs-on: ubuntu-latest")
            jobs.append(f"    needs: [{'test, build' if has_tests and has_backend else 'build' if has_backend else 'test'}]")
            jobs.append("    environment: production")
            jobs.append("    steps:")
            jobs.append("      - uses: actions/checkout@v4")
            if has_infra:
                jobs.append("      - uses: hashicorp/setup-terraform@v3")
                jobs.append("      - name: Provision infrastructure")
                jobs.append("        run: |")
                jobs.append("          terraform init")
                jobs.append(f"          {deploy_cmd}")
            if has_db:
                jobs.append("      - name: Apply database migrations")
                jobs.append("        run: alembic upgrade head")
            if has_backend:
                jobs.append("      - name: Deploy application stack")
                jobs.append("        run: docker compose up -d")

        return f"""name: Deploy

on:
  push:
    branches: [main]

{chr(10).join(jobs)}
"""

    # ─── Docker Compose wiring ──────────────────────────────────────────────

    def _generate_compose(
        self,
        project: str,
        has_backend: bool,
        has_db: bool,
        has_ops: bool,
        backend_port: int,
        prometheus_port: int,
        grafana_port: int,
    ) -> str:
        services: List[str] = []

        if has_backend:
            services += [
                "  backend:",
                "    build: ./backend",
                f'    ports:',
                f'      - "{backend_port}:{backend_port}"',
                "    environment:",
                "      - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317",
            ]

        if has_db:
            services += [
                "  postgres:",
                "    image: postgres:16",
                "    environment:",
                '      POSTGRES_DB: app',
                '      POSTGRES_USER: app',
                '      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}',
            ]

        if has_ops:
            services += [
                "  otel-collector:",
                "    image: otel/opentelemetry-collector-contrib",
                "    volumes:",
                "      - ./observability/telemetry:/etc/otel",
                "  prometheus:",
                "    image: prom/prometheus",
                "    volumes:",
                "      - ./observability/slos:/etc/prometheus",
                "    ports:",
                f'      - "{prometheus_port}:{prometheus_port}"',
                "  grafana:",
                "    image: grafana/grafana",
                "    volumes:",
                "      - ./observability/dashboards:/var/lib/grafana/dashboards",
                "    ports:",
                f'      - "{grafana_port}:{grafana_port}"',
            ]

        body = "\n".join(services)
        return f"# Auto-generated deployment wiring for {project}\nversion: \"3.9\"\n\nservices:\n{body}\n"
