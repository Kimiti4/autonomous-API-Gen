"""Integration tests for the Deployment Engine."""

import pytest

from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.fields import Field, FieldType
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.service import Service, Operation, OperationType
from constitutional_architecture.isr.model.system import System

from constitutional_architecture.deployment.deployment_context import DeploymentContext
from constitutional_architecture.deployment.deployment_engine import DeploymentEngine
from constitutional_architecture.deployment.deployment_pipeline import DeploymentPipeline
from constitutional_architecture.deployment.deployment_result import DeploymentResult, DeploymentStatus, DeploymentArtifact, HealthCheckResult
from constitutional_architecture.deployment.deployment_events import DeploymentEventType
from constitutional_architecture.deployment.deployment_registry import DeploymentRegistry
from constitutional_architecture.deployment.environment_manager import EnvironmentManager, EnvironmentTier, EnvironmentConfig
from constitutional_architecture.deployment.stages.build_stage import BuildStage
from constitutional_architecture.deployment.stages.package_stage import PackageStage
from constitutional_architecture.deployment.stages.container_stage import ContainerStage
from constitutional_architecture.deployment.stages.infrastructure_stage import InfrastructureStage
from constitutional_architecture.deployment.stages.provision_stage import ProvisionStage
from constitutional_architecture.deployment.stages.deploy_stage import DeployStage
from constitutional_architecture.deployment.stages.health_stage import HealthStage
from constitutional_architecture.deployment.stages.stage_interface import DeploymentStage, StageResult
from constitutional_architecture.deployment.targets.docker_target import DockerTarget
from constitutional_architecture.deployment.targets.kubernetes_target import KubernetesTarget
from constitutional_architecture.deployment.targets.local_target import LocalTarget
from constitutional_architecture.deployment.targets.target_interface import DeploymentTarget, TargetResult
from constitutional_architecture.deployment.rollout.rollout_manager import RolloutManager, RolloutConfig, RolloutStrategy, RolloutPlan
from constitutional_architecture.deployment.rollout.rollback_manager import RollbackManager, RollbackConfig, RollbackReason
from constitutional_architecture.deployment.rollout.promotion_manager import PromotionManager, PromotionConfig, PromotionEnvironment
from constitutional_architecture.deployment.health.health_monitor import HealthMonitor, HealthCheckConfig, HealthStatus


