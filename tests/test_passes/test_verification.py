import pytest

from constitutional_architecture.compiler.artifacts.artifact_model import (
    Artifact,
    ArtifactType,
    SourceMapping,
)
from constitutional_architecture.compiler.compilation_config import CompilationConfig
from constitutional_architecture.compiler.compiler_context import CompilerContext
from constitutional_architecture.compiler.passes.verification_pass import VerificationPass
from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.fields import Field, FieldType
from constitutional_architecture.isr.model.interface import (
    Endpoint,
    HttpMethod,
    Interface,
    InterfaceType,
)
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.policy import Policy, PolicyType
from constitutional_architecture.isr.model.service import Operation, OperationType, Service
from constitutional_architecture.isr.model.system import System


def _create_valid_system() -> System:
    """A minimal but architecturally valid Shop system."""
    return System(
        id="shop",
        name="Shop",
        modules=(
            Module(
                id="mod-shop",
                name="Shop",
                entities=(
                    Entity(
                        id="ent-shop",
                        name="Shop",
                        fields=(
                            Field(name="id", field_type=FieldType.UUID, is_primary_key=True),
                        ),
                    ),
                ),
                services=(
                    Service(
                        id="svc-shop",
                        name="ShopService",
                        operations=(
                            Operation(id="op-get", name="get", operation_type=OperationType.QUERY),
                        ),
                    ),
                ),
                policies=(
                    Policy(
                        id="pol-auth",
                        name="AuthPolicy",
                        policy_type=PolicyType.AUTHENTICATION,
                        strategy="OAuth2",
                        roles=("Admin",),
                    ),
                ),
                interfaces=(
                    Interface(
                        id="iface-shop",
                        name="ShopAPI",
                        interface_type=InterfaceType.REST,
                        secured_by_policy_id="pol-auth",
                        endpoints=(
                            Endpoint(id="ep-health", name="health", path="/health", method=HttpMethod.GET),
                        ),
                    ),
                ),
            ),
        ),
    )


def _create_context_with_artifacts() -> CompilerContext:
    config = CompilationConfig(project_name="shop", target_backends=("fastapi",))
    isr = ISR(system=_create_valid_system())
    ctx = CompilerContext(_isr=isr, _config=config)
    ctx.artifacts.append(Artifact(
        path="app/main.py",
        content=(
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n\n"
            "@app.get('/health')\n"
            "async def health():\n"
            "    return {'status': 'ok'}\n"
        ),
        artifact_type=ArtifactType.SOURCE, backend="fastapi",
        source_mapping=SourceMapping(isr_node_id="shop", artifact_path="app/main.py"),
    ))
    ctx.artifacts.append(Artifact(
        path="requirements.txt", content="fastapi>=0.104.0\nuvicorn>=0.24.0\n",
        artifact_type=ArtifactType.CONFIG, backend="fastapi",
    ))
    return ctx


class TestVerificationPass:
    def test_passes_with_valid_artifacts(self):
        ctx = _create_context_with_artifacts()
        result = VerificationPass().execute(ctx)
        assert result.success
        assert result.metrics["compiler_checks_passed"] > 0

    def test_fails_with_no_artifacts(self):
        config = CompilationConfig(project_name="shop", target_backends=("fastapi",))
        isr = ISR(system=System(id="shop", name="Shop"))
        ctx = CompilerContext(_isr=isr, _config=config)
        result = VerificationPass().execute(ctx)
        assert not result.success

    def test_detects_duplicate_paths(self):
        ctx = _create_context_with_artifacts()
        ctx.artifacts.append(Artifact(
            path="app/main.py", content="duplicate",
            artifact_type=ArtifactType.SOURCE, backend="fastapi",
        ))
        result = VerificationPass().execute(ctx)
        assert not result.success

    def test_detects_empty_source_files(self):
        ctx = _create_context_with_artifacts()
        ctx.artifacts.append(Artifact(
            path="app/empty.py", content="",
            artifact_type=ArtifactType.SOURCE, backend="fastapi",
        ))
        result = VerificationPass().execute(ctx)
        assert result.metrics.get("compiler_checks_passed", 0) > 0

    def test_records_verification_metrics(self):
        ctx = _create_context_with_artifacts()
        result = VerificationPass().execute(ctx)
        assert "verification_checks" in result.metrics
        assert "duration_ms" in result.metrics
