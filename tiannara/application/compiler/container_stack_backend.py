"""ContainerStackBackend -- infrastructure topology derived from the ISR.

Consumes the typed SystemModel and deterministically emits:

  * ``<slug>/infra/topology.json`` -- machine-readable stack topology: system
    name, topology style, statefulness, and one entry per service (build
    context, Dockerfile, port, health check, dependencies), derived from the
    ISR's infrastructure model and the compiled service layout;
  * ``<slug>/infra/render.py``     -- deterministic, dependency-free renderer
    that turns the topology into deployment-orchestration YAML (strict subset,
    stable key order, quoted scalars) plus a CLI for regeneration;
  * ``<slug>/infra/tests/...``     -- executable pytest suite proving topology
    well-formedness, artifact cross-references (build contexts and Dockerfiles
    exist), render determinism, and health-contract coherence with the
    generated backend entrypoint.

Design constraints (mirrors the FastAPI/Go backends):
  * structure derives solely from the ISR; nothing is hard-coded per product;
  * the bundle roots at ``<slug>/infra/`` so multi-backend fleets sharing one
    project root never collide;
  * generated tests pass on first run against the generated tree itself.
"""

from __future__ import annotations

import json

from tiannara.application.compiler.build_profile import BackendBuildProfile
from tiannara.domain.models.backend_declaration import (
    ArtifactKind,
    BackendCapabilityDeclaration,
)
from tiannara.domain.models.capability_manifest import BundleCapability, CapabilityManifest
from tiannara.domain.models.compilation import CompilationResult
from tiannara.domain.models.system_model import SystemModel

from .naming import slugify

_API_PORT = 8000
_FRONTEND_PORT = 8080


def _healthcheck(path: str, port: int, interval_seconds: int) -> dict:
    probe = (
        "import urllib.request,sys; "
        "sys.exit(0 if urllib.request.urlopen("
        f"'http://127.0.0.1:{port}{path}', timeout=3).status==200 else 1)"
    )
    return {
        "path": path,
        "interval_seconds": interval_seconds,
        "test": ["CMD", "python", "-c", probe],
    }


def _topology(slug: str, system_model: SystemModel) -> dict:
    api_name = f"{slug}-api"
    frontend_name = f"{slug}-frontend"
    return {
        "system": slug,
        "style": system_model.infrastructure.topology.value,
        "stateful": system_model.infrastructure.stateful,
        "availability": system_model.infrastructure.availability.value,
        "services": [
            {
                "name": api_name,
                "kind": "backend",
                "build_context": ".",
                "dockerfile": "Dockerfile",
                "port": _API_PORT,
                "healthcheck": _healthcheck("/health", _API_PORT, 10),
                "depends_on": [],
            },
            {
                "name": frontend_name,
                "kind": "frontend",
                "build_context": f"{slug}/frontend",
                "dockerfile": "Dockerfile",
                "port": _FRONTEND_PORT,
                "healthcheck": _healthcheck("/index.html", _FRONTEND_PORT, 30),
                "depends_on": [api_name],
            },
        ],
    }


