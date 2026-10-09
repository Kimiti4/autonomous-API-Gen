"""TraceabilityDocsBackend -- documentation derived from the ISR.

Consumes the typed SystemModel and deterministically emits:

  * ``<slug>/docs/REQUIREMENTS_TRACEABILITY.md`` -- capability -> requirement
    -> service -> data model matrix (the audit spine of the bundle);
  * ``<slug>/docs/API_REFERENCE.md``             -- every route the backend
    family exposes (health/readiness plus per-resource CRUD, with the exact
    path parameters the router generates);
  * ``<slug>/docs/ARCHITECTURE.md``              -- layers, topology, security
    posture, data models and invariants, all in abstract vocabulary;
  * ``<slug>/docs/RUNBOOK.md``                   -- start/test/deploy commands
    for every family present, health endpoints, and service level objectives;
  * ``<slug>/docs/ADR-001-deployment-strategy.md`` -- decision record for the
    chosen rollout strategy (required by the documentation policy);
  * ``<slug>/docs/README.md``                    -- artifact index;
  * ``<slug>/docs/validate_docs.py``             -- dependency-free validator
    used by the generated test suite: required artifacts present, ADR present,
    traceability rows well-formed, every router prefix documented, entrypoint
    documented in the runbook.

Design constraints (mirrors the FastAPI/Go backends):
  * structure derives solely from the ISR; nothing is hard-coded per product;
  * the bundle roots at ``<slug>/docs/`` so multi-backend fleets sharing one
    project root never collide;
  * generated tests pass on first run against the generated tree itself.
"""

from __future__ import annotations

from tiannara.application.compiler.build_profile import BackendBuildProfile
from tiannara.domain.models.backend_declaration import (
    ArtifactKind,
    BackendCapabilityDeclaration,
)
from tiannara.domain.models.capability_manifest import BundleCapability, CapabilityManifest
from tiannara.domain.models.compilation import CompilationResult
from tiannara.domain.models.system_model import (
    AbstractFieldType,
    SystemModel,
)

from .naming import pluralize, slugify, snake_case


def _id_field_name(model) -> str | None:
    for field in model.fields:
        if field.name == "id":
            return field.name
    for field in model.fields:
        if field.type is AbstractFieldType.IDENTIFIER:
            return field.name
    return None


