"""
ISR Deserializer.

Converts JSON back into the ISR object model.
"""

from __future__ import annotations

import json
from typing import Any

from constitutional_architecture.isr.model.constraints import Constraint, ConstraintScope, ConstraintSeverity
from constitutional_architecture.isr.model.deployment import (
    Deployment,
    EnvironmentTier,
    MonitoringConfig,
    NetworkingConfig,
    ScalingConfig,
    ScalingStrategy,
    SecretsConfig,
    StorageConfig,
)
from constitutional_architecture.isr.model.entity import Entity, Relationship
from constitutional_architecture.isr.model.event import Event, EventGuarantee, EventPattern
from constitutional_architecture.isr.model.fields import Field, FieldCardinality, FieldConstraint, FieldType
from constitutional_architecture.isr.model.interface import Endpoint, HttpMethod, Interface, InterfaceType
from constitutional_architecture.isr.model.isr import ISR, ISRProvenance
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.policy import Permission, Policy, PolicyRule, PolicyType
from constitutional_architecture.isr.model.service import Operation, OperationType, Service, ServiceDependency
from constitutional_architecture.isr.model.system import System, SystemMetadata
from constitutional_architecture.isr.model.workflow import Workflow, WorkflowState, WorkflowTransition, StateType


class ISRDeserializer:
    """Deserializes JSON into ISR object model."""

    @staticmethod
    def from_json(json_str: str) -> ISR:
        data = json.loads(json_str)
        return ISRDeserializer.from_dict(data)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ISR:
        system_data = data.get("system", {})
        system = ISRDeserializer._deserialize_system(system_data)

        provenance_data = data.get("provenance", {})
        provenance = ISRProvenance(
            created_by=provenance_data.get("created_by", ""),
            parent_hash=provenance_data.get("parent_hash"),
            mutation_description=provenance_data.get("mutation_description", ""),
            evolution_run_id=provenance_data.get("evolution_run_id"),
            generation=provenance_data.get("generation", 0),
        )

        return ISR(
            system=system,
            version=data.get("version", 1),
            provenance=provenance,
        )

    @staticmethod
    def _deserialize_system(data: dict[str, Any]) -> System:
        modules = tuple(
            ISRDeserializer._deserialize_module(m) for m in data.get("modules", [])
        )
        deployment = None
        if data.get("deployment"):
            deployment = ISRDeserializer._deserialize_deployment(data["deployment"])

        metadata_data = data.get("metadata", {})
        metadata = SystemMetadata(
            version=metadata_data.get("version", "1.0"),
            authors=tuple(metadata_data.get("authors", [])),
            license=metadata_data.get("license", ""),
            description=metadata_data.get("description", ""),
            tags=tuple(metadata_data.get("tags", [])),
        )

        return System(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            modules=modules,
            deployment=deployment,
            metadata=metadata,
            global_policies=tuple(data.get("global_policies", [])),
        )

    @staticmethod
    def _deserialize_module(data: dict[str, Any]) -> Module:
        return Module(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            entities=tuple(
                ISRDeserializer._deserialize_entity(e) for e in data.get("entities", [])
            ),
            services=tuple(
                ISRDeserializer._deserialize_service(s) for s in data.get("services", [])
            ),
            workflows=tuple(
                ISRDeserializer._deserialize_workflow(w) for w in data.get("workflows", [])
            ),
            policies=tuple(
                ISRDeserializer._deserialize_policy(p) for p in data.get("policies", [])
            ),
            interfaces=tuple(
                ISRDeserializer._deserialize_interface(i) for i in data.get("interfaces", [])
            ),
            events=tuple(
                ISRDeserializer._deserialize_event(e) for e in data.get("events", [])
            ),
            dependencies=tuple(data.get("dependencies", [])),
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def _deserialize_entity(data: dict[str, Any]) -> Entity:
        return Entity(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            fields=tuple(
                ISRDeserializer._deserialize_field(f) for f in data.get("fields", [])
            ),
            relationships=tuple(
                Relationship(
                    target_entity_id=r.get("target_entity_id", ""),
                    relationship_type=r.get("relationship_type", ""),
                    field_name=r.get("field_name", ""),
                    inverse_field_name=r.get("inverse_field_name", ""),
                    cascade_delete=r.get("cascade_delete", False),
                    description=r.get("description", ""),
                )
                for r in data.get("relationships", [])
            ),
            constraints=tuple(
                ISRDeserializer._deserialize_constraint(c) for c in data.get("constraints", [])
            ),
            is_aggregate_root=data.get("is_aggregate_root", False),
            is_value_object=data.get("is_value_object", False),
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def _deserialize_field(data: dict[str, Any]) -> Field:
        return Field(
            name=data.get("name", ""),
            field_type=FieldType(data.get("field_type", "string")),
            cardinality=FieldCardinality(data.get("cardinality", "required")),
            description=data.get("description", ""),
            default_value=data.get("default_value"),
            constraints=tuple(
                FieldConstraint(
                    name=c.get("name", ""),
                    constraint_type=c.get("constraint_type", ""),
                    parameters=c.get("parameters", {}),
                    message=c.get("message", ""),
                )
                for c in data.get("constraints", [])
            ),
            enum_values=tuple(data.get("enum_values", [])),
            reference_target=data.get("reference_target"),
            is_primary_key=data.get("is_primary_key", False),
            is_indexed=data.get("is_indexed", False),
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def _deserialize_service(data: dict[str, Any]) -> Service:
        return Service(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            operations=tuple(
                Operation(
                    id=op.get("id", ""),
                    name=op.get("name", ""),
                    operation_type=OperationType(op.get("operation_type", "command")),
                    description=op.get("description", ""),
                    is_idempotent=op.get("is_idempotent", False),
                    is_public=op.get("is_public", True),
                    required_permissions=tuple(op.get("required_permissions", [])),
                    metadata=op.get("metadata", {}),
                )
                for op in data.get("operations", [])
            ),
            dependencies=tuple(
                ServiceDependency(
                    target_service_id=d.get("target_service_id", ""),
                    dependency_type=d.get("dependency_type", "runtime"),
                    is_required=d.get("is_required", True),
                    description=d.get("description", ""),
                )
                for d in data.get("dependencies", [])
            ),
            emitted_events=tuple(data.get("emitted_events", [])),
            consumed_events=tuple(data.get("consumed_events", [])),
            is_stateless=data.get("is_stateless", True),
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def _deserialize_workflow(data: dict[str, Any]) -> Workflow:
        return Workflow(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            states=tuple(
                WorkflowState(
                    id=s.get("id", ""),
                    name=s.get("name", ""),
                    state_type=StateType(s.get("state_type", "intermediate")),
                    description=s.get("description", ""),
                    entry_actions=tuple(s.get("entry_actions", [])),
                    exit_actions=tuple(s.get("exit_actions", [])),
                    metadata=s.get("metadata", {}),
                )
                for s in data.get("states", [])
            ),
            transitions=tuple(
                WorkflowTransition(
                    id=t.get("id", ""),
                    name=t.get("name", ""),
                    from_state_id=t.get("from_state_id", ""),
                    to_state_id=t.get("to_state_id", ""),
                    trigger=t.get("trigger", ""),
                    guard_condition=t.get("guard_condition", ""),
                    actions=tuple(t.get("actions", [])),
                    description=t.get("description", ""),
                    metadata=t.get("metadata", {}),
                )
                for t in data.get("transitions", [])
            ),
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def _deserialize_policy(data: dict[str, Any]) -> Policy:
        return Policy(
            id=data.get("id", ""),
            name=data.get("name", ""),
            policy_type=PolicyType(data.get("policy_type", "authentication")),
            description=data.get("description", ""),
            strategy=data.get("strategy", ""),
            roles=tuple(data.get("roles", [])),
            rules=tuple(
                PolicyRule(
                    id=r.get("id", ""),
                    name=r.get("name", ""),
                    description=r.get("description", ""),
                    rule_type=r.get("rule_type", ""),
                    parameters=r.get("parameters", {}),
                    priority=r.get("priority", 0),
                )
                for r in data.get("rules", [])
            ),
            permissions=tuple(
                Permission(
                    id=p.get("id", ""),
                    name=p.get("name", ""),
                    description=p.get("description", ""),
                    resource=p.get("resource", ""),
                    actions=tuple(p.get("actions", [])),
                    conditions=tuple(p.get("conditions", [])),
                )
                for p in data.get("permissions", [])
            ),
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def _deserialize_interface(data: dict[str, Any]) -> Interface:
        return Interface(
            id=data.get("id", ""),
            name=data.get("name", ""),
            interface_type=InterfaceType(data.get("interface_type", "rest")),
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            endpoints=tuple(
                Endpoint(
                    id=ep.get("id", ""),
                    name=ep.get("name", ""),
                    path=ep.get("path", ""),
                    method=HttpMethod(ep.get("method", "GET")),
                    description=ep.get("description", ""),
                    required_permissions=tuple(ep.get("required_permissions", [])),
                    is_public=ep.get("is_public", False),
                    rate_limit=ep.get("rate_limit"),
                    metadata=ep.get("metadata", {}),
                )
                for ep in data.get("endpoints", [])
            ),
            secured_by_policy_id=data.get("secured_by_policy_id"),
            is_internal=data.get("is_internal", False),
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def _deserialize_event(data: dict[str, Any]) -> Event:
        return Event(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            schema=tuple(
                ISRDeserializer._deserialize_field(f) for f in data.get("schema", [])
            ),
            pattern=EventPattern(data.get("pattern", "publish_subscribe")),
            guarantee=EventGuarantee(data.get("guarantee", "at_least_once")),
            ordering_required=data.get("ordering_required", False),
            ttl_seconds=data.get("ttl_seconds"),
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def _deserialize_deployment(data: dict[str, Any]) -> Deployment:
        scaling_data = data.get("scaling", {})
        networking_data = data.get("networking", {})
        monitoring_data = data.get("monitoring", {})
        storage_data = data.get("storage", {})
        secrets_data = data.get("secrets", {})

        return Deployment(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            environment=EnvironmentTier(data.get("environment", "production")),
            scaling=ScalingConfig(
                strategy=ScalingStrategy(scaling_data.get("strategy", "auto")),
                min_instances=scaling_data.get("min_instances", 1),
                max_instances=scaling_data.get("max_instances", 10),
                target_cpu_percent=scaling_data.get("target_cpu_percent", 70.0),
                target_memory_percent=scaling_data.get("target_memory_percent", 80.0),
            ),
            networking=NetworkingConfig(
                expose_publicly=networking_data.get("expose_publicly", False),
                internal_dns=networking_data.get("internal_dns", ""),
                tls_required=networking_data.get("tls_required", True),
                allowed_origins=tuple(networking_data.get("allowed_origins", [])),
                port=networking_data.get("port", 8080),
            ),
            monitoring=MonitoringConfig(
                health_check_path=monitoring_data.get("health_check_path", "/health"),
                readiness_check_path=monitoring_data.get("readiness_check_path", "/ready"),
                metrics_enabled=monitoring_data.get("metrics_enabled", True),
                tracing_enabled=monitoring_data.get("tracing_enabled", True),
                structured_logging=monitoring_data.get("structured_logging", True),
                alert_rules=tuple(monitoring_data.get("alert_rules", [])),
            ),
            storage=StorageConfig(
                persistent_storage_required=storage_data.get("persistent_storage_required", False),
                storage_size_gb=storage_data.get("storage_size_gb"),
                backup_enabled=storage_data.get("backup_enabled", True),
                encryption_at_rest=storage_data.get("encryption_at_rest", True),
            ),
            secrets=SecretsConfig(
                secrets=tuple(secrets_data.get("secrets", [])),
                rotation_policy_days=secrets_data.get("rotation_policy_days", 90),
                encryption_in_transit=secrets_data.get("encryption_in_transit", True),
            ),
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def _deserialize_constraint(data: dict[str, Any]) -> Constraint:
        return Constraint(
            id=data.get("id", ""),
            name=data.get("name", ""),
            scope=ConstraintScope(data.get("scope", "entity")),
            severity=ConstraintSeverity(data.get("severity", "error")),
            description=data.get("description", ""),
            rule_type=data.get("rule_type", ""),
            parameters=data.get("parameters", {}),
            target_node_ids=tuple(data.get("target_node_ids", [])),
            message=data.get("message", ""),
        )
