"""Tests for the ISR object model."""

import pytest

from constitutional_architecture.isr.model.entity import Entity, Relationship
from constitutional_architecture.isr.model.fields import Field, FieldCardinality, FieldType
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.service import Operation, OperationType, Service
from constitutional_architecture.isr.model.system import System
from constitutional_architecture.isr.model.workflow import Workflow, WorkflowState, WorkflowTransition, StateType
from constitutional_architecture.isr.model.policy import Policy, PolicyType
from constitutional_architecture.isr.model.interface import Interface, InterfaceType, Endpoint, HttpMethod


class TestField:
    def test_create_basic_field(self):
        field = Field(name="email", field_type=FieldType.EMAIL)
        assert field.name == "email"
        assert field.field_type == FieldType.EMAIL
        assert field.cardinality == FieldCardinality.REQUIRED

    def test_enum_field_requires_values(self):
        with pytest.raises(ValueError, match="ENUM but has no enum_values"):
            Field(name="status", field_type=FieldType.ENUM)

    def test_reference_field_requires_target(self):
        with pytest.raises(ValueError, match="REFERENCE but has no reference_target"):
            Field(name="user_id", field_type=FieldType.REFERENCE)

    def test_valid_enum_field(self):
        field = Field(
            name="status",
            field_type=FieldType.ENUM,
            enum_values=("active", "inactive", "suspended"),
        )
        assert len(field.enum_values) == 3


class TestEntity:
    def test_create_entity(self):
        entity = Entity(
            id="user-entity",
            name="User",
            fields=(
                Field(name="id", field_type=FieldType.UUID, is_primary_key=True),
                Field(name="email", field_type=FieldType.EMAIL),
            ),
        )
        assert entity.name == "User"
        assert len(entity.fields) == 2
        assert len(entity.primary_key_fields) == 1

    def test_get_field(self):
        entity = Entity(
            id="user-entity",
            name="User",
            fields=(
                Field(name="id", field_type=FieldType.UUID, is_primary_key=True),
                Field(name="email", field_type=FieldType.EMAIL),
            ),
        )
        assert entity.get_field("email") is not None
        assert entity.get_field("nonexistent") is None


class TestService:
    def test_create_service(self):
        service = Service(
            id="auth-service",
            name="AuthService",
            operations=(
                Operation(id="op-login", name="login", operation_type=OperationType.COMMAND),
                Operation(id="op-logout", name="logout", operation_type=OperationType.COMMAND),
            ),
            emitted_events=("UserAuthenticated",),
        )
        assert service.name == "AuthService"
        assert len(service.operations) == 2
        assert service.get_operation("login") is not None


class TestWorkflow:
    def test_create_workflow(self):
        workflow = Workflow(
            id="order-lifecycle",
            name="OrderLifecycle",
            states=(
                WorkflowState(id="s1", name="Pending", state_type=StateType.INITIAL),
                WorkflowState(id="s2", name="Confirmed", state_type=StateType.INTERMEDIATE),
                WorkflowState(id="s3", name="Delivered", state_type=StateType.FINAL),
            ),
            transitions=(
                WorkflowTransition(
                    id="t1", name="confirm",
                    from_state_id="s1", to_state_id="s2",
                    trigger="PaymentConfirmed",
                ),
            ),
        )
        assert len(workflow.initial_states) == 1
        assert len(workflow.final_states) == 1
        assert len(workflow.get_transitions_from("s1")) == 1


class TestISRImmutability:
    def test_isr_is_frozen(self):
        system = System(id="sys-1", name="TestSystem")
        isr = ISR(system=system)
        with pytest.raises(AttributeError):
            isr.version = 2

    def test_with_system_creates_new_version(self):
        system = System(id="sys-1", name="TestSystem")
        isr_v1 = ISR(system=system, version=1)

        new_system = System(id="sys-1", name="TestSystem", modules=(
            Module(id="mod-1", name="Auth"),
        ))
        isr_v2 = isr_v1.with_system(new_system)

        assert isr_v1.version == 1
        assert isr_v2.version == 2
        assert isr_v1.system.module_count == 0
        assert isr_v2.system.module_count == 1
        assert isr_v2.provenance.parent_hash == isr_v1.content_hash