class TraceabilityDocsBackend:
    """Deterministic, model-free compiler backend for generated documentation."""

    backend_id = "traceability_docs"

    # -- public: pure product ---------------------------------------------

    def generate(self, system_model: SystemModel) -> CompilationResult:
        slug = slugify(system_model.system_name)
        root = f"{slug}/docs"
        routes_present = bool(system_model.services)
        files: dict[str, str] = {
            f"{root}/__init__.py": "",
            f"{root}/README.md": self._readme(slug),
            f"{root}/REQUIREMENTS_TRACEABILITY.md": self._traceability(system_model),
            f"{root}/API_REFERENCE.md": self._api_reference(slug, system_model),
            f"{root}/ARCHITECTURE.md": self._architecture(slug, system_model),
            f"{root}/RUNBOOK.md": self._runbook(slug, system_model, routes_present),
            f"{root}/ADR-001-deployment-strategy.md": self._adr(system_model),
            f"{root}/validate_docs.py": self._validate_py(slug),
            f"{root}/tests/__init__.py": "",
            f"{root}/tests/test_docs.py": self._tests_py(
                slug, system_model, routes_present
            ),
        }
        return CompilationResult(
            backend_id=self.backend_id,
            system_name=slug,
            files=files,
            capability_manifest=self._manifest(),
        )

    def build_profile(self, system_name: str) -> BackendBuildProfile:
        slug = slugify(system_name)
        return BackendBuildProfile(
            language="python",
            required_files=(
                f"{slug}/docs/REQUIREMENTS_TRACEABILITY.md",
                f"{slug}/docs/API_REFERENCE.md",
                f"{slug}/docs/RUNBOOK.md",
            ),
            verifier_kind="python",
            build_command=["python", "-m", "pip", "install", "-q", "pytest"],
            test_command=["python", "-m", "pytest", "-q", f"{slug}/docs/tests"],
            runtime_image=None,
            requires_build_phase=True,
        )

    def declaration(self) -> BackendCapabilityDeclaration:
        return BackendCapabilityDeclaration(
            backend_id=self.backend_id,
            artifact_kinds=[ArtifactKind.DOCUMENTATION],
            capabilities=[
                BundleCapability.DOCUMENTATION,
                BundleCapability.BUILD,
                BundleCapability.TEST,
                BundleCapability.RELEASE,
            ],
            quality_profile=0.7,
            metadata={"language": "python", "style": "traceability-docs"},
        )

    @property
    def name(self) -> str:
        return self.backend_id

    # -- derivation helpers ------------------------------------------------

    @staticmethod
    def _prefixes(system_model: SystemModel) -> list[str]:
        return [pluralize(snake_case(m.name)) for m in system_model.data_models]

    # -- file generators ---------------------------------------------------

    def _readme(self, slug: str) -> str:
        return "\n".join(
            [
                f"# {slug} -- generated documentation",
                "",
                "Documentation artifacts generated from the typed ISR.",
                "Regeneration is deterministic: identical ISR, identical files.",
                "",
                "## Artifacts",
                "",
                "- `REQUIREMENTS_TRACEABILITY.md` -- capability/requirement/service/model matrix",
                "- `API_REFERENCE.md` -- routes and auth contract",
                "- `ARCHITECTURE.md` -- layers, topology, security posture, models",
                "- `RUNBOOK.md` -- start, test, deploy and verification commands",
                "- `ADR-001-deployment-strategy.md` -- rollout strategy decision record",
                "- `validate_docs.py` -- structural validator (used by the test suite)",
                "",
                "## Validation",
                "",
                "```bash",
                "python -m pytest -q " + f"{slug}/docs/tests",
                "```",
                "",
            ]
        )

    def _traceability(self, system_model: SystemModel) -> str:
        lines = [
            "# Requirements Traceability",
            "",
            "Every compiled artifact traces back to ISR capabilities and requirements.",
            "",
            "| Capability | Requirement refs | Priority | Criticality | Services | Data models |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        service_names = ", ".join(s.name for s in system_model.services) or "-"
        model_names = ", ".join(m.name for m in system_model.data_models) or "-"
        if not system_model.capabilities:
            lines.append(
                f"| - | - | - | - | {service_names} | {model_names} |"
            )
        for capability in system_model.capabilities:
            refs = ", ".join(capability.traced_requirement_ids) or "-"
            lines.append(
                f"| {capability.name} | {refs} | {capability.priority.value} | "
                f"{capability.criticality.value} | {service_names} | {model_names} |"
            )
        lines += [
            "",
            "## Services",
            "",
            "| Service | Domain | Responsibilities |",
            "| --- | --- | --- |",
        ]
        if system_model.services:
            for service in system_model.services:
                responsibilities = ", ".join(service.responsibilities) or "-"
                lines.append(
                    f"| {service.name} | {service.domain_id} | {responsibilities} |"
                )
        else:
            lines.append("| - | - | - |")
        lines += [
            "",
            "## Data models",
            "",
            "| Model | Owning service | Fields | Invariants |",
            "| --- | --- | --- | --- |",
        ]
        if system_model.data_models:
            services = {s.id: s.name for s in system_model.services}
            for model in system_model.data_models:
                fields = ", ".join(
                    f"{f.name} ({f.type.value})"
                    + ("" if f.required else "?")
                    for f in model.fields
                )
                invariants = ", ".join(model.invariants) or "-"
                owner = services.get(model.owning_service_id, model.owning_service_id)
                lines.append(
                    f"| {model.name} | {owner} | {fields} | {invariants} |"
                )
        else:
            lines.append("| - | - | - | - |")
        lines.append("")
        return "\n".join(lines)

    def _api_reference(self, slug: str, system_model: SystemModel) -> str:
        auth = system_model.security.authentication.value
        lines = [
            "# API Reference",
            "",
            f"Generated for `{slug}` from the typed ISR.",
            "",
            "## Authentication",
            "",
            f"Posture: `{auth}`.",
        ]
        if auth != "anonymous":
            lines += [
                "",
                "Send `X-API-Key: <key>` on every resource request. "
                "Missing or invalid credentials yield `401`.",
            ]
        lines += [
            "",
            "## Endpoints",
            "",
            "| Method | Path | Description |",
            "| --- | --- | --- |",
            "| GET | /health | Liveness probe |",
            "| GET | /readiness | Readiness probe |",
        ]
        for model in system_model.data_models:
            prefix = "/" + pluralize(snake_case(model.name))
            param = "{" + snake_case(model.name) + "_id}"
            lines += [
                f"| GET | {prefix} | List {model.name} |",
                f"| POST | {prefix} | Create {model.name} |",
                f"| GET | {prefix}/{param} | Fetch {model.name} by id |",
                f"| PUT | {prefix}/{param} | Replace {model.name} by id |",
                f"| DELETE | {prefix}/{param} | Delete {model.name} by id |",
            ]
        lines += [
            "",
            "## Status codes",
            "",
            "- `200` -- successful read/replace",
            "- `201` -- created",
            "- `204` -- deleted",
            "- `401` -- missing or invalid credentials",
            "- `404` -- unknown identifier",
            "- `422` -- payload failed validation",
            "",
        ]
        return "\n".join(lines)

    def _architecture(self, slug: str, system_model: SystemModel) -> str:
        infrastructure = system_model.infrastructure
        deployment = system_model.deployment
        lines = [
            f"# Architecture -- {slug}",
            "",
            "## Layers",
            "",
            "- `domain/` -- entities and repository ports (imports nothing outer)",
            "- `application/` -- services and use cases (depends on domain)",
            "- `infrastructure/` -- adapters (in-memory repositories)",
            "- `api/` -- routers, schemas, auth dependency",
            "",
            "## Topology",
            "",
            f"- style: `{infrastructure.topology.value}`",
            f"- stateful: `{str(infrastructure.stateful).lower()}`",
            f"- availability: `{infrastructure.availability.value}`",
            f"- deployment strategy: `{deployment.rollout_strategy.value}`",
            f"- zero downtime required: `{str(deployment.zero_downtime_required).lower()}`",
            "",
            "## Security posture",
            "",
            f"- authentication: `{system_model.security.authentication.value}`",
            f"- authorization: `{system_model.security.authorization.value}`",
            f"- data classification: `{system_model.security.data_classification.value}`",
            f"- encryption in transit required: `{str(system_model.security.encryption_in_transit_required).lower()}`",
            f"- audit logging required: `{str(system_model.security.audit_logging_required).lower()}`",
            "",
            "## Services",
            "",
        ]
        if system_model.services:
            for service in system_model.services:
                lines.append(f"### {service.name}")
                lines.append("")
                for responsibility in service.responsibilities:
                    lines.append(f"- {responsibility}")
                lines.append("")
        else:
            lines += ["- (none declared)", ""]
        lines.append("## Data models")
        lines.append("")
        if system_model.data_models:
            for model in system_model.data_models:
                lines.append(f"### {model.name}")
                lines.append("")
                lines.append(f"- owning service: `{model.owning_service_id}`")
                lines.append(f"- consistency: `{model.consistency.value}`")
                for field in model.fields:
                    required = "required" if field.required else "optional"
                    suffix = (
                        f" -- one of: {', '.join(field.enumeration_values)}"
                        if field.type is AbstractFieldType.ENUMERATION
                        and field.enumeration_values
                        else ""
                    )
                    lines.append(
                        f"- `{field.name}`: `{field.type.value}` ({required}){suffix}"
                    )
                for invariant in model.invariants:
                    lines.append(f"- invariant: {invariant}")
                lines.append("")
        else:
            lines += ["- (none declared)", ""]
        return "\n".join(lines)

    def _runbook(self, slug: str, system_model: SystemModel, routes: bool) -> str:
        lines = [
            f"# Runbook -- {slug}",
            "",
            "## Start",
            "",
        ]
        if routes:
            lines += [
                "```bash",
                "pip install -r requirements.txt",
                f'uvicorn "{slug}.main:create_app" --factory --host 127.0.0.1 --port 8000',
                "```",
                "",
                "Environment: `API_KEY` (credential), `LOG_LEVEL`, `CORS_ORIGINS`.",
                "",
                "Health endpoints: `GET /health`, `GET /readiness`.",
                "",
                "## Verify",
                "",
                "```bash",
                f"python -m pytest -q {slug}/tests",
                f"python -m pytest -q {slug}/migrations/tests",
                f"python -m pytest -q {slug}/infra/tests",
                f"python -m pytest -q {slug}/deploy/tests",
                f"python -m pytest -q {slug}/docs/tests",
                f"node --test {slug}/frontend/tests",
                "```",
                "",
            ]
        else:
            lines += [
                "(no service entrypoint declared in the ISR)",
                "",
                "## Verify",
                "",
                "```bash",
                f"python -m pytest -q {slug}/docs/tests",
                "```",
                "",
            ]
        lines += [
            "## Migrations",
            "",
            "```bash",
            f"python {slug}/migrations/apply.py app.db",
            "```",
            "",
            "## Deployment",
            "",
            f"Strategy: `{system_model.deployment.rollout_strategy.value}`; "
            f"environments: {', '.join(system_model.deployment.environment_names)}.",
            "",
            "```bash",
            f"python -m {slug}.deploy.plan --root .",
            f"python -m {slug}.infra.render --root .",
            "```",
            "",
            "Preflight must return zero problems before any rollout step runs.",
            "",
            "## Service level objectives",
            "",
        ]
        objectives = system_model.operational_policies.service_level_objectives
        if objectives:
            for objective in objectives:
                lines.append(
                    f"- {objective.name}: {objective.metric} -> {objective.target}"
                )
        else:
            lines.append("- (none declared)")
        lines += [
            "",
            "## Incident response",
            "",
            f"- required: `{str(system_model.operational_policies.incident_response_required).lower()}`",
            f"- backup posture: `{system_model.operational_policies.backup_posture}`",
            "",
        ]
        return "\n".join(lines)

    def _adr(self, system_model: SystemModel) -> str:
        deployment = system_model.deployment
        strategy = deployment.rollout_strategy.value
        return "\n".join(
            [
                "# ADR-001: Deployment rollout strategy",
                "",
                "## Status",
                "",
                "Accepted (derived from the typed ISR).",
                "",
                "## Context",
                "",
                f"The system must deploy to {', '.join(deployment.environment_names)} "
                f"with zero downtime required = "
                f"`{str(deployment.zero_downtime_required).lower()}` and scaling "
                f"policy `{deployment.scaling_policy.value}`.",
                "",
                "## Decision",
                "",
                f"The deployment family uses the `{strategy}` rollout strategy.",
                "",
                "## Alternatives considered",
                "",
                "- `all_at_once` -- simplest, but violates zero-downtime intent",
                "- `rolling` -- health-gated replacement of instances",
                "- `blue_green` -- parallel environments with a traffic switch",
                "- `canary` -- progressive exposure with observation gates",
                "",
                "## Consequences",
                "",
                "- rollout steps are generated from this strategy and are testable",
                "- changing the strategy in the ISR regenerates this record",
                "",
            ]
        )

    def _validate_py(self, slug: str) -> str:
        return "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import re",
                "from pathlib import Path",
                "",
                f'SYSTEM = "{slug}"',
                "REQUIRED = (",
                '    "README.md",',
                '    "API_REFERENCE.md",',
                '    "ARCHITECTURE.md",',
                '    "RUNBOOK.md",',
                '    "REQUIREMENTS_TRACEABILITY.md",',
                ")",
                "",
                "",
                "def validate(root: Path, slug: str = SYSTEM) -> list[str]:",
                '    """Structural validation of the generated documentation set."""',
                "    root = Path(root)",
                "    problems: list[str] = []",
                "    docs = root / slug / \"docs\"",
                "    if not docs.is_dir():",
                '        return [f"missing documentation directory: {slug}/docs"]',
                "    for name in REQUIRED:",
                "        if not (docs / name).is_file():",
                '            problems.append(f"missing documentation artifact: {slug}/docs/{name}")',
                "    if not sorted(docs.glob(\"ADR*.md\")):",
                '        problems.append("no architecture decision record (ADR*.md) present")',
                "    trace_path = docs / \"REQUIREMENTS_TRACEABILITY.md\"",
                "    if trace_path.is_file():",
                "        rows = [",
                "            line",
                "            for line in trace_path.read_text(encoding=\"utf-8\").splitlines()",
                "            if line.startswith(\"|\")",
                "        ]",
                "        data_rows = [",
                "            row",
                "            for row in rows",
                "            if not set(row.replace(\"|\", \"\").replace(\"-\", \"\").strip()) <= {\" \"}",
                "        ]",
                "        if len(data_rows) < 2:",
                '            problems.append("traceability matrix has no capability rows")',
                "        for row in data_rows[1:]:",
                "            cells = [cell.strip() for cell in row.strip(\"|\").split(\"|\")]",
                "            if any(cell == \"\" for cell in cells):",
                '                problems.append(f"traceability row has empty cells: {row[:60]}")',
                "                break",
                "    api_path = docs / \"API_REFERENCE.md\"",
                "    if api_path.is_file():",
                "        api_text = api_path.read_text(encoding=\"utf-8\")",
                '        if "/health" not in api_text:',
                '            problems.append("API reference does not document the health endpoint")',
                "        routes = root / slug / \"api\" / \"routes.py\"",
                "        if routes.is_file():",
                "            prefixes = re.findall(",
                "                r'prefix=\"(/[^\"]*)\"',",
                "                routes.read_text(encoding=\"utf-8\"),",
                "            )",
                "            for prefix in prefixes:",
                "                if prefix not in api_text:",
                "                    problems.append(",
                "                        f\"router prefix '{prefix}' is not documented in the API reference\"",
                "                    )",
                "    runbook_path = docs / \"RUNBOOK.md\"",
                "    entrypoint = root / slug / \"main.py\"",
                "    if runbook_path.is_file() and entrypoint.is_file():",
                "        runbook_text = runbook_path.read_text(encoding=\"utf-8\")",
                "        if f\"{slug}.main\" not in runbook_text:",
                '            problems.append("runbook does not document the service entry point")',
                "    return problems",
                "",
            ]
        )

    def _tests_py(self, slug: str, system_model: SystemModel, routes: bool) -> str:
        prefixes = [f"/{p}" for p in self._prefixes(system_model)]
        capability_names = [c.name for c in system_model.capabilities]
        service_names = [s.name for s in system_model.services]
        model_names = [m.name for m in system_model.data_models]
        route_case: list[str] = []
        if routes:
            route_case = [
                "",
                "def test_every_data_model_has_a_documented_route_section():",
                f'    routes_py = (ROOT / "{slug}" / "api" / "routes.py").read_text(',
                '        encoding="utf-8"',
                "    )",
                "    api = (ROOT / \"" + slug + "\" / \"docs\" / \"API_REFERENCE.md\").read_text(",
                '        encoding="utf-8"',
                "    )",
                f"    for prefix in {prefixes!r}:",
                '        assert f\'prefix="{prefix}"\' in routes_py',
                "        assert prefix in api",
                "",
            ]
        return "\n".join(
            [
                "from __future__ import annotations",
                "",
                "from pathlib import Path",
                "",
                f"from {slug}.docs.validate_docs import validate",
                "",
                "ROOT = Path(__file__).resolve().parents[3]",
                "",
                "",
                "def test_validate_passes_against_materialized_tree():",
                f'    assert validate(ROOT, "{slug}") == []',
                "",
                "",
                "def test_traceability_covers_capabilities_services_and_models():",
                f'    trace = (ROOT / "{slug}" / "docs" / "REQUIREMENTS_TRACEABILITY.md").read_text(',
                '        encoding="utf-8"',
                "    )",
                f"    for name in {capability_names!r}:",
                "        assert name in trace",
                f"    for name in {service_names!r}:",
                "        assert name in trace",
                f"    for name in {model_names!r}:",
                "        assert name in trace",
                "",
            ]
            + route_case
            + [
                "def test_runbook_documents_verification_commands():",
                f'    runbook = (ROOT / "{slug}" / "docs" / "RUNBOOK.md").read_text(',
                '        encoding="utf-8"',
                "    )",
                '    assert "pytest" in runbook',
            ]
            + (['    assert "/health" in runbook'] if routes else [])
            + [""]
        )

    def _manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            backend_id=self.backend_id,
            capabilities=[
                BundleCapability.DOCUMENTATION,
                BundleCapability.BUILD,
                BundleCapability.TEST,
            ],
            metadata={"language": "python", "style": "traceability-docs"},
        )
