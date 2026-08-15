from __future__ import annotations

from dataclasses import replace
from typing import Any, Optional

from constitutional_architecture.compiler.compiler_context import CompilerContext
from constitutional_architecture.compiler.pass_interface import CompilerPass, PassResult
from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.event import Event
from constitutional_architecture.isr.model.interface import Endpoint, Interface
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.policy import Policy
from constitutional_architecture.isr.model.service import Operation, Service
from constitutional_architecture.isr.model.system import System
from constitutional_architecture.isr.model.workflow import Workflow


class NormalizationPass(CompilerPass):
    @property
    def identifier(self) -> str:
        return "normalization"

    @property
    def description(self) -> str:
        return "Normalize architecture into canonical form for deterministic compilation"

    @property
    def dependencies(self) -> list[str]:
        return ["validation"]

    @property
    def input_requirements(self) -> set[str]:
        return {"isr_validated"}

    @property
    def output_guarantees(self) -> set[str]:
        return {"isr_normalized", "deterministic_ordering"}

    def execute(self, ctx: CompilerContext) -> PassResult:
        isr = ctx.isr
        metrics: dict[str, Any] = {"modules_normalized": 0, "entities_sorted": 0, "services_sorted": 0, "empty_metadata_removed": 0}

        normalized_modules = []
        for module in isr.system.modules:
            normalized_modules.append(self._normalize_module(module, metrics))
        normalized_modules.sort(key=lambda m: m.name.lower())

        normalized_system = System(
            id=isr.system.id, name=isr.system.name, description=isr.system.description,
            modules=tuple(normalized_modules), deployment=isr.system.deployment,
            metadata=isr.system.metadata, global_policies=tuple(sorted(isr.system.global_policies)),
        )

        normalized_isr = ISR(system=normalized_system, version=isr.version, provenance=isr.provenance)
        ctx.update_isr(normalized_isr)

        ctx.diagnostics.info("COMP-NORM-001",
            f"ISR normalized: {metrics['modules_normalized']} modules, "
            f"{metrics['entities_sorted']} entities, {metrics['services_sorted']} services sorted")

        return PassResult(success=True, description="Normalization complete", metrics=metrics)

    def _normalize_module(self, module: Module, metrics: dict[str, Any]) -> Module:
        metrics["modules_normalized"] += 1

        entities = sorted((self._normalize_entity(e, metrics) for e in module.entities), key=lambda e: e.name.lower())
        metrics["entities_sorted"] += len(entities)

        services = sorted((self._normalize_service(s, metrics) for s in module.services), key=lambda s: s.name.lower())
        metrics["services_sorted"] += len(services)

        workflows = sorted((self._normalize_workflow(w) for w in module.workflows), key=lambda w: w.name.lower())
        policies = sorted((self._normalize_policy(p) for p in module.policies), key=lambda p: p.name.lower())
        interfaces = sorted((self._normalize_interface(i) for i in module.interfaces), key=lambda i: i.name.lower())
        events = sorted((self._normalize_event(e) for e in module.events), key=lambda e: e.name.lower())
        sorted_deps = tuple(sorted(module.dependencies))
        cleaned_metadata = self._clean_metadata(module.metadata, metrics)

        return Module(id=module.id, name=module.name, description=module.description,
                      entities=tuple(entities), services=tuple(services),
                      workflows=tuple(workflows), policies=tuple(policies),
                      interfaces=tuple(interfaces), events=tuple(events),
                      dependencies=sorted_deps, metadata=cleaned_metadata)

    def _normalize_entity(self, entity: Entity, metrics: dict[str, Any]) -> Entity:
        sorted_fields = tuple(sorted(entity.fields, key=lambda f: f.name.lower()))
        sorted_relationships = tuple(sorted(entity.relationships, key=lambda r: r.target_entity_id.lower()))
        sorted_constraints = tuple(sorted(entity.constraints, key=lambda c: c.name.lower()))
        cleaned_fields = tuple(replace(f, metadata=self._clean_metadata(f.metadata, metrics)) for f in sorted_fields)
        cleaned_metadata = self._clean_metadata(entity.metadata, metrics)
        return Entity(id=entity.id, name=entity.name, description=entity.description,
                      fields=cleaned_fields, relationships=sorted_relationships,
                      constraints=sorted_constraints, is_aggregate_root=entity.is_aggregate_root,
                      is_value_object=entity.is_value_object, metadata=cleaned_metadata)

    def _normalize_service(self, service: Service, metrics: dict[str, Any]) -> Service:
        ops = sorted((self._normalize_operation(op) for op in service.operations), key=lambda o: o.name.lower())
        sorted_deps = tuple(sorted(service.dependencies, key=lambda d: d.target_service_id.lower()))
        sorted_emitted = tuple(sorted(service.emitted_events))
        sorted_consumed = tuple(sorted(service.consumed_events))
        cleaned_metadata = self._clean_metadata(service.metadata, metrics)
        return Service(id=service.id, name=service.name, description=service.description,
                       operations=tuple(ops), dependencies=sorted_deps,
                       emitted_events=sorted_emitted, consumed_events=sorted_consumed,
                       is_stateless=service.is_stateless, metadata=cleaned_metadata)

    def _normalize_operation(self, operation: Operation) -> Operation:
        sorted_permissions = tuple(sorted(operation.required_permissions))
        return Operation(id=operation.id, name=operation.name,
                         operation_type=operation.operation_type, description=operation.description,
                         input_schema=operation.input_schema, output_schema=operation.output_schema,
                         is_idempotent=operation.is_idempotent, is_public=operation.is_public,
                         required_permissions=sorted_permissions)

    def _normalize_workflow(self, workflow: Workflow) -> Workflow:
        sorted_states = tuple(sorted(workflow.states, key=lambda s: s.name.lower()))
        sorted_transitions = tuple(sorted(workflow.transitions, key=lambda t: (t.from_state_id, t.to_state_id)))
        return Workflow(id=workflow.id, name=workflow.name, description=workflow.description,
                        states=sorted_states, transitions=sorted_transitions)

    def _normalize_policy(self, policy: Policy) -> Policy:
        sorted_roles = tuple(sorted(policy.roles))
        sorted_rules = tuple(sorted(policy.rules, key=lambda r: r.name.lower()))
        sorted_permissions = tuple(sorted(policy.permissions, key=lambda p: p.name.lower()))
        return Policy(id=policy.id, name=policy.name, policy_type=policy.policy_type,
                      description=policy.description, strategy=policy.strategy,
                      roles=sorted_roles, rules=sorted_rules, permissions=sorted_permissions)

    def _normalize_interface(self, interface: Interface) -> Interface:
        endpoints = sorted((self._normalize_endpoint(ep) for ep in interface.endpoints), key=lambda e: (e.method.value, e.path))
        return Interface(id=interface.id, name=interface.name,
                         interface_type=interface.interface_type, description=interface.description,
                         version=interface.version, endpoints=tuple(endpoints),
                         secured_by_policy_id=interface.secured_by_policy_id, is_internal=interface.is_internal)

    def _normalize_endpoint(self, endpoint: Endpoint) -> Endpoint:
        sorted_permissions = tuple(sorted(endpoint.required_permissions))
        return Endpoint(id=endpoint.id, name=endpoint.name, path=endpoint.path,
                        method=endpoint.method, description=endpoint.description,
                        input_schema=endpoint.input_schema, output_schema=endpoint.output_schema,
                        required_permissions=sorted_permissions, is_public=endpoint.is_public,
                        rate_limit=endpoint.rate_limit)

    def _normalize_event(self, event: Event) -> Event:
        return Event(id=event.id, name=event.name, description=event.description,
                     schema=event.schema, pattern=event.pattern, guarantee=event.guarantee,
                     ordering_required=event.ordering_required, ttl_seconds=event.ttl_seconds)

    def _clean_metadata(self, metadata: dict[str, Any], metrics: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        if not metadata:
            return {}
        cleaned = {k: v for k, v in metadata.items() if v not in (None, "", [], {}, ())}
        if metrics is not None and len(cleaned) < len(metadata):
            metrics["empty_metadata_removed"] += len(metadata) - len(cleaned)
        return cleaned