def _make_isr() -> ISR:
    return ISR(
        system=System(
            id="test-app",
            name="TestApp",
            modules=(
                Module(
                    id="mod-main",
                    name="Main",
                    entities=(
                        Entity(
                            id="ent-item",
                            name="Item",
                            fields=(
                                Field(name="id", field_type=FieldType.UUID, is_primary_key=True),
                                Field(name="name", field_type=FieldType.STRING),
                            ),
                        ),
                    ),
                    services=(
                        Service(
                            id="svc-api",
                            name="ApiService",
                            operations=(
                                Operation(id="op-get", name="getItem", operation_type=OperationType.QUERY),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def _make_empty_isr() -> ISR:
    return ISR(
        system=System(
            id="empty-app",
            name="EmptyApp",
            modules=(),
        ),
    )


# ---------------------------------------------------------------------------
# Pipeline stage tests
# ---------------------------------------------------------------------------

class TestPipelineStages:
    def test_build_stage_success(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        stage = BuildStage()
        result = stage.execute(ctx)
        assert result.success
        assert result.stage_name == "build"
        assert len(result.artifacts) > 0

    def test_build_stage_no_source(self):
        isr = _make_empty_isr()
        ctx = DeploymentContext(isr=isr)
        stage = BuildStage()
        result = stage.execute(ctx)
        assert not result.success

    def test_package_stage_needs_build(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        stage = PackageStage()
        result = stage.execute(ctx)
        assert not result.success
        assert "Build stage" in result.error

    def test_container_stage_needs_package(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        stage = ContainerStage()
        result = stage.execute(ctx)
        assert not result.success

    def test_provision_stage_needs_infrastructure(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        stage = ProvisionStage()
        result = stage.execute(ctx)
        assert not result.success

    def test_deploy_stage_needs_provision_and_containerize(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        stage = DeployStage()
        result = stage.execute(ctx)
        assert not result.success

    def test_health_stage_needs_deploy(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        stage = HealthStage()
        result = stage.execute(ctx)
        assert not result.success

    def test_infrastructure_stage_success(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        stage = InfrastructureStage()
        result = stage.execute(ctx)
        assert result.success
        assert len(result.artifacts) > 0


# ---------------------------------------------------------------------------
# PIPELINE
# ---------------------------------------------------------------------------

class TestPipeline:
    def test_ordered_execution(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        pipeline = DeploymentPipeline()
        pipeline.register_stage(BuildStage())
        pipeline.register_stage(PackageStage())
        pipeline.register_stage(InfrastructureStage())
        pipeline.register_stage(ProvisionStage())
        pipeline.register_stage(ContainerStage())
        pipeline.register_stage(DeployStage())
        pipeline.register_stage(HealthStage())

        result = pipeline.execute(ctx)
        assert result.status == DeploymentStatus.RUNNING, str(result.metadata)

    def test_no_stages_fails(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        pipeline = DeploymentPipeline()
        result = pipeline.execute(ctx)
        assert result.status == DeploymentStatus.FAILED

    def test_stage_failure_halts_pipeline(self):
        class FailingStage(DeploymentStage):
            @property
            def name(self): return "fail"
            @property
            def description(self): return "Always fails"
            def execute(self, ctx):
                return StageResult(stage_name="fail", success=False, error="Intentional failure")

        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        pipeline = DeploymentPipeline()
        pipeline.register_stage(BuildStage())
        pipeline.register_stage(FailingStage())
        result = pipeline.execute(ctx)
        assert result.status == DeploymentStatus.FAILED
        assert "fail" in str(result.metadata)


# ---------------------------------------------------------------------------
# TARGETS
# ---------------------------------------------------------------------------

class TestTargets:
    def test_docker_deploy(self):
        target = DockerTarget()
        artifact = DeploymentArtifact(artifact_type="container_image", name="img:latest", location="reg/img")
        result = target.deploy(artifact)
        assert result.success
        assert "localhost" in result.endpoint

    def test_docker_rejects_non_container(self):
        target = DockerTarget()
        artifact = DeploymentArtifact(artifact_type="build", name="output.tar", location="./out")
        result = target.deploy(artifact)
        assert not result.success

    def test_kubernetes_deploy(self):
        target = KubernetesTarget()
        artifact = DeploymentArtifact(artifact_type="container_image", name="img:stable", location="reg/img")
        result = target.deploy(artifact)
        assert result.success
        assert "k8s" in result.endpoint

    def test_local_deploy(self):
        target = LocalTarget()
        artifact = DeploymentArtifact(artifact_type="build", name="local-app", location="./out")
        result = target.deploy(artifact)
        assert result.success

    def test_health_check(self):
        target = DockerTarget()
        hc = target.health_check()
        assert hc.status == "healthy"
        assert hc.response_time_ms >= 0


# ---------------------------------------------------------------------------
# ROLLOUT
# ---------------------------------------------------------------------------

class TestRollout:
    def test_create_plan(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        mgr = RolloutManager()
        plan = mgr.create_plan(ctx)
        assert plan.rollout_id is not None
        assert plan.status == "pending"

    def test_immediate_execution(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        mgr = RolloutManager()
        plan = mgr.create_plan(ctx, RolloutConfig(strategy=RolloutStrategy.IMMEDIATE))
        result = mgr.execute_plan(plan, ctx)
        assert result.status == DeploymentStatus.RUNNING

    def test_canary_execution(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        mgr = RolloutManager()
        plan = mgr.create_plan(ctx, RolloutConfig(strategy=RolloutStrategy.CANARY, canary_percent=25.0))
        result = mgr.execute_plan(plan, ctx)
        assert result.status == DeploymentStatus.RUNNING

    def test_canary_invalid_percent(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        mgr = RolloutManager()
        plan = mgr.create_plan(ctx, RolloutConfig(strategy=RolloutStrategy.CANARY, canary_percent=0.0))
        result = mgr.execute_plan(plan, ctx)
        assert result.status == DeploymentStatus.FAILED

    def test_rolling_execution(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        mgr = RolloutManager()
        plan = mgr.create_plan(ctx, RolloutConfig(strategy=RolloutStrategy.ROLLING, rolling_batch_size=2))
        result = mgr.execute_plan(plan, ctx)
        assert result.status == DeploymentStatus.RUNNING

    def test_rolling_invalid_batch(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        mgr = RolloutManager()
        plan = mgr.create_plan(ctx, RolloutConfig(strategy=RolloutStrategy.ROLLING, rolling_batch_size=0))
        result = mgr.execute_plan(plan, ctx)
        assert result.status == DeploymentStatus.FAILED

    def test_get_plan(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        mgr = RolloutManager()
        plan = mgr.create_plan(ctx)
        retrieved = mgr.get_plan(plan.rollout_id)
        assert retrieved is not None
        assert retrieved.rollout_id == plan.rollout_id

    def test_get_plan_missing(self):
        mgr = RolloutManager()
        assert mgr.get_plan("nonexistent") is None


# ---------------------------------------------------------------------------
# ROLLBACK
# ---------------------------------------------------------------------------

class TestRollback:
    def test_rollback_with_history(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        ctx.deployment_history.append(
            DeploymentResult(status=DeploymentStatus.RUNNING, version="v1.0.0")
        )
        mgr = RollbackManager()
        result = mgr.rollback(ctx, RollbackReason.HEALTH_CHECK_FAILURE)
        assert result.status == DeploymentStatus.RUNNING

    def test_rollback_no_history(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        mgr = RollbackManager(RollbackConfig(auto_rollback=True))
        result = mgr.rollback(ctx, RollbackReason.MANUAL_INTERVENTION)
        assert result.status == DeploymentStatus.FAILED

    def test_rollback_disabled(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        mgr = RollbackManager(RollbackConfig(auto_rollback=False))
        result = mgr.rollback(ctx)
        assert result.status == DeploymentStatus.FAILED

    def test_get_history(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        ctx.deployment_history.append(
            DeploymentResult(status=DeploymentStatus.RUNNING, version="v1.0.0")
        )
        mgr = RollbackManager()
        mgr.rollback(ctx)
        history = mgr.get_history()
        assert len(history) >= 1


# ---------------------------------------------------------------------------
# PROMOTION
# ---------------------------------------------------------------------------

class TestPromotion:
    def test_promote_success(self):
        mgr = PromotionManager()
        result = mgr.promote("v1.0.0", PromotionEnvironment.DEVELOPMENT, PromotionEnvironment.STAGING)
        assert result

    def test_promote_production_blocked(self):
        mgr = PromotionManager(PromotionConfig(require_approval=True))
        result = mgr.promote("v1.0.0", PromotionEnvironment.STAGING, PromotionEnvironment.PRODUCTION)
        assert not result

    def test_promote_too_many_jumps(self):
        mgr = PromotionManager(PromotionConfig(allowed_jumps=1))
        result = mgr.promote("v1.0.0", PromotionEnvironment.DEVELOPMENT, PromotionEnvironment.PRODUCTION)
        assert not result

    def test_get_history(self):
        mgr = PromotionManager()
        mgr.promote("v1.0.0", PromotionEnvironment.DEVELOPMENT, PromotionEnvironment.STAGING)
        history = mgr.get_promotion_history()
        assert len(history) == 1
        assert history[0]["version"] == "v1.0.0"


# ---------------------------------------------------------------------------
# HEALTH MONITOR
# ---------------------------------------------------------------------------

class TestHealthMonitor:
    def test_check_success(self):
        monitor = HealthMonitor()
        result = monitor.check("/health")
        assert result.status == "healthy"
        assert result.response_time_ms >= 0

    def test_get_latest(self):
        monitor = HealthMonitor()
        monitor.check("/health")
        latest = monitor.get_latest()
        assert latest is not None
        assert latest.endpoint == "/health"

    def test_get_latest_empty(self):
        monitor = HealthMonitor()
        assert monitor.get_latest() is None

    def test_get_history(self):
        monitor = HealthMonitor()
        monitor.check("/health")
        monitor.check("/ready")
        assert len(monitor.get_history()) == 2

    def test_average_response_time(self):
        monitor = HealthMonitor()
        assert monitor.get_average_response_time() == 0.0
        monitor.check("/health")
        assert monitor.get_average_response_time() > 0


# ---------------------------------------------------------------------------
# ENVIRONMENT MANAGER
# ---------------------------------------------------------------------------

class TestEnvironmentManager:
    def test_list_environments(self):
        mgr = EnvironmentManager()
        mgr.register_environment(EnvironmentConfig(tier=EnvironmentTier.STAGING, name="staging"))
        envs = mgr.registered_environments
        assert len(envs) == 1

    def test_register_environment(self):
        mgr = EnvironmentManager()
        config = EnvironmentConfig(tier=EnvironmentTier.STAGING, name="staging")
        mgr.register_environment(config)
        envs = mgr.registered_environments
        assert EnvironmentTier.STAGING in envs

    def test_get_environment(self):
        mgr = EnvironmentManager()
        config = EnvironmentConfig(tier=EnvironmentTier.STAGING, name="staging")
        mgr.register_environment(config)
        env = mgr.get_environment(EnvironmentTier.STAGING)
        assert env is not None
        assert env.name == "staging"

    def test_get_environment_missing(self):
        mgr = EnvironmentManager()
        assert mgr.get_environment(EnvironmentTier.PRODUCTION) is None

    def test_promotion_validation(self):
        mgr = EnvironmentManager()
        from constitutional_architecture.verification.verification_result import VerificationLevel
        ok, msg = mgr.can_promote(
            "dep-1",
            EnvironmentTier.DEVELOPMENT,
            EnvironmentTier.SANDBOX,
            VerificationLevel.L4_PERFORMANCE,
        )
        assert ok

    def test_cannot_skip_tier(self):
        mgr = EnvironmentManager()
        from constitutional_architecture.verification.verification_result import VerificationLevel
        ok, msg = mgr.can_promote(
            "dep-2",
            EnvironmentTier.DEVELOPMENT,
            EnvironmentTier.PRODUCTION,
            VerificationLevel.L5_OPERATIONAL,
        )
        assert not ok


# ---------------------------------------------------------------------------
# DEPLOYMENT CONTEXT
# ---------------------------------------------------------------------------

class TestDeploymentContext:
    def test_artifacts_populated(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        artifacts = ctx.verified_system.artifacts
        assert len(artifacts) >= 0

    def test_get_stage_result_missing(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        assert ctx.get_stage_result("nonexistent") is None

    def test_record_stage_result(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        sr = StageResult(stage_name="test", success=True)
        ctx.record_stage_result(sr)
        retrieved = ctx.get_stage_result("test")
        assert retrieved is not None
        assert retrieved.success

    def test_deployment_history(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        assert len(ctx.deployment_history) == 0

    def test_metadata(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr, metadata={"key": "value"})
        assert ctx.metadata["key"] == "value"


# ---------------------------------------------------------------------------
# ENGINE INTEGRATION
# ---------------------------------------------------------------------------

class TestEngineIntegration:
    def test_full_deploy_success(self):
        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        engine = DeploymentEngine()
        pipeline = engine.pipeline
        pipeline.register_stage(BuildStage())
        pipeline.register_stage(PackageStage())
        pipeline.register_stage(InfrastructureStage())
        pipeline.register_stage(ProvisionStage())
        pipeline.register_stage(ContainerStage())
        pipeline.register_stage(DeployStage())
        pipeline.register_stage(HealthStage())

        result = engine.deploy(ctx)
        assert result.status == DeploymentStatus.RUNNING
        assert "TestApp" in str(result.metadata)

    def test_deploy_failure_propagates(self):
        class FailingStage(DeploymentStage):
            @property
            def name(self): return "fail"
            @property
            def description(self): return "Always fails"
            def execute(self, ctx):
                return StageResult(stage_name="fail", success=False, error="Intentional failure")

        isr = _make_isr()
        ctx = DeploymentContext(isr=isr)
        engine = DeploymentEngine()
        pipeline = engine.pipeline
        pipeline.register_stage(BuildStage())
        pipeline.register_stage(FailingStage())

        result = engine.deploy(ctx)
        assert result.status == DeploymentStatus.FAILED

    def test_engine_properties(self):
        engine = DeploymentEngine()
        assert engine.pipeline is not None
        assert engine.env_manager is not None
        assert engine.rollout is not None
        assert engine.rollback is not None
        assert engine.promotion is not None
        assert engine.health is not None

    def test_registry(self):
        registry = DeploymentRegistry()
        stage = BuildStage()
        registry.register_stage(stage)
        assert registry.get_stage("build") is stage
        assert "build" in registry.list_stages()
        registry.clear()
        assert "build" not in registry.list_stages()

    def test_artifact_creation(self):
        art = DeploymentArtifact(
            artifact_type="container_image",
            name="img:v1",
            location="reg/img:v1",
            metadata={"sha": "abc123"},
        )
        assert art.artifact_type == "container_image"
        assert art.metadata["sha"] == "abc123"

    def test_health_check_result_creation(self):
        hc = HealthCheckResult(
            endpoint="/health",
            status="healthy",
            response_time_ms=10.0,
            details="OK",
        )
        assert hc.status == "healthy"
        assert hc.response_time_ms == 10.0
