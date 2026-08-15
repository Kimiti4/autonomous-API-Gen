import pytest

from constitutional_architecture.compiler.compilation_config import CompilationConfig
from constitutional_architecture.compiler.compiler_context import CompilerContext
from constitutional_architecture.compiler.passes.normalization_pass import NormalizationPass
from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.fields import Field, FieldCardinality, FieldType
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.policy import Policy, PolicyType
from constitutional_architecture.isr.model.service import Operation, OperationType, Service, ServiceDependency
from constitutional_architecture.isr.model.system import System


def _create_unsorted_isr() -> ISR:
    return ISR(
        system=System(
            id="shop", name="Shop",
            modules=(
                Module(
                    id="mod-orders", name="Orders",
                    entities=(
                        Entity(id="ent-order", name="Order", fields=(
                            Field(name="total", field_type=FieldType.DECIMAL, cardinality=FieldCardinality.REQUIRED),
                            Field(name="id", field_type=FieldType.UUID, is_primary_key=True, cardinality=FieldCardinality.REQUIRED),
                        )),
                        Entity(id="ent-item", name="OrderItem", fields=(
                            Field(name="id", field_type=FieldType.UUID, is_primary_key=True, cardinality=FieldCardinality.REQUIRED),
                        )),
                    ),
                    services=(
                        Service(
                            id="svc-orders", name="OrderService",
                            operations=(
                                Operation(id="op-get", name="get_order", operation_type=OperationType.QUERY),
                                Operation(id="op-create", name="create_order", operation_type=OperationType.COMMAND),
                            ),
                            dependencies=(
                                ServiceDependency(target_service_id="svc-payments"),
                                ServiceDependency(target_service_id="svc-auth"),
                            ),
                        ),
                    ),
                    metadata={"empty": "", "valid": "value"},
                ),
                Module(
                    id="mod-auth", name="Authentication",
                    entities=(), services=(),
                    policies=(
                        Policy(id="pol-auth", name="AuthPolicy", policy_type=PolicyType.AUTHENTICATION,
                               strategy="OAuth2", roles=("User", "Admin")),
                    ),
                ),
            ),
        ),
    )


class TestNormalizationPass:
    def test_sorts_modules_alphabetically(self):
        isr = _create_unsorted_isr()
        config = CompilationConfig(project_name="shop", target_backends=("fastapi",))
        ctx = CompilerContext(_isr=isr, _config=config)
        NormalizationPass().execute(ctx)
        assert ctx.isr.system.modules[0].name == "Authentication"
        assert ctx.isr.system.modules[1].name == "Orders"

    def test_sorts_entities_within_module(self):
        isr = _create_unsorted_isr()
        config = CompilationConfig(project_name="shop", target_backends=("fastapi",))
        ctx = CompilerContext(_isr=isr, _config=config)
        NormalizationPass().execute(ctx)
        orders = ctx.isr.system.modules[1]
        assert orders.entities[0].name == "Order"
        assert orders.entities[1].name == "OrderItem"

    def test_sorts_fields_within_entity(self):
        isr = _create_unsorted_isr()
        config = CompilationConfig(project_name="shop", target_backends=("fastapi",))
        ctx = CompilerContext(_isr=isr, _config=config)
        NormalizationPass().execute(ctx)
        entity = ctx.isr.system.modules[1].entities[0]
        assert entity.fields[0].name == "id"
        assert entity.fields[1].name == "total"

    def test_sorts_operations(self):
        isr = _create_unsorted_isr()
        config = CompilationConfig(project_name="shop", target_backends=("fastapi",))
        ctx = CompilerContext(_isr=isr, _config=config)
        NormalizationPass().execute(ctx)
        svc = ctx.isr.system.modules[1].services[0]
        assert svc.operations[0].name == "create_order"
        assert svc.operations[1].name == "get_order"

    def test_sorts_dependencies(self):
        isr = _create_unsorted_isr()
        config = CompilationConfig(project_name="shop", target_backends=("fastapi",))
        ctx = CompilerContext(_isr=isr, _config=config)
        NormalizationPass().execute(ctx)
        svc = ctx.isr.system.modules[1].services[0]
        assert svc.dependencies[0].target_service_id == "svc-auth"
        assert svc.dependencies[1].target_service_id == "svc-payments"

    def test_sorts_roles(self):
        isr = _create_unsorted_isr()
        config = CompilationConfig(project_name="shop", target_backends=("fastapi",))
        ctx = CompilerContext(_isr=isr, _config=config)
        NormalizationPass().execute(ctx)
        policy = ctx.isr.system.modules[0].policies[0]
        assert policy.roles[0] == "Admin"
        assert policy.roles[1] == "User"

    def test_removes_empty_metadata(self):
        isr = _create_unsorted_isr()
        config = CompilationConfig(project_name="shop", target_backends=("fastapi",))
        ctx = CompilerContext(_isr=isr, _config=config)
        NormalizationPass().execute(ctx)
        orders = ctx.isr.system.modules[1]
        assert "empty" not in orders.metadata
        assert orders.metadata.get("valid") == "value"

    def test_preserves_original_isr(self):
        isr = _create_unsorted_isr()
        original_hash = isr.content_hash
        config = CompilationConfig(project_name="shop", target_backends=("fastapi",))
        ctx = CompilerContext(_isr=isr, _config=config)
        NormalizationPass().execute(ctx)
        assert ctx.original_isr.content_hash == original_hash
        assert ctx.isr is not isr

    def test_deterministic_output(self):
        isr = _create_unsorted_isr()
        config = CompilationConfig(project_name="shop", target_backends=("fastapi",))
        ctx1 = CompilerContext(_isr=isr, _config=config)
        NormalizationPass().execute(ctx1)
        ctx2 = CompilerContext(_isr=isr, _config=config)
        NormalizationPass().execute(ctx2)
        assert ctx1.isr.content_hash == ctx2.isr.content_hash
