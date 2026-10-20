"""Deployment targets must not fabricate success without a real executor.

Regression for D04: the Kubernetes target (and its Docker/local siblings)
previously returned a hardcoded endpoint and a ``healthy`` status without
contacting any runtime. Success is now only reportable by an injected
``TargetExecutor``; the default fails closed and health is ``unknown``.
"""

from __future__ import annotations

import pytest

from constitutional_architecture.deployment.deployment_result import (
    DeploymentArtifact,
    HealthCheckResult,
)
from constitutional_architecture.deployment.targets.docker_target import DockerTarget
from constitutional_architecture.deployment.targets.kubernetes_target import KubernetesTarget
from constitutional_architecture.deployment.targets.local_target import LocalTarget
from constitutional_architecture.deployment.targets.target_interface import TargetResult

TARGET_CASES = [
    (DockerTarget, "container_image", "docker"),
    (KubernetesTarget, "container_image", "kubernetes"),
    (LocalTarget, "build", "local"),
]


class _Executor:
    def __init__(
        self,
        result: TargetResult,
        health: HealthCheckResult | None = None,
    ) -> None:
        self.result = result
        self.health = health or HealthCheckResult(
            endpoint="https://runtime.example/app/health",
            status="healthy",
            response_time_ms=1.5,
            details="Probe executed by injected adapter",
        )
        self.deploy_calls: list[DeploymentArtifact] = []
        self.cleaned = False

    def deploy(self, artifact: DeploymentArtifact) -> TargetResult:
        self.deploy_calls.append(artifact)
        return self.result

    def health_check(self) -> HealthCheckResult:
        return self.health

    def cleanup(self) -> None:
        self.cleaned = True


def _artifact(artifact_type: str) -> DeploymentArtifact:
    return DeploymentArtifact(
        artifact_type=artifact_type,
        name="app",
        location="./dist/app",
    )


@pytest.mark.parametrize("target_cls,artifact_type,target_name", TARGET_CASES)
def test_target_without_executor_fails_closed(target_cls, artifact_type, target_name):
    target = target_cls()

    result = target.deploy(_artifact(artifact_type))

    assert target.name == target_name
    assert result.success is False
    assert result.endpoint == ""
    assert result.deployed_artifacts == ()
    assert result.health is None
    assert "executor" in result.error.lower()
    assert result.diagnostics


@pytest.mark.parametrize("target_cls,artifact_type,target_name", TARGET_CASES)
def test_target_without_executor_reports_unknown_health(target_cls, artifact_type, target_name):
    health = target_cls().health_check()

    assert health.status == "unknown"
    assert health.endpoint == ""
    assert "not healthy" in health.details


@pytest.mark.parametrize("target_cls,artifact_type,target_name", TARGET_CASES)
def test_target_rejects_wrong_artifact_type(target_cls, artifact_type, target_name):
    wrong_type = "build" if artifact_type == "container_image" else "container_image"
    executor = _Executor(TargetResult(success=True, endpoint="https://runtime.example/app"))
    target = target_cls(executor=executor)

    result = target.deploy(_artifact(wrong_type))

    assert result.success is False
    assert "Cannot deploy" in result.error
    assert executor.deploy_calls == []


@pytest.mark.parametrize("target_cls,artifact_type,target_name", TARGET_CASES)
def test_injected_executor_owns_deployment_evidence(target_cls, artifact_type, target_name):
    artifact = _artifact(artifact_type)
    endpoint = f"https://{target_name}.example/app"
    executor = _Executor(
        TargetResult(
            success=True,
            endpoint=endpoint,
            deployed_artifacts=(artifact,),
        )
    )
    target = target_cls(executor=executor)

    result = target.deploy(artifact)

    assert result is executor.result
    assert result.success is True
    assert result.endpoint == endpoint
    assert result.deployed_artifacts == (artifact,)
    assert executor.deploy_calls == [artifact]
    assert target.health_check() is executor.health

    target.cleanup()
    assert executor.cleaned is True


@pytest.mark.parametrize("target_cls,artifact_type,target_name", TARGET_CASES)
def test_executor_success_without_endpoint_is_rejected(target_cls, artifact_type, target_name):
    executor = _Executor(TargetResult(success=True, endpoint=""))
    target = target_cls(executor=executor)

    result = target.deploy(_artifact(artifact_type))

    assert result.success is False
    assert "without an endpoint" in result.error


@pytest.mark.parametrize("target_cls,artifact_type,target_name", TARGET_CASES)
def test_executor_failure_is_propagated(target_cls, artifact_type, target_name):
    executor = _Executor(TargetResult(success=False, error="runtime unreachable"))
    target = target_cls(executor=executor)

    result = target.deploy(_artifact(artifact_type))

    assert result.success is False
    assert result.error == "runtime unreachable"


@pytest.mark.parametrize("target_cls,artifact_type,target_name", TARGET_CASES)
def test_cleanup_without_executor_is_a_noop(target_cls, artifact_type, target_name):
    target_cls().cleanup()
