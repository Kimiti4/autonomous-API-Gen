"""Tests for ISR serialization and deserialization."""

import json

import pytest

from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.fields import Field, FieldType
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.service import Service, Operation, OperationType
from constitutional_architecture.isr.model.system import System
from constitutional_architecture.isr.serialization.serializer import ISRSerializer
from constitutional_architecture.isr.serialization.deserializer import ISRDeserializer


def _create_sample_isr() -> ISR:
    return ISR(
        system=System(
            id="shop-system",
            name="Shop",
            modules=(
                Module(
                    id="auth-module",
                    name="Authentication",
                    entities=(
                        Entity(
                            id="user-entity",
                            name="User",
                            fields=(
                                Field(name="id", field_type=FieldType.UUID, is_primary_key=True),
                                Field(name="email", field_type=FieldType.EMAIL),
                            ),
                        ),
                    ),
                    services=(
                        Service(
                            id="auth-service",
                            name="AuthService",
                            operations=(
                                Operation(id="op-1", name="login", operation_type=OperationType.COMMAND),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        version=1,
    )


class TestSerialization:
    def test_serialize_to_json(self):
        isr = _create_sample_isr()
        json_str = ISRSerializer.to_json(isr)
        data = json.loads(json_str)
        assert data["system"]["name"] == "Shop"
        assert len(data["system"]["modules"]) == 1

    def test_canonical_json_is_deterministic(self):
        isr = _create_sample_isr()
        json1 = ISRSerializer.to_canonical_json(isr)
        json2 = ISRSerializer.to_canonical_json(isr)
        assert json1 == json2

    def test_round_trip(self):
        isr = _create_sample_isr()
        json_str = ISRSerializer.to_json(isr)
        restored = ISRDeserializer.from_json(json_str)
        assert restored.system.name == "Shop"
        assert restored.system.modules[0].name == "Authentication"
        assert restored.system.modules[0].entities[0].name == "User"
        assert restored.system.modules[0].services[0].name == "AuthService"

    def test_content_hash_stability(self):
        isr = _create_sample_isr()
        hash1 = isr.content_hash
        hash2 = isr.content_hash
        assert hash1 == hash2
        assert len(hash1) == 64
