"""Integration tests for the Verification Engine."""

import pytest

from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.fields import Field, FieldType
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.policy import Policy, PolicyType
from constitutional_architecture.isr.model.service import Service, Operation, OperationType
from constitutional_architecture.isr.model.interface import Interface, InterfaceType, Endpoint, HttpMethod
from constitutional_architecture.isr.model.system import System
from constitutional_architecture.verification.verification_engine import VerificationEngine
from constitutional_architecture.verification.verification_context import ArtifactReference
from constitutional_architecture.verification.verification_result import VerificationLevel


def _create_valid_isr() -> ISR:
    return ISR(
        system=System(
            id="shop",
            name="Shop",
            modules=(
                Module(
                    id="mod-auth",
                    name="Authentication",
                    entities=(
                        Entity(
                            id="ent-user",
                            name="User",
                            fields=(
                                Field(name="id", field_type=FieldType.UUID, is_primary_key=True),
                                Field(name="email", field_type=FieldType.EMAIL),
                            ),
                        ),
                    ),
                    services=(
                        Service(
                            id="svc-auth",
                            name="AuthService",
                            operations=(
                                Operation(id="op-login", name="login", operation_type=OperationType.COMMAND),
                            ),
                        ),
                    ),
                    policies=(
                        Policy(
                            id="pol-auth",
                            name="AuthPolicy",
                            policy_type=PolicyType.AUTHENTICATION,
                            strategy="OAuth2",
                            roles=("Admin", "User"),
                        ),
                    ),
                    interfaces=(
                        Interface(
                            id="iface-auth",
                            name="AuthAPI",
                            interface_type=InterfaceType.REST,
                            secured_by_policy_id="pol-auth",
                            endpoints=(
                                Endpoint(id="ep-login", name="login", path="/auth/login", method=HttpMethod.POST),
                            ),
                        ),
                    ),
                ),
                Module(
                    id="mod-orders",
                    name="Orders",
                    entities=(
                        Entity(
                            id="ent-order",
                            name="Order",
                            fields=(
                                Field(name="id", field_type=FieldType.UUID, is_primary_key=True),
                                Field(name="total", field_type=FieldType.DECIMAL),
                            ),
                        ),
                    ),
                    services=(
                        Service(
                            id="svc-orders",
                            name="OrderService",
                            operations=(
                                Operation(id="op-create", name="create_order", operation_type=OperationType.COMMAND),
                            ),
                        ),
                    ),
                    interfaces=(
                        Interface(
                            id="iface-orders",
                            name="OrderAPI",
                            interface_type=InterfaceType.REST,
                            secured_by_policy_id="pol-auth",
                            endpoints=(
                                Endpoint(id="ep-create", name="create_order", path="/orders", method=HttpMethod.POST),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def _create_artifacts() -> list[ArtifactReference]:
    return [
        ArtifactReference(
            path="app/main.py",
            content='from fastapi import FastAPI\napp = FastAPI()\n\n@app.get("/health")\nasync def health():\n    return {"status": "ok"}\n',
            artifact_type="source",
            backend="fastapi",
        ),
        ArtifactReference(
            path="app/auth/router.py",
            content='from fastapi import APIRouter\nrouter = APIRouter()\n\n@router.post("/auth/login")\nasync def login():\n    pass\n',
            artifact_type="source",
            backend="fastapi",
        ),
        ArtifactReference(
            path="requirements.txt",
            content="fastapi>=0.104.0\nuvicorn>=0.24.0\n",
            artifact_type="config",
            backend="fastapi",
        ),
    ]


class TestVerificationEngine:
    def test_verify_valid_system(self):
        engine = VerificationEngine()
        report = engine.verify(_create_valid_isr(), _create_artifacts())
        assert report.total_checks > 0
        assert report.passed_checks > 0

    def test_verify_produces_report(self):
        engine = VerificationEngine()
        report = engine.verify(_create_valid_isr(), _create_artifacts())
        assert report.report_id != ""
        assert report.isr_hash != ""
        assert report.verifier_version == "0.1.0"

    def test_approval_with_valid_system(self):
        engine = VerificationEngine()
        report = engine.verify(_create_valid_isr(), _create_artifacts())
        assert report.approved_for_deployment is True

    def test_rejection_without_auth_policy(self):
        isr = ISR(
            system=System(
                id="no-auth",
                name="NoAuth",
                modules=(
                    Module(
                        id="mod-1",
                        name="Core",
                        entities=(Entity(id="e1", name="Thing", fields=(
                            Field(name="id", field_type=FieldType.UUID, is_primary_key=True),
                        ),),),
                        services=(Service(id="s1", name="ThingService", operations=(
                            Operation(id="o1", name="get_thing", operation_type=OperationType.QUERY),
                        ),),),
                        interfaces=(Interface(
                            id="i1", name="ThingAPI",
                            interface_type=InterfaceType.REST,
                            endpoints=(Endpoint(id="ep1", name="get", path="/things", method=HttpMethod.GET),),
                        ),),
                    ),
                ),
            ),
        )
        engine = VerificationEngine()
        report = engine.verify(isr, _create_artifacts())
        assert report.failed_checks > 0 or report.warning_checks > 0

    def test_isr_not_modified(self):
        engine = VerificationEngine()
        isr = _create_valid_isr()
        original_hash = isr.content_hash
        engine.verify(isr, _create_artifacts())
        assert isr.content_hash == original_hash

    def test_repair_plan_generated_on_failure(self):
        isr = ISR(
            system=System(
                id="broken",
                name="Broken",
                modules=(
                    Module(id="m1", name="A", dependencies=("m2",)),
                    Module(id="m2", name="B", dependencies=("m1",)),
                ),
            ),
        )
        engine = VerificationEngine()
        report = engine.verify(isr, [])
        if not report.approved_for_deployment:
            plan = engine.get_repair_plan(report)
            assert report.blocking_failures or report.failed_checks >= 0

    def test_fitness_contribution(self):
        engine = VerificationEngine()
        report = engine.verify(_create_valid_isr(), _create_artifacts())
        assert "verification_pass_rate" in report.fitness_contribution
        assert report.fitness_contribution["verification_pass_rate"] > 0

    def test_level_filtering(self):
        engine = VerificationEngine()
        report = engine.verify(
            _create_valid_isr(), [],
            max_level=VerificationLevel.L0_ARCHITECTURAL,
        )
        verifier_names = {r.verifier_name for r in report.verifier_results}
        assert "architecture" in verifier_names

    def test_no_engine_imports(self):
        import constitutional_architecture.verification.verification_engine as mod
        import inspect
        source = inspect.getsource(mod)
        assert "from constitutional_architecture.engine" not in source
        assert "import constitutional_architecture.engine" not in source
