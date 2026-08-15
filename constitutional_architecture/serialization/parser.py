"""
ISR Parser — Converts JSON back to ISR graphs.

Provides lossless deserialization from JSON to in-memory ISR graph.
The round-trip (serialize → parse) must preserve all architectural
information with zero loss.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import field

from constitutional_architecture.isr.legacy_model import (
    System, Module, Entity, Service, Workflow, Policy,
    Interface, Event, Deployment, Constraint,
    Field, Operation, State, Transition, Action,
    Rule, Permission, Endpoint, Contract, SecurityBinding,
    Relationship, Dependency, Scaling, Networking, Storage,
    Secrets, Monitoring, Metadata,
    NodeType, EdgeType, Cardinality, CompletenessLevel, Severity,
)
from constitutional_architecture.isr.isr_graph import ISRGraph


class ISRParser:
    """Parses JSON back into ISR graphs."""

    def parse_system(self, data: dict) -> System:
        """Parse a System from a JSON-compatible dict."""
        return self._parse_system(data)

    def parse_json(self, json_str: str) -> ISRGraph:
        """Parse an ISRGraph from a JSON string."""
        data = json.loads(json_str)
        system = self.parse_system(data.get("system", data))
        return ISRGraph(system)

    def parse_json_file(self, filepath: str) -> ISRGraph:
        """Parse an ISRGraph from a JSON file."""
        with open(filepath, 'r') as f:
            return self.parse_json(f.read())

    def _parse_system(self, data: dict) -> System:
        """Recursively parse a System from a dict."""
        modules_data = data.get("modules", [])
        modules = [self._parse_module(m) for m in modules_data]

        deployment = None
        if "deployment" in data:
            deployment = self._parse_deployment(data["deployment"])

        constraints = []
        for c in data.get("constraints", []):
            constraints.append(self._parse_constraint(c))

        metadata = Metadata(
            version=data.get("metadata", {}).get("version", 1),
            parent_hash=data.get("metadata", {}).get("parent_hash"),
            lineage=data.get("metadata", {}).get("lineage", []),
            fitness_annotations=data.get("metadata", {}).get("fitness_annotations", {}),
            validation_results=data.get("metadata", {}).get("validation_results", []),
            provenance=data.get("metadata", {}).get("provenance", []),
            owner_agent=data.get("metadata", {}).get("owner_agent"),
        )

        return System(
            name=data.get("name", ""),
            modules=modules,
            deployment=deployment,
            constraints=constraints,
            metadata=metadata,
            description=data.get("description"),
        )

    def _parse_module(self, data: dict) -> Module:
        entities = [self._parse_entity(e) for e in data.get("entities", [])]
        services = [self._parse_service(s) for s in data.get("services", [])]
        workflows = [self._parse_workflow(w) for w in data.get("workflows", [])]
        policies = [self._parse_policy(p) for p in data.get("policies", [])]
        interfaces = [self._parse_interface(i) for i in data.get("interfaces", [])]
        events = [self._parse_event(e) for e in data.get("events", [])]

        deployment = None
        if "deployment" in data:
            deployment = self._parse_deployment(data["deployment"])

        return Module(
            name=data.get("name", ""),
            entities=entities,
            services=services,
            workflows=workflows,
            policies=policies,
            interfaces=interfaces,
            events=events,
            deployment=deployment,
            description=data.get("description"),
        )

    def _parse_entity(self, data: dict) -> Entity:
        fields_list = [self._parse_field(f) for f in data.get("fields", [])]
        relationships = [self._parse_relationship(r) for r in data.get("relationships", [])]
        return Entity(
            name=data.get("name", ""),
            fields=fields_list,
            relationships=relationships,
            constraints=data.get("constraints", []),
            description=data.get("description"),
            is_aggregate_root=data.get("is_aggregate_root", False),
            id_field=data.get("id_field", "id"),
        )

    def _parse_field(self, data: dict) -> Field:
        return Field(
            name=data.get("name", ""),
            field_type=data.get("field_type", "string"),
            required=data.get("required", True),
            unique=data.get("unique", False),
            indexed=data.get("indexed", False),
            default=data.get("default"),
            description=data.get("description"),
            constraints=data.get("constraints", []),
        )

    def _parse_relationship(self, data: dict) -> Relationship:
        card = data.get("cardinality", "1:N")
        cardinality = next((c for c in Cardinality if c.value == card), Cardinality.ONE_TO_MANY)
        return Relationship(
            target_entity=data.get("target_entity", ""),
            target_module=data.get("target_module"),
            type=data.get("type", "reference"),
            cardinality=cardinality,
            foreign_key_field=data.get("foreign_key_field"),
            inverse_field=data.get("inverse_field"),
            description=data.get("description"),
        )

    def _parse_service(self, data: dict) -> Service:
        operations = [self._parse_operation(o) for o in data.get("operations", [])]
        dependencies = [self._parse_dependency(d) for d in data.get("dependencies", [])]
        return Service(
            name=data.get("name", ""),
            operations=operations,
            dependencies=dependencies,
            events=data.get("events", []),
            consumes=data.get("consumes", []),
            description=data.get("description"),
        )

    def _parse_operation(self, data: dict) -> Operation:
        return Operation(
            name=data.get("name", ""),
            parameters=data.get("parameters", []),
            return_type=data.get("return_type"),
            description=data.get("description"),
            is_query=data.get("is_query", False),
            event_triggers=data.get("event_triggers", []),
        )

    def _parse_dependency(self, data: dict) -> Dependency:
        return Dependency(
            target_service=data.get("target_service", ""),
            target_module=data.get("target_module"),
            coupling_strength=data.get("coupling_strength", "loose"),
            sync_or_async=data.get("sync_or_async", "sync"),
            criticality=data.get("criticality", "normal"),
            latency_budget_ms=data.get("latency_budget_ms"),
            circuit_breaker=data.get("circuit_breaker", False),
            retry_policy=data.get("retry_policy"),
        )

    def _parse_workflow(self, data: dict) -> Workflow:
        states = [self._parse_state(s) for s in data.get("states", [])]
        transitions = [self._parse_transition(t) for t in data.get("transitions", [])]
        actions = [self._parse_action(a) for a in data.get("actions", [])]
        return Workflow(
            name=data.get("name", ""),
            states=states,
            transitions=transitions,
            actions=actions,
            description=data.get("description"),
        )

    def _parse_state(self, data: dict) -> State:
        return State(
            name=data.get("name", ""),
            description=data.get("description"),
            is_initial=data.get("is_initial", False),
            is_terminal=data.get("is_terminal", False),
            is_error=data.get("is_error", False),
        )

    def _parse_transition(self, data: dict) -> Transition:
        return Transition(
            from_state=data.get("from_state", ""),
            to_state=data.get("to_state", ""),
            action=data.get("action", ""),
            guard_condition=data.get("guard_condition"),
            description=data.get("description"),
        )

    def _parse_action(self, data: dict) -> Action:
        return Action(
            name=data.get("name", ""),
            service=data.get("service"),
            operation=data.get("operation"),
            description=data.get("description"),
        )

    def _parse_policy(self, data: dict) -> Policy:
        rules = [self._parse_rule(r) for r in data.get("rules", [])]
        permissions = [self._parse_permission(p) for p in data.get("permissions", [])]
        return Policy(
            name=data.get("name", ""),
            strategy=data.get("strategy"),
            rules=rules,
            permissions=permissions,
            roles=data.get("roles", []),
            constraints=data.get("constraints", []),
            description=data.get("description"),
        )

    def _parse_rule(self, data: dict) -> Rule:
        return Rule(
            name=data.get("name", ""),
            description=data.get("description", ""),
            effect=data.get("effect", "allow"),
            resource_pattern=data.get("resource_pattern"),
            condition=data.get("condition"),
        )

    def _parse_permission(self, data: dict) -> Permission:
        return Permission(
            resource=data.get("resource", ""),
            action=data.get("action", "read"),
            roles=data.get("roles", []),
            conditions=data.get("conditions", []),
        )

    def _parse_interface(self, data: dict) -> Interface:
        endpoints = [self._parse_endpoint(e) for e in data.get("endpoints", [])]
        contracts = [self._parse_contract(c) for c in data.get("contracts", [])]
        security_bindings = [self._parse_security_binding(sb) for sb in data.get("security_bindings", [])]
        return Interface(
            name=data.get("name", ""),
            interface_type=data.get("interface_type", "REST"),
            endpoints=endpoints,
            contracts=contracts,
            security_bindings=security_bindings,
            internal=data.get("internal", False),
            version=data.get("version", "1.0.0"),
            description=data.get("description"),
        )

    def _parse_endpoint(self, data: dict) -> Endpoint:
        return Endpoint(
            path=data.get("path", ""),
            method=data.get("method", "GET"),
            operation=data.get("operation"),
            request_schema=data.get("request_schema"),
            response_schema=data.get("response_schema"),
            description=data.get("description"),
            rate_limit=data.get("rate_limit"),
            timeout_ms=data.get("timeout_ms"),
        )

    def _parse_contract(self, data: dict) -> Contract:
        return Contract(
            name=data.get("name", ""),
            schema_type=data.get("schema_type", "object"),
            properties=data.get("properties", {}),
            required_fields=data.get("required_fields", []),
            description=data.get("description"),
        )

    def _parse_security_binding(self, data: dict) -> SecurityBinding:
        return SecurityBinding(
            policy_name=data.get("policy_name", ""),
            auth_strategy=data.get("auth_strategy"),
            scopes=data.get("scopes", []),
        )

    def _parse_event(self, data: dict) -> Event:
        return Event(
            name=data.get("name", ""),
            schema_type=data.get("schema_type", "object"),
            properties=data.get("properties", {}),
            routing_key=data.get("routing_key"),
            delivery_mode=data.get("delivery_mode", "at_least_once"),
            retention_days=data.get("retention_days", 7),
            description=data.get("description"),
        )

    def _parse_deployment(self, data: dict) -> Deployment:
        scaling = self._parse_scaling(data.get("scaling", {}))
        networking = self._parse_networking(data.get("networking", {}))
        storage = self._parse_storage(data.get("storage", {}))
        secrets = self._parse_secrets(data.get("secrets", {}))
        monitoring = self._parse_monitoring(data.get("monitoring", {}))
        return Deployment(
            name=data.get("name", "default"),
            scaling=scaling,
            networking=networking,
            storage=storage,
            secrets=secrets,
            monitoring=monitoring,
            description=data.get("description"),
        )

    def _parse_scaling(self, data: dict) -> Scaling:
        return Scaling(
            min_instances=data.get("min_instances", 1),
            max_instances=data.get("max_instances", 3),
            target_cpu_utilization=data.get("target_cpu_utilization", 0.7),
            target_memory_utilization=data.get("target_memory_utilization", 0.8),
            scaling_policy=data.get("scaling_policy", "horizontal"),
            cooldown_seconds=data.get("cooldown_seconds", 60),
        )

    def _parse_networking(self, data: dict) -> Networking:
        return Networking(
            dns_name=data.get("dns_name"),
            ports=data.get("ports", []),
            ingress_type=data.get("ingress_type", "load_balancer"),
            tls_enabled=data.get("tls_enabled", True),
            network_policy=data.get("network_policy"),
            allowed_cidrs=data.get("allowed_cidrs", []),
        )

    def _parse_storage(self, data: dict) -> Storage:
        return Storage(
            type=data.get("type", "persistent"),
            size_gb=data.get("size_gb", 10),
            performance_tier=data.get("performance_tier", "standard"),
            backup_enabled=data.get("backup_enabled", True),
            encryption_at_rest=data.get("encryption_at_rest", True),
        )

    def _parse_secrets(self, data: dict) -> Secrets:
        return Secrets(
            provider=data.get("provider", "environment"),
            secret_names=data.get("secret_names", []),
            rotation_days=data.get("rotation_days", 90),
        )

    def _parse_monitoring(self, data: dict) -> Monitoring:
        return Monitoring(
            metrics_enabled=data.get("metrics_enabled", True),
            logging_enabled=data.get("logging_enabled", True),
            tracing_enabled=data.get("tracing_enabled", True),
            health_check_path=data.get("health_check_path", "/health"),
            readiness_check_path=data.get("readiness_check_path", "/ready"),
            metrics_port=data.get("metrics_port", 9090),
            alert_endpoints=data.get("alert_endpoints", []),
        )

    def _parse_constraint(self, data: dict) -> Constraint:
        sev = data.get("severity", "error")
        severity = next((s for s in Severity if s.value == sev), Severity.ERROR)
        return Constraint(
            name=data.get("name", ""),
            description=data.get("description", ""),
            constraint_type=data.get("constraint_type", "architectural"),
            severity=severity,
            affected_nodes=data.get("affected_nodes", []),
            rule_expression=data.get("rule_expression"),
        )