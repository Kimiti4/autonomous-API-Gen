"""
EIR — Evolution Intermediate Representation and Mutation Operators

The EIR describes transitions between ISR versions. Each transformation
is a typed, classified mutation operator that transforms an ISR into a
new ISR version.

Transformation classes:
- Structural: Changes graph topology (split, merge, extract)
- Strategic: Changes node attributes / chromosome family (auth strategy, CQRS)
- Additive: Adds nodes/edges (cache, rate limiting, audit logging)
- Parametric: Changes attribute values (scaling policy, TTL)
- Topological: Changes edge types (sync→async, introduce message bus)
"""

from __future__ import annotations

import uuid
import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Callable, Tuple
from datetime import datetime

from constitutional_architecture.isr.model import (
    System, Module, Entity, Service, Workflow, Policy,
    Interface, Event, Deployment, Constraint,
    Field, Operation, State, Transition, Action,
    Rule, Permission, Endpoint, Contract, SecurityBinding,
    Relationship, Dependency, Scaling, Networking, Storage,
    Secrets, Monitoring, Metadata,
    NodeType, EdgeType, Cardinality, CompletenessLevel, Severity,
)
from constitutional_architecture.isr.isr_graph import ISRGraph


class TransformationClass(Enum):
    """Classification of transformation types."""
    STRUCTURAL = "structural"
    STRATEGIC = "strategic"
    ADDITIVE = "additive"
    PARAMETRIC = "parametric"
    TOPOLOGICAL = "topological"


@dataclass(frozen=True)
class Transformation:
    """A single architectural transformation."""
    type: str
    target: str  # Node ID or pattern
    parameters: Dict[str, Any] = field(default_factory=dict)
    fitness_impact: List[str] = field(default_factory=list)
    reversible: bool = True
    description: str = ""


