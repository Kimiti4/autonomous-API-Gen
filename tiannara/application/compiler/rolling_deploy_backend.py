"""RollingDeployBackend -- deployment planning derived from the ISR.

Consumes the typed SystemModel's deployment model and deterministically emits:

  * ``<slug>/deploy/deployment.json`` -- machine-readable deployment
    descriptor: rollout strategy, target environments, zero-downtime
    requirement, scaling policy, and the service names being deployed
    (derived from the same naming rule the infrastructure family uses);
  * ``<slug>/deploy/plan.py``         -- dependency-free planner: strategy ->
    ordered rollout steps (health-gated for rolling updates), a preflight
    checker that validates the materialized tree (entrypoint, health route,
    container contract, infrastructure topology, frontend entry, descriptor),
    plus a descriptor loader;
  * ``<slug>/deploy/tests/...``       -- executable pytest suite proving
    descriptor well-formedness, health-gated rolling order, zero-downtime
    alternates, strategy validation, preflight success against the materialized
    tree, and cross-family coherence with the infrastructure topology.

Design constraints (mirrors the FastAPI/Go backends):
  * structure derives solely from the ISR; nothing is hard-coded per product;
  * the bundle roots at ``<slug>/deploy/`` so multi-backend fleets sharing one
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


def _descriptor(slug: str, system_model: SystemModel) -> dict:
    deployment = system_model.deployment
    return {
        "system": slug,
        "strategy": deployment.rollout_strategy.value,
        "environments": list(deployment.environment_names),
        "zero_downtime_required": deployment.zero_downtime_required,
        "scaling_policy": deployment.scaling_policy.value,
        "services": [f"{slug}-api", f"{slug}-frontend"],
    }


class RollingDeployBackend:
    """Deterministic, model-free compiler backend for deployment planning."""

    backend_id = "rolling_deploy"

    # -- public: pure product ---------------------------------------------

    def generate(self, system_model: SystemModel) -> CompilationResult:
        slug = slugify(system_model.system_name)
        descriptor = _descriptor(slug, system_model)
        root = f"{slug}/deploy"
        files: dict[str, str] = {
            f"{root}/__init__.py": "",
            f"{root}/deployment.json": json.dumps(
                descriptor, indent=2, sort_keys=True
            )
            + "\n",
            f"{root}/plan.py": self._plan_py(slug),
            f"{root}/tests/__init__.py": "",
            f"{root}/tests/test_deploy.py": self._tests_py(slug),
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
                f"{slug}/deploy/deployment.json",
                f"{slug}/deploy/plan.py",
            ),
            verifier_kind="python",
            build_command=["python", "-m", "pip", "install", "-q", "pytest"],
            test_command=["python", "-m", "pytest", "-q", f"{slug}/deploy/tests"],
            runtime_image=None,
            requires_build_phase=True,
        )

    def declaration(self) -> BackendCapabilityDeclaration:
        return BackendCapabilityDeclaration(
            backend_id=self.backend_id,
            artifact_kinds=[ArtifactKind.DEPLOYMENT],
            capabilities=[
                BundleCapability.DEPLOY,
                BundleCapability.BUILD,
                BundleCapability.TEST,
                BundleCapability.RELEASE,
            ],
            quality_profile=0.75,
            metadata={"language": "python", "style": "rollout-plan"},
        )

    @property
    def name(self) -> str:
        return self.backend_id

    # -- file generators ---------------------------------------------------

    def _plan_py(self, slug: str) -> str:
        return "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import json",
                "from pathlib import Path",
                "",
                f'ENTRYPOINT = "{slug}/main.py"',
                f'DESCRIPTOR = "{slug}/deploy/deployment.json"',
                "",
                "",
                "def rollout_steps(strategy: str, zero_downtime: bool = True) -> list[str]:",
                '    if strategy == "rolling":',
                "        if zero_downtime:",
                "            return [",
                '                "preflight",',
                '                "pull",',
                '                "start-replacement",',
                '                "health-check",',
                '                "switch-traffic",',
                '                "retire-old",',
                '                "post-checks",',
                "            ]",
                "        return [",
                '            "preflight",',
                '            "pull",',
                '            "stop-old",',
                '            "start-new",',
                '            "post-checks",',
                "        ]",
                '    if strategy == "blue_green":',
                "        return [",
                '            "preflight",',
                '            "build-replacement",',
                '            "smoke-replacement",',
                '            "switch-traffic",',
                '            "retire-previous",',
                "        ]",
                '    if strategy == "canary":',
                "        return [",
                '            "preflight",',
                '            "canary-10",',
                '            "observe",',
                '            "canary-50",',
                '            "observe",',
                '            "promote",',
                "        ]",
                '    if strategy == "all_at_once":',
                "        return [",
                '            "preflight",',
                '            "replace-all",',
                '            "post-checks",',
                "        ]",
                '    raise ValueError(f"unknown rollout strategy: {strategy!r}")',
                "",
                "",
                "def load_deployment(root: Path) -> dict:",
                "    return json.loads((Path(root) / DESCRIPTOR).read_text(encoding=\"utf-8\"))",
                "",
                "",
                "def preflight(root: Path) -> list[str]:",
                '    """Validate the materialized tree before any rollout step runs."""',
                "    root = Path(root)",
                "    problems: list[str] = []",
                "    entrypoint = root / ENTRYPOINT",
                "    if not entrypoint.is_file():",
                '        problems.append(f"missing entrypoint: {ENTRYPOINT}")',
                "    elif '\"/health\"' not in entrypoint.read_text(encoding=\"utf-8\"):",
                '        problems.append("entrypoint does not expose the /health route")',
                "    if not (root / \"Dockerfile\").is_file():",
                '        problems.append("missing container contract: Dockerfile")',
                f'    topology = root / "{slug}" / "infra" / "topology.json"',
                "    if not topology.is_file():",
                f'        problems.append("missing infrastructure topology: {slug}/infra/topology.json")',
                f'    frontend = root / "{slug}" / "frontend" / "index.html"',
                "    if not frontend.is_file():",
                f'        problems.append("missing frontend entry: {slug}/frontend/index.html")',
                "    if not (root / DESCRIPTOR).is_file():",
                '        problems.append(f"missing deployment descriptor: {DESCRIPTOR}")',
                "    return problems",
                "",
                "",
                'if __name__ == "__main__":',
                "    import argparse",
                "",
                '    parser = argparse.ArgumentParser(description="Run deployment preflight against a bundle")',
                '    parser.add_argument("--root", default=".", help="bundle root containing the system directory")',
                "    args = parser.parse_args()",
                "    found = preflight(Path(args.root))",
                "    for problem in found:",
                "        print(problem)",
                "    raise SystemExit(1 if found else 0)",
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
                "import pytest",
                "",
                f"from {slug}.deploy.plan import load_deployment, preflight, rollout_steps",
                "",
                "ROOT = Path(__file__).resolve().parents[3]",
                "",
                "",
                "def test_deployment_declares_environments_and_strategy():",
                "    deployment = load_deployment(ROOT)",
                f'    assert deployment["system"] == "{slug}"',
                '    assert deployment["strategy"] in (',
                '        "all_at_once", "rolling", "blue_green", "canary"',
                "    )",
                '    assert "staging" in deployment["environments"]',
                '    assert "production" in deployment["environments"]',
                '    assert deployment["zero_downtime_required"] is True',
                '    assert len(deployment["services"]) == len(set(deployment["services"]))',
                "",
                "",
                "def test_rolling_plan_gates_traffic_on_health():",
                '    steps = rollout_steps("rolling", True)',
                '    assert steps[0] == "preflight"',
                '    assert steps[-1] == "post-checks"',
                '    assert steps.index("start-replacement") < steps.index("health-check")',
                '    assert steps.index("health-check") < steps.index("switch-traffic")',
                '    assert steps.index("switch-traffic") < steps.index("retire-old")',
                "",
                "",
                "def test_zero_downtime_false_uses_replacement_swap():",
                '    steps = rollout_steps("rolling", False)',
                '    assert "health-check" not in steps',
                '    assert steps.index("stop-old") < steps.index("start-new")',
                "",
                "",
                "def test_alternate_strategies_are_planned():",
                '    assert "switch-traffic" in rollout_steps("blue_green", True)',
                '    assert "canary-10" in rollout_steps("canary", True)',
                '    assert "replace-all" in rollout_steps("all_at_once", True)',
                "",
                "",
                "def test_unknown_strategy_is_rejected():",
                '    with pytest.raises(ValueError):',
                '        rollout_steps("sideways", True)',
                "",
                "",
                "def test_preflight_passes_against_materialized_tree():",
                "    assert preflight(ROOT) == []",
                "",
                "",
                "def test_preflight_fails_when_entrypoint_is_absent(tmp_path):",
                "    problems = preflight(tmp_path)",
                "    assert any(\"missing entrypoint\" in problem for problem in problems)",
                "",
                "",
                "def test_deployment_services_match_infrastructure_topology():",
                "    deployment = load_deployment(ROOT)",
                "    topology = json.loads(",
                f'        (ROOT / "{slug}" / "infra" / "topology.json").read_text(',
                '            encoding="utf-8"',
                "        )",
                "    )",
                '    assert deployment["services"] == [',
                '        service["name"] for service in topology["services"]',
                "    ]",
                "",
            ]
        )

    def _manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            backend_id=self.backend_id,
            capabilities=[
                BundleCapability.DEPLOY,
                BundleCapability.BUILD,
                BundleCapability.TEST,
                BundleCapability.RELEASE,
            ],
            metadata={"language": "python", "style": "rollout-plan"},
        )