class ContainerStackBackend:
    """Deterministic, model-free compiler backend for infrastructure topology."""

    backend_id = "container_stack"

    # -- public: pure product ---------------------------------------------

    def generate(self, system_model: SystemModel) -> CompilationResult:
        slug = slugify(system_model.system_name)
        topology = _topology(slug, system_model)
        root = f"{slug}/infra"
        files: dict[str, str] = {
            f"{root}/__init__.py": "",
            f"{root}/topology.json": json.dumps(topology, indent=2, sort_keys=True)
            + "\n",
            f"{root}/render.py": self._render_py(slug),
            f"{root}/tests/__init__.py": "",
            f"{root}/tests/test_infra.py": self._tests_py(slug),
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
                f"{slug}/infra/topology.json",
                f"{slug}/infra/render.py",
            ),
            verifier_kind="python",
            build_command=["python", "-m", "pip", "install", "-q", "pytest"],
            test_command=["python", "-m", "pytest", "-q", f"{slug}/infra/tests"],
            runtime_image=None,
            requires_build_phase=True,
        )

    def declaration(self) -> BackendCapabilityDeclaration:
        return BackendCapabilityDeclaration(
            backend_id=self.backend_id,
            artifact_kinds=[ArtifactKind.INFRASTRUCTURE_PROVISION],
            capabilities=[
                BundleCapability.INFRASTRUCTURE_PROVISION,
                BundleCapability.BUILD,
                BundleCapability.TEST,
                BundleCapability.CONTAINERIZE,
            ],
            quality_profile=0.75,
            metadata={"language": "python", "style": "topology-render"},
        )

    @property
    def name(self) -> str:
        return self.backend_id

    # -- file generators ---------------------------------------------------

    def _render_py(self, slug: str) -> str:
        return "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import argparse",
                "import json",
                "import sys",
                "from pathlib import Path",
                "",
                "",
                "def _scalar(value) -> str:",
                "    if isinstance(value, bool):",
                '        return "true" if value else "false"',
                "    if isinstance(value, (int, float)):",
                "        return str(value)",
                '    text = str(value).replace(\'"\', \'\\\\"\')',
                '    return f\'"{text}"\'',
                "",
                "",
                "def render(topology: dict) -> str:",
                '    """Deterministic YAML rendering of a topology document."""',
                '    lines = ["services:"]',
                "    for service in topology[\"services\"]:",
                "        lines.append(f\"  {service['name']}:\")",
                '        lines.append("    build:")',
                "        lines.append(",
                "            f\"      context: {_scalar(service['build_context'])}\"",
                "        )",
                "        lines.append(",
                "            f\"      dockerfile: {_scalar(service['dockerfile'])}\"",
                "        )",
                '        lines.append("    ports:")',
                '        lines.append(f"      - \\"{service[\'port\']}:{service[\'port\']}\\"")',
                "        if service.get(\"depends_on\"):",
                '            lines.append("    depends_on:")',
                "            lines.extend(",
                "                f'      - {_scalar(name)}'",
                "                for name in service[\"depends_on\"]",
                "            )",
                '        lines.append("    healthcheck:")',
                '        lines.append("      test:")',
                "        lines.extend(",
                "            f'        - {_scalar(part)}'",
                "            for part in service[\"healthcheck\"][\"test\"]",
                "        )",
                "        lines.append(",
                "            f\"      interval: {service['healthcheck']['interval_seconds']}\"",
                "        )",
                "        lines.append(",
                "            f\"      path: {_scalar(service['healthcheck']['path'])}\"",
                "        )",
                "    return \"\\n\".join(lines) + \"\\n\"",
                "",
                "",
                "def load_topology(root: Path) -> dict:",
                "    return json.loads(",
                f'        (Path(root) / "{slug}" / "infra" / "topology.json").read_text(',
                '            encoding="utf-8"',
                "        )",
                "    )",
                "",
                "",
                'if __name__ == "__main__":',
                '    parser = argparse.ArgumentParser(description="Render the stack topology as YAML")',
                '    parser.add_argument("--root", default=".", help="bundle root containing the system directory")',
                "    args = parser.parse_args()",
                "    sys.stdout.write(render(load_topology(Path(args.root))))",
                "",
            ]
        )

    def _tests_py(self, slug: str) -> str:
        return "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import json",
                "from pathlib import Path",
                "",
                f"from {slug}.infra.render import render",
                "",
                f"ROOT = Path(__file__).resolve().parents[3]",
                f"SYSTEM_DIR = ROOT / \"{slug}\"",
                "",
                "",
                "def _topology() -> dict:",
                '    return json.loads((SYSTEM_DIR / "infra" / "topology.json").read_text(encoding="utf-8"))',
                "",
                "",
                "def test_topology_is_well_formed():",
                "    topology = _topology()",
                f'    assert topology["system"] == "{slug}"',
                '    assert topology["style"]',
                '    assert isinstance(topology["stateful"], bool)',
                '    services = topology["services"]',
                "    assert services, \"topology must declare at least one service\"",
                '    names = [service["name"] for service in services]',
                "    assert len(names) == len(set(names))",
                "    for service in services:",
                '        assert service["kind"] in ("backend", "frontend")',
                '        assert isinstance(service["port"], int)',
                '        assert service["healthcheck"]["path"].startswith("/")',
                '        assert service["healthcheck"]["test"][0] == "CMD"',
                '        for dependency in service["depends_on"]:',
                "            assert dependency in names",
                "",
                "",
                "def test_topology_references_existing_build_artifacts():",
                "    topology = _topology()",
                "    for service in topology[\"services\"]:",
                "        context = (",
                "            ROOT",
                '            if service["build_context"] == "."',
                "            else ROOT / service[\"build_context\"]",
                "        )",
                "        assert context.is_dir(), service[\"build_context\"]",
                "        assert (context / service[\"dockerfile\"]).is_file(), service[\"dockerfile\"]",
                "",
                "",
                "def test_backend_healthcheck_matches_generated_entrypoint():",
                "    topology = _topology()",
                '    api = next(s for s in topology["services"] if s["kind"] == "backend")',
                '    source = (SYSTEM_DIR / "main.py").read_text(encoding="utf-8")',
                '    assert f\'"{api["healthcheck"]["path"]}"\' in source',
                "",
                "",
                "def test_render_is_deterministic_and_coherent():",
                "    topology = _topology()",
                "    rendered = render(topology)",
                "    assert rendered == render(topology)",
                '    assert rendered.startswith("services:")',
                '    api = next(s for s in topology["services"] if s["kind"] == "backend")',
                "    assert f'{api[\"name\"]}:' in rendered",
                "    assert f'\"{api[\"port\"]}:{api[\"port\"]}\"' in rendered",
                "    assert api[\"healthcheck\"][\"path\"] in rendered",
                '    frontend = next(s for s in topology["services"] if s["kind"] == "frontend")',
                "    assert f'{frontend[\"name\"]}:' in rendered",
                "    assert f'- \"{frontend[\"depends_on\"][0]}\"' in rendered",
                "",
                "",
                "def test_render_output_parses_as_topology_services_block():",
                "    rendered = render(_topology())",
                '    lines = rendered.splitlines()',
                '    assert lines[0] == "services:"',
                '    service_lines = [line for line in lines if line.startswith("  ") and line.endswith(":") and not line.startswith("    ")]',
                "    assert len(service_lines) == len(_topology()[\"services\"])",
                "",
            ]
        )

    def _manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            backend_id=self.backend_id,
            capabilities=[
                BundleCapability.INFRASTRUCTURE_PROVISION,
                BundleCapability.BUILD,
                BundleCapability.TEST,
                BundleCapability.CONTAINERIZE,
            ],
            metadata={"language": "python", "style": "topology-render"},
        )