@dataclass(frozen=True)
class EIR:
    """Evolution Intermediate Representation.

    An EIR is a typed, ordered sequence of architectural transformations
    that, when applied to a source ISR, produces a target ISR.
    """
    id: str = field(default_factory=lambda: f"EIR-{uuid.uuid4().hex[:8]}")
    source_isr_hash: str = ""
    target_isr_hash: str = ""
    transformations: List[Transformation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def transformation_count(self) -> int:
        return len(self.transformations)

    @property
    def is_empty(self) -> bool:
        return len(self.transformations) == 0


class MutationOperator:
    """A typed mutation operator that transforms an ISR.

    Each operator has:
    - A name and classification
    - Preconditions that must be satisfied
    - An apply function that produces a new ISR + EIR
    - Postconditions that must hold after application
    - A fitness impact description
    - Reversibility information
    """

    def __init__(
        self,
        name: str,
        transformation_class: TransformationClass,
        precondition: Callable[[ISRGraph, str, dict], bool],
        apply_fn: Callable[[ISRGraph, str, dict], Tuple[System, Transformation]],
        postcondition: Optional[Callable[[ISRGraph], bool]] = None,
        fitness_impact: Optional[List[str]] = None,
        reversible: bool = True,
        inverse_name: Optional[str] = None,
        description: str = "",
    ):
        self.name = name
        self.transformation_class = transformation_class
        self.precondition = precondition
        self.apply_fn = apply_fn
        self.postcondition = postcondition
        self.fitness_impact = fitness_impact or []
        self.reversible = reversible
        self.inverse_name = inverse_name
        self.description = description

    def can_apply(self, graph: ISRGraph, target: str, params: dict) -> bool:
        """Check if this operator can be applied."""
        return self.precondition(graph, target, params)

    def apply(self, graph: ISRGraph, target: str, params: dict) -> Tuple[System, Transformation]:
        """Apply this operator and return (new_system, transformation_record)."""
        return self.apply_fn(graph, target, params)

    def verify(self, graph: ISRGraph) -> bool:
        """Verify postcondition holds."""
        if self.postcondition:
            return self.postcondition(graph)
        return True


# ─── Operator Registry ───

_operator_registry: Dict[str, MutationOperator] = {}


def register_operator(op: MutationOperator):
    """Register a mutation operator."""
    _operator_registry[op.name] = op


def get_operator(name: str) -> Optional[MutationOperator]:
    """Get a registered operator by name."""
    return _operator_registry.get(name)


def get_operator_registry() -> Dict[str, MutationOperator]:
    """Get all registered operators."""
    return dict(_operator_registry)


# ─── Precondition Helpers ───

def _has_module(graph: ISRGraph, module_name: str) -> bool:
    return any(m.name == module_name for m in graph.system.modules)


def _has_service(graph: ISRGraph, module_name: str, service_name: str) -> bool:
    for m in graph.system.modules:
        if m.name == module_name:
            return any(s.name == service_name for s in m.services)
    return False


def _has_entity(graph: ISRGraph, module_name: str, entity_name: str) -> bool:
    for m in graph.system.modules:
        if m.name == module_name:
            return any(e.name == entity_name for e in m.entities)
    return False


# ─── Operator: Split Module ───

def _pre_split_module(graph: ISRGraph, target: str, params: dict) -> bool:
    """Precondition: target module exists and has entities to extract."""
    return _has_module(graph, target)


def _apply_split_module(graph: ISRGraph, target: str, params: dict) -> Tuple[System, Transformation]:
    """Split a module by extracting entities into a new module."""
    extract_entities = params.get("extract", [])
    new_module_name = params.get("new_module", f"{target}Extracted")
    interface_name = params.get("interface", f"{new_module_name}API")

    # Deep copy the system
    new_modules = []
    extracted_entities = []
    source_module = None

    for m in graph.system.modules:
        if m.name == target:
            source_module = m
            remaining_entities = []
            for e in m.entities:
                if e.name in extract_entities:
                    extracted_entities.append(e)
                else:
                    remaining_entities.append(e)
            new_modules.append(Module(
                name=m.name,
                entities=remaining_entities,
                services=m.services,
                workflows=m.workflows,
                policies=m.policies,
                interfaces=m.interfaces,
                events=m.events,
                deployment=m.deployment,
                description=m.description,
            ))
        else:
            new_modules.append(m)

    # Create new module with extracted entities
    new_module = Module(
        name=new_module_name,
        entities=extracted_entities,
        interfaces=[
            Interface(
                name=interface_name,
                interface_type="REST",
                endpoints=[],
            )
        ],
        description=f"Extracted from {target}",
    )
    new_modules.append(new_module)

    new_system = System(
        name=graph.system.name,
        modules=new_modules,
        deployment=graph.system.deployment,
        constraints=graph.system.constraints,
        metadata=Metadata(
            version=graph.system.metadata.version + 1,
            parent_hash=graph.compute_hash(),
            provenance=graph.system.metadata.provenance + [f"split_module({target})"],
        ),
        description=graph.system.description,
    )

    transformation = Transformation(
        type="split_module",
        target=target,
        parameters=params,
        fitness_impact=["maintainability+", "coupling-"],
        reversible=True,
        description=f"Split module '{target}': extracted {extract_entities} into '{new_module_name}'",
    )

    return new_system, transformation


# ─── Operator: Introduce Cache ───

def _pre_introduce_cache(graph: ISRGraph, target: str, params: dict) -> bool:
    """Precondition: target service exists."""
    parts = target.split(".", 1)
    if len(parts) != 2:
        return False
    module_name, service_name = parts[0], parts[1]
    return _has_service(graph, module_name, service_name)


def _apply_introduce_cache(graph: ISRGraph, target: str, params: dict) -> Tuple[System, Transformation]:
    """Add caching configuration to a service operation."""
    parts = target.split(".", 1)
    module_name, service_name = parts[0], parts[1]
    strategy = params.get("strategy", "read-through")
    invalidation = params.get("invalidation", "ttl")
    ttl_seconds = params.get("ttl_seconds", 300)

    new_modules = []
    for m in graph.system.modules:
        if m.name == module_name:
            new_services = []
            for s in m.services:
                if s.name == service_name:
                    new_operations = []
                    for op in s.operations:
                        new_params = dict(op.parameters) if op.parameters else {}
                        new_params["_cache_strategy"] = strategy
                        new_params["_cache_ttl"] = ttl_seconds
                        new_operations.append(Operation(
                            name=op.name,
                            parameters=op.parameters,
                            return_type=op.return_type,
                            description=op.description,
                            is_query=op.is_query,
                            event_triggers=op.event_triggers,
                        ))
                    new_services.append(Service(
                        name=s.name,
                        operations=new_operations,
                        dependencies=s.dependencies,
                        events=s.events,
                        consumes=s.consumes,
                        description=s.description,
                    ))
                else:
                    new_services.append(s)
            new_modules.append(Module(
                name=m.name,
                entities=m.entities,
                services=new_services,
                workflows=m.workflows,
                policies=m.policies,
                interfaces=m.interfaces,
                events=m.events,
                deployment=m.deployment,
                description=m.description,
            ))
        else:
            new_modules.append(m)

    new_system = System(
        name=graph.system.name,
        modules=new_modules,
        deployment=graph.system.deployment,
        constraints=graph.system.constraints,
        metadata=Metadata(
            version=graph.system.metadata.version + 1,
            parent_hash=graph.compute_hash(),
            provenance=graph.system.metadata.provenance + [f"introduce_cache({target})"],
        ),
    )

    transformation = Transformation(
        type="introduce_cache",
        target=target,
        parameters=params,
        fitness_impact=["performance+", "complexity+"],
        reversible=True,
        description=f"Introduced {strategy} cache on '{target}' (TTL: {ttl_seconds}s)",
    )

    return new_system, transformation


# ─── Operator: Add Rate Limiting ───

def _pre_add_rate_limiting(graph: ISRGraph, target: str, params: dict) -> bool:
    """Precondition: target interface exists."""
    parts = target.split(".", 1)
    if len(parts) != 2:
        return False
    module_name, iface_name = parts[0], parts[1]
    for m in graph.system.modules:
        if m.name == module_name:
            return any(i.name == iface_name for i in m.interfaces)
    return False


def _apply_add_rate_limiting(graph: ISRGraph, target: str, params: dict) -> Tuple[System, Transformation]:
    """Add rate limiting to an interface."""
    parts = target.split(".", 1)
    module_name, iface_name = parts[0], parts[1]
    rate_limit = params.get("rate_limit", "100/minute")

    new_modules = []
    for m in graph.system.modules:
        if m.name == module_name:
            new_interfaces = []
            for i in m.interfaces:
                if i.name == iface_name:
                    new_endpoints = []
                    for ep in i.endpoints:
                        new_endpoints.append(Endpoint(
                            path=ep.path,
                            method=ep.method,
                            operation=ep.operation,
                            request_schema=ep.request_schema,
                            response_schema=ep.response_schema,
                            description=ep.description,
                            rate_limit=rate_limit,
                            timeout_ms=ep.timeout_ms,
                        ))
                    new_interfaces.append(Interface(
                        name=i.name,
                        interface_type=i.interface_type,
                        endpoints=new_endpoints,
                        contracts=i.contracts,
                        security_bindings=i.security_bindings,
                        internal=i.internal,
                        version=i.version,
                        description=i.description,
                    ))
                else:
                    new_interfaces.append(i)
            new_modules.append(Module(
                name=m.name,
                entities=m.entities,
                services=m.services,
                workflows=m.workflows,
                policies=m.policies,
                interfaces=new_interfaces,
                events=m.events,
                deployment=m.deployment,
                description=m.description,
            ))
        else:
            new_modules.append(m)

    new_system = System(
        name=graph.system.name,
        modules=new_modules,
        deployment=graph.system.deployment,
        constraints=graph.system.constraints,
        metadata=Metadata(
            version=graph.system.metadata.version + 1,
            parent_hash=graph.compute_hash(),
            provenance=graph.system.metadata.provenance + [f"add_rate_limiting({target})"],
        ),
    )

    transformation = Transformation(
        type="add_rate_limiting",
        target=target,
        parameters=params,
        fitness_impact=["reliability+", "security+"],
        reversible=True,
        description=f"Added rate limiting ({rate_limit}) to '{target}'",
    )

    return new_system, transformation


# ─── Operator: Convert to Async ───

def _pre_convert_to_async(graph: ISRGraph, target: str, params: dict) -> bool:
    """Precondition: target service exists and has sync dependencies."""
    parts = target.split(".", 1)
    if len(parts) != 2:
        return False
    module_name, service_name = parts[0], parts[1]
    for m in graph.system.modules:
        if m.name == module_name:
            for s in m.services:
                if s.name == service_name:
                    return any(d.sync_or_async == "sync" for d in s.dependencies)
    return False


def _apply_convert_to_async(graph: ISRGraph, target: str, params: dict) -> Tuple[System, Transformation]:
    """Convert a sync dependency to async event-driven communication."""
    parts = target.split(".", 1)
    module_name, service_name = parts[0], parts[1]
    target_dep = params.get("dependency", "")
    event_name = params.get("event_name", f"{service_name}Requested")

    new_modules = []
    for m in graph.system.modules:
        if m.name == module_name:
            new_services = []
            for s in m.services:
                if s.name == service_name:
                    new_deps = []
                    for d in s.dependencies:
                        if d.target_service == target_dep:
                            new_deps.append(Dependency(
                                target_service=d.target_service,
                                target_module=d.target_module,
                                coupling_strength=d.coupling_strength,
                                sync_or_async="async",
                                criticality=d.criticality,
                                latency_budget_ms=d.latency_budget_ms,
                                circuit_breaker=d.circuit_breaker,
                                retry_policy=d.retry_policy,
                            ))
                        else:
                            new_deps.append(d)
                    new_services.append(Service(
                        name=s.name,
                        operations=s.operations,
                        dependencies=new_deps,
                        events=s.events + [event_name],
                        consumes=s.consumes,
                        description=s.description,
                    ))
                else:
                    new_services.append(s)

            # Add the event
            new_events = list(m.events) + [
                Event(name=event_name, description=f"Async request from {service_name} to {target_dep}")
            ]

            new_modules.append(Module(
                name=m.name,
                entities=m.entities,
                services=new_services,
                workflows=m.workflows,
                policies=m.policies,
                interfaces=m.interfaces,
                events=new_events,
                deployment=m.deployment,
                description=m.description,
            ))
        else:
            new_modules.append(m)

    new_system = System(
        name=graph.system.name,
        modules=new_modules,
        deployment=graph.system.deployment,
        constraints=graph.system.constraints,
        metadata=Metadata(
            version=graph.system.metadata.version + 1,
            parent_hash=graph.compute_hash(),
            provenance=graph.system.metadata.provenance + [f"convert_to_async({target})"],
        ),
    )

    transformation = Transformation(
        type="convert_to_async",
        target=target,
        parameters=params,
        fitness_impact=["scalability+", "complexity+", "coupling-"],
        reversible=True,
        description=f"Converted '{service_name}' → '{target_dep}' to async via '{event_name}'",
    )

    return new_system, transformation


# ─── Operator: Extract Interface ───

def _pre_extract_interface(graph: ISRGraph, target: str, params: dict) -> bool:
    """Precondition: target service exists."""
    parts = target.split(".", 1)
    if len(parts) != 2:
        return False
    return _has_service(graph, parts[0], parts[1])


def _apply_extract_interface(graph: ISRGraph, target: str, params: dict) -> Tuple[System, Transformation]:
    """Extract a service's operations into a formal interface."""
    parts = target.split(".", 1)
    module_name, service_name = parts[0], parts[1]
    iface_name = params.get("interface_name", f"{service_name}API")
    iface_type = params.get("interface_type", "REST")

    new_modules = []
    for m in graph.system.modules:
        if m.name == module_name:
            service = None
            for s in m.services:
                if s.name == service_name:
                    service = s
                    break

            if service:
                new_interface = Interface(
                    name=iface_name,
                    interface_type=iface_type,
                    endpoints=[
                        Endpoint(
                            path=f"/{service_name.lower()}/{op.name}",
                            method="POST" if not op.is_query else "GET",
                            operation=op.name,
                        )
                        for op in service.operations
                    ],
                    security_bindings=[],
                )
                new_modules.append(Module(
                    name=m.name,
                    entities=m.entities,
                    services=m.services,
                    workflows=m.workflows,
                    policies=m.policies,
                    interfaces=list(m.interfaces) + [new_interface],
                    events=m.events,
                    deployment=m.deployment,
                    description=m.description,
                ))
            else:
                new_modules.append(m)
        else:
            new_modules.append(m)

    new_system = System(
        name=graph.system.name,
        modules=new_modules,
        deployment=graph.system.deployment,
        constraints=graph.system.constraints,
        metadata=Metadata(
            version=graph.system.metadata.version + 1,
            parent_hash=graph.compute_hash(),
            provenance=graph.system.metadata.provenance + [f"extract_interface({target})"],
        ),
    )

    transformation = Transformation(
        type="extract_interface",
        target=target,
        parameters=params,
        fitness_impact=["maintainability+", "modularity+"],
        reversible=True,
        description=f"Extracted interface '{iface_name}' from '{service_name}'",
    )

    return new_system, transformation


# ─── Operator: Add Audit Logging ───

def _pre_add_audit_logging(graph: ISRGraph, target: str, params: dict) -> bool:
    """Precondition: target module exists."""
    return _has_module(graph, target)


def _apply_add_audit_logging(graph: ISRGraph, target: str, params: dict) -> Tuple[System, Transformation]:
    """Add audit logging policy to a module."""
    retention_days = params.get("retention_days", 365)

    new_modules = []
    for m in graph.system.modules:
        if m.name == target:
            audit_policy = Policy(
                name=f"{target}AuditPolicy",
                strategy="audit_log",
                rules=[
                    Rule(name="audit-all-writes", description="Log all write operations", effect="audit"),
                    Rule(name=f"retention-{retention_days}d", description=f"Retain logs for {retention_days} days", effect="audit"),
                ],
                description=f"Audit logging policy for {target}",
            )
            new_modules.append(Module(
                name=m.name,
                entities=m.entities,
                services=m.services,
                workflows=m.workflows,
                policies=list(m.policies) + [audit_policy],
                interfaces=m.interfaces,
                events=m.events,
                deployment=m.deployment,
                description=m.description,
            ))
        else:
            new_modules.append(m)

    new_system = System(
        name=graph.system.name,
        modules=new_modules,
        deployment=graph.system.deployment,
        constraints=graph.system.constraints,
        metadata=Metadata(
            version=graph.system.metadata.version + 1,
            parent_hash=graph.compute_hash(),
            provenance=graph.system.metadata.provenance + [f"add_audit_logging({target})"],
        ),
    )

    transformation = Transformation(
        type="add_audit_logging",
        target=target,
        parameters=params,
        fitness_impact=["security+", "compliance+", "complexity+"],
        reversible=True,
        description=f"Added audit logging to '{target}' (retention: {retention_days}d)",
    )

    return new_system, transformation


# ─── Operator: Change Scaling Policy ───

def _pre_change_scaling_policy(graph: ISRGraph, target: str, params: dict) -> bool:
    """Precondition: system has deployment configuration."""
    return graph.system.deployment is not None


def _apply_change_scaling_policy(graph: ISRGraph, target: str, params: dict) -> Tuple[System, Transformation]:
    """Change the scaling policy parameters."""
    min_inst = params.get("min_instances", 2)
    max_inst = params.get("max_instances", 10)
    cpu_target = params.get("target_cpu_utilization", 0.7)

    new_deployment = Deployment(
        name=graph.system.deployment.name if graph.system.deployment else "default",
        scaling=Scaling(
            min_instances=min_inst,
            max_instances=max_inst,
            target_cpu_utilization=cpu_target,
            target_memory_utilization=params.get("target_memory_utilization", 0.8),
            scaling_policy=params.get("scaling_policy", "horizontal"),
            cooldown_seconds=params.get("cooldown_seconds", 60),
        ),
        networking=graph.system.deployment.networking if graph.system.deployment else Networking(),
        storage=graph.system.deployment.storage if graph.system.deployment else Storage(),
        secrets=graph.system.deployment.secrets if graph.system.deployment else Secrets(),
        monitoring=graph.system.deployment.monitoring if graph.system.deployment else Monitoring(),
    )

    new_system = System(
        name=graph.system.name,
        modules=graph.system.modules,
        deployment=new_deployment,
        constraints=graph.system.constraints,
        metadata=Metadata(
            version=graph.system.metadata.version + 1,
            parent_hash=graph.compute_hash(),
            provenance=graph.system.metadata.provenance + [f"change_scaling_policy"],
        ),
    )

    transformation = Transformation(
        type="change_scaling_policy",
        target=target,
        parameters=params,
        fitness_impact=["scalability+", "cost+"],
        reversible=True,
        description=f"Changed scaling policy: {min_inst}-{max_inst} instances, {cpu_target*100:.0f}% CPU target",
    )

    return new_system, transformation


# ─── Operator: Add Event ───

def _pre_add_event(graph: ISRGraph, target: str, params: dict) -> bool:
    """Precondition: target service exists."""
    parts = target.split(".", 1)
    if len(parts) != 2:
        return False
    return _has_service(graph, parts[0], parts[1])


def _apply_add_event(graph: ISRGraph, target: str, params: dict) -> Tuple[System, Transformation]:
    """Add a new event to a service."""
    parts = target.split(".", 1)
    module_name, service_name = parts[0], parts[1]
    event_name = params.get("event_name", f"{service_name}Event")
    event_description = params.get("description", f"Event emitted by {service_name}")

    new_modules = []
    for m in graph.system.modules:
        if m.name == module_name:
            new_services = []
            for s in m.services:
                if s.name == service_name:
                    new_services.append(Service(
                        name=s.name,
                        operations=s.operations,
                        dependencies=s.dependencies,
                        events=list(s.events) + [event_name],
                        consumes=s.consumes,
                        description=s.description,
                    ))
                else:
                    new_services.append(s)

            new_event = Event(name=event_name, description=event_description)
            new_modules.append(Module(
                name=m.name,
                entities=m.entities,
                services=new_services,
                workflows=m.workflows,
                policies=m.policies,
                interfaces=m.interfaces,
                events=list(m.events) + [new_event],
                deployment=m.deployment,
                description=m.description,
            ))
        else:
            new_modules.append(m)

    new_system = System(
        name=graph.system.name,
        modules=new_modules,
        deployment=graph.system.deployment,
        constraints=graph.system.constraints,
        metadata=Metadata(
            version=graph.system.metadata.version + 1,
            parent_hash=graph.compute_hash(),
            provenance=graph.system.metadata.provenance + [f"add_event({target})"],
        ),
    )

    transformation = Transformation(
        type="add_event",
        target=target,
        parameters=params,
        fitness_impact=["extensibility+", "complexity+"],
        reversible=True,
        description=f"Added event '{event_name}' to '{service_name}'",
    )

    return new_system, transformation


# ─── Operator: Merge Services ───

def _pre_merge_services(graph: ISRGraph, target: str, params: dict) -> bool:
    """Precondition: both services exist in the same module."""
    parts = target.split(".", 1)
    if len(parts) != 2:
        return False
    module_name, service_name = parts[0], parts[1]
    merge_with = params.get("merge_with", "")
    if not merge_with:
        return False
    return (_has_service(graph, module_name, service_name) and
            _has_service(graph, module_name, merge_with))


def _apply_merge_services(graph: ISRGraph, target: str, params: dict) -> Tuple[System, Transformation]:
    """Merge two services into one."""
    parts = target.split(".", 1)
    module_name, service_name = parts[0], parts[1]
    merge_with = params.get("merge_with", "")
    new_name = params.get("new_name", f"{service_name}{merge_with}")

    new_modules = []
    for m in graph.system.modules:
        if m.name == module_name:
            svc1 = None
            svc2 = None
            other_services = []
            for s in m.services:
                if s.name == service_name:
                    svc1 = s
                elif s.name == merge_with:
                    svc2 = s
                else:
                    other_services.append(s)

            if svc1 and svc2:
                merged = Service(
                    name=new_name,
                    operations=list(svc1.operations) + list(svc2.operations),
                    dependencies=list(svc1.dependencies) + list(svc2.dependencies),
                    events=list(set(svc1.events + svc2.events)),
                    consumes=list(set(svc1.consumes + svc2.consumes)),
                    description=f"Merged {svc1.name} + {svc2.name}",
                )
                new_modules.append(Module(
                    name=m.name,
                    entities=m.entities,
                    services=other_services + [merged],
                    workflows=m.workflows,
                    policies=m.policies,
                    interfaces=m.interfaces,
                    events=m.events,
                    deployment=m.deployment,
                    description=m.description,
                ))
            else:
                new_modules.append(m)
        else:
            new_modules.append(m)

    new_system = System(
        name=graph.system.name,
        modules=new_modules,
        deployment=graph.system.deployment,
        constraints=graph.system.constraints,
        metadata=Metadata(
            version=graph.system.metadata.version + 1,
            parent_hash=graph.compute_hash(),
            provenance=graph.system.metadata.provenance + [f"merge_services({target})"],
        ),
    )

    transformation = Transformation(
        type="merge_services",
        target=target,
        parameters=params,
        fitness_impact=["simplicity+", "coupling+"],
        reversible=True,
        description=f"Merged '{service_name}' + '{merge_with}' into '{new_name}'",
    )

    return new_system, transformation


# ─── Operator: Add Circuit Breaker ───

def _pre_add_circuit_breaker(graph: ISRGraph, target: str, params: dict) -> bool:
    """Precondition: target service exists."""
    parts = target.split(".", 1)
    if len(parts) != 2:
        return False
    return _has_service(graph, parts[0], parts[1])


def _apply_add_circuit_breaker(graph: ISRGraph, target: str, params: dict) -> Tuple[System, Transformation]:
    """Add circuit breaker to a service dependency."""
    parts = target.split(".", 1)
    module_name, service_name = parts[0], parts[1]
    dep_name = params.get("dependency", "")

    new_modules = []
    for m in graph.system.modules:
        if m.name == module_name:
            new_services = []
            for s in m.services:
                if s.name == service_name:
                    new_deps = []
                    for d in s.dependencies:
                        if d.target_service == dep_name:
                            new_deps.append(Dependency(
                                target_service=d.target_service,
                                target_module=d.target_module,
                                coupling_strength=d.coupling_strength,
                                sync_or_async=d.sync_or_async,
                                criticality=d.criticality,
                                latency_budget_ms=d.latency_budget_ms,
                                circuit_breaker=True,
                                retry_policy=d.retry_policy or "exponential_backoff",
                            ))
                        else:
                            new_deps.append(d)
                    new_services.append(Service(
                        name=s.name,
                        operations=s.operations,
                        dependencies=new_deps,
                        events=s.events,
                        consumes=s.consumes,
                        description=s.description,
                    ))
                else:
                    new_services.append(s)
            new_modules.append(Module(
                name=m.name,
                entities=m.entities,
                services=new_services,
                workflows=m.workflows,
                policies=m.policies,
                interfaces=m.interfaces,
                events=m.events,
                deployment=m.deployment,
                description=m.description,
            ))
        else:
            new_modules.append(m)

    new_system = System(
        name=graph.system.name,
        modules=new_modules,
        deployment=graph.system.deployment,
        constraints=graph.system.constraints,
        metadata=Metadata(
            version=graph.system.metadata.version + 1,
            parent_hash=graph.compute_hash(),
            provenance=graph.system.metadata.provenance + [f"add_circuit_breaker({target})"],
        ),
    )

    transformation = Transformation(
        type="add_circuit_breaker",
        target=target,
        parameters=params,
        fitness_impact=["reliability+", "resilience+"],
        reversible=True,
        description=f"Added circuit breaker to '{service_name}' → '{dep_name}'",
    )

    return new_system, transformation


# ─── Factory Functions ───

def create_split_module_operator() -> MutationOperator:
    return MutationOperator(
        name="split_module",
        transformation_class=TransformationClass.STRUCTURAL,
        precondition=_pre_split_module,
        apply_fn=_apply_split_module,
        fitness_impact=["maintainability+", "coupling-"],
        reversible=True,
        inverse_name="merge_modules",
        description="Split a module by extracting entities into a new module",
    )


def create_introduce_cache_operator() -> MutationOperator:
    return MutationOperator(
        name="introduce_cache",
        transformation_class=TransformationClass.ADDITIVE,
        precondition=_pre_introduce_cache,
        apply_fn=_apply_introduce_cache,
        fitness_impact=["performance+", "complexity+"],
        reversible=True,
        description="Add caching configuration to a service operation",
    )


def create_add_rate_limiting_operator() -> MutationOperator:
    return MutationOperator(
        name="add_rate_limiting",
        transformation_class=TransformationClass.ADDITIVE,
        precondition=_pre_add_rate_limiting,
        apply_fn=_apply_add_rate_limiting,
        fitness_impact=["reliability+", "security+"],
        reversible=True,
        description="Add rate limiting to an interface",
    )


def create_convert_to_async_operator() -> MutationOperator:
    return MutationOperator(
        name="convert_to_async",
        transformation_class=TransformationClass.TOPOLOGICAL,
        precondition=_pre_convert_to_async,
        apply_fn=_apply_convert_to_async,
        fitness_impact=["scalability+", "complexity+", "coupling-"],
        reversible=True,
        description="Convert a sync dependency to async event-driven communication",
    )


def create_extract_interface_operator() -> MutationOperator:
    return MutationOperator(
        name="extract_interface",
        transformation_class=TransformationClass.STRUCTURAL,
        precondition=_pre_extract_interface,
        apply_fn=_apply_extract_interface,
        fitness_impact=["maintainability+", "modularity+"],
        reversible=True,
        description="Extract a service's operations into a formal interface",
    )


def create_add_audit_logging_operator() -> MutationOperator:
    return MutationOperator(
        name="add_audit_logging",
        transformation_class=TransformationClass.ADDITIVE,
        precondition=_pre_add_audit_logging,
        apply_fn=_apply_add_audit_logging,
        fitness_impact=["security+", "compliance+", "complexity+"],
        reversible=True,
        description="Add audit logging policy to a module",
    )


def create_change_scaling_policy_operator() -> MutationOperator:
    return MutationOperator(
        name="change_scaling_policy",
        transformation_class=TransformationClass.PARAMETRIC,
        precondition=_pre_change_scaling_policy,
        apply_fn=_apply_change_scaling_policy,
        fitness_impact=["scalability+", "cost+"],
        reversible=True,
        description="Change the scaling policy parameters",
    )


def create_add_event_operator() -> MutationOperator:
    return MutationOperator(
        name="add_event",
        transformation_class=TransformationClass.ADDITIVE,
        precondition=_pre_add_event,
        apply_fn=_apply_add_event,
        fitness_impact=["extensibility+", "complexity+"],
        reversible=True,
        description="Add a new event to a service",
    )


def create_merge_services_operator() -> MutationOperator:
    return MutationOperator(
        name="merge_services",
        transformation_class=TransformationClass.STRUCTURAL,
        precondition=_pre_merge_services,
        apply_fn=_apply_merge_services,
        fitness_impact=["simplicity+", "coupling+"],
        reversible=True,
        inverse_name="split_service",
        description="Merge two services into one",
    )


def create_add_circuit_breaker_operator() -> MutationOperator:
    return MutationOperator(
        name="add_circuit_breaker",
        transformation_class=TransformationClass.ADDITIVE,
        precondition=_pre_add_circuit_breaker,
        apply_fn=_apply_add_circuit_breaker,
        fitness_impact=["reliability+", "resilience+"],
        reversible=True,
        description="Add circuit breaker to a service dependency",
    )


def register_default_operators():
    """Register all default mutation operators."""
    operators = [
        create_split_module_operator(),
        create_introduce_cache_operator(),
        create_add_rate_limiting_operator(),
        create_convert_to_async_operator(),
        create_extract_interface_operator(),
        create_add_audit_logging_operator(),
        create_change_scaling_policy_operator(),
        create_add_event_operator(),
        create_merge_services_operator(),
        create_add_circuit_breaker_operator(),
    ]
    for op in operators:
        register_operator(op)


# Auto-register on import
register_default_operators()