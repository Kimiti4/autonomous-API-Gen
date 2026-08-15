from __future__ import annotations

from dataclasses import replace
from typing import Any, TYPE_CHECKING

from constitutional_architecture.isr.model.isr import ISR

if TYPE_CHECKING:
    from constitutional_architecture.compiler.compiler_context import CompilerContext
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.service import Service
from constitutional_architecture.isr.model.system import System
from constitutional_architecture.isr.model.workflow import StateType, Workflow


class OptimizationRecord:
    def __init__(self, name: str, description: str, nodes_affected: int = 0, semantics_preserved: bool = True) -> None:
        self.name = name
        self.description = description
        self.nodes_affected = nodes_affected
        self.semantics_preserved = semantics_preserved


class OptimizationEngine:
    def optimize(self, ctx: CompilerContext, level: int = 1) -> list[OptimizationRecord]:
        records: list[OptimizationRecord] = []
        isr = ctx.isr

        if level >= 1:
            records.extend(self._remove_unreachable_states(ctx))
            records.extend(self._remove_duplicate_dependencies(ctx))
            records.extend(self._remove_empty_interfaces(ctx))

        if level >= 2:
            records.extend(self._simplify_transitive_dependencies(ctx))

        if records:
            optimized_isr = self._apply_optimizations(isr, records)
            ctx.update_isr(optimized_isr)

        return records

    def _remove_unreachable_states(self, ctx: CompilerContext) -> list[OptimizationRecord]:
        isr = ctx.isr
        total_removed = 0
        for module in isr.system.modules:
            for workflow in module.workflows:
                unreachable = self._find_unreachable_states(workflow)
                total_removed += len(unreachable)
        if total_removed > 0:
            return [OptimizationRecord(
                name="remove_unreachable_states",
                description=f"Removed {total_removed} unreachable workflow state(s)",
                nodes_affected=total_removed)]
        return []

    def _find_unreachable_states(self, workflow: Workflow) -> set[str]:
        if not workflow.states:
            return set()
        initial_ids = {s.id for s in workflow.states if s.state_type == StateType.INITIAL}
        if not initial_ids:
            return set()
        reachable: set[str] = set(initial_ids)
        queue = list(initial_ids)
        while queue:
            current = queue.pop(0)
            for transition in workflow.transitions:
                if transition.from_state_id == current and transition.to_state_id not in reachable:
                    reachable.add(transition.to_state_id)
                    queue.append(transition.to_state_id)
        all_ids = {s.id for s in workflow.states}
        return all_ids - reachable

    def _remove_duplicate_dependencies(self, ctx: CompilerContext) -> list[OptimizationRecord]:
        isr = ctx.isr
        total_removed = 0
        for module in isr.system.modules:
            seen = set()
            for dep in module.dependencies:
                if dep in seen:
                    total_removed += 1
                seen.add(dep)
            for service in module.services:
                seen_svc = set()
                for dep in service.dependencies:
                    key = dep.target_service_id
                    if key in seen_svc:
                        total_removed += 1
                    seen_svc.add(key)
        if total_removed > 0:
            return [OptimizationRecord(
                name="remove_duplicate_dependencies",
                description=f"Removed {total_removed} duplicate dependency declaration(s)",
                nodes_affected=total_removed)]
        return []

    def _remove_empty_interfaces(self, ctx: CompilerContext) -> list[OptimizationRecord]:
        isr = ctx.isr
        total_removed = 0
        for module in isr.system.modules:
            for interface in module.interfaces:
                if not interface.endpoints:
                    total_removed += 1
        if total_removed > 0:
            return [OptimizationRecord(
                name="remove_empty_interfaces",
                description=f"Identified {total_removed} empty interface(s) for removal",
                nodes_affected=total_removed)]
        return []

    def _simplify_transitive_dependencies(self, ctx: CompilerContext) -> list[OptimizationRecord]:
        isr = ctx.isr
        module_ids = {m.id for m in isr.system.modules}
        adjacency: dict[str, set[str]] = {m.id: set() for m in isr.system.modules}
        for module in isr.system.modules:
            for dep in module.dependencies:
                if dep in module_ids:
                    adjacency[module.id].add(dep)
        removable: list[tuple[str, str]] = []
        for mod_id, direct_deps in adjacency.items():
            for dep in list(direct_deps):
                for other_dep in direct_deps:
                    if other_dep == dep:
                        continue
                    if self._can_reach(adjacency, other_dep, dep, exclude_direct=True):
                        removable.append((mod_id, dep))
                        break
        if removable:
            return [OptimizationRecord(
                name="simplify_transitive_dependencies",
                description=f"Identified {len(removable)} transitive dependency(ies) for removal",
                nodes_affected=len(removable))]
        return []

    def _can_reach(self, adjacency: dict[str, set[str]], start: str, target: str, exclude_direct: bool = False) -> bool:
        visited: set[str] = set()
        queue = [start]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for neighbor in adjacency.get(current, set()):
                if exclude_direct and current == start and neighbor == target:
                    continue
                if neighbor == target:
                    return True
                if neighbor not in visited:
                    queue.append(neighbor)
        return False

    def _apply_optimizations(self, isr: ISR, records: list[OptimizationRecord]) -> ISR:
        optimized_modules = []
        for module in isr.system.modules:
            optimized_modules.append(self._optimize_module(module, records))
        optimized_system = System(
            id=isr.system.id, name=isr.system.name, description=isr.system.description,
            modules=tuple(optimized_modules), deployment=isr.system.deployment,
            metadata=isr.system.metadata, global_policies=isr.system.global_policies,
        )
        return ISR(system=optimized_system, version=isr.version, provenance=isr.provenance)

    def _optimize_module(self, module: Module, records: list[OptimizationRecord]) -> Module:
        seen = set()
        unique_deps = [d for d in module.dependencies if not (d in seen or seen.add(d))]

        optimized_services = []
        for service in module.services:
            seen_svc = set()
            unique_svc_deps = [d for d in service.dependencies if not (d.target_service_id in seen_svc or seen_svc.add(d.target_service_id))]
            optimized_service = Service(
                id=service.id, name=service.name, description=service.description,
                operations=service.operations, dependencies=tuple(unique_svc_deps),
                emitted_events=service.emitted_events, consumed_events=service.consumed_events,
                is_stateless=service.is_stateless, metadata=service.metadata,
            )
            optimized_services.append(optimized_service)

        optimized_workflows = []
        for workflow in module.workflows:
            unreachable = self._find_unreachable_states(workflow)
            if unreachable:
                reachable_states = tuple(s for s in workflow.states if s.id not in unreachable)
                reachable_transitions = tuple(
                    t for t in workflow.transitions
                    if t.from_state_id not in unreachable and t.to_state_id not in unreachable
                )
                optimized_workflows.append(Workflow(
                    id=workflow.id, name=workflow.name, description=workflow.description,
                    states=reachable_states, transitions=reachable_transitions,
                ))
            else:
                optimized_workflows.append(workflow)

        empty_iface_ids = {i.id for i in module.interfaces if not i.endpoints}
        optimized_interfaces = tuple(i for i in module.interfaces if i.id not in empty_iface_ids)

        return Module(
            id=module.id, name=module.name, description=module.description,
            entities=module.entities, services=tuple(optimized_services),
            workflows=tuple(optimized_workflows), policies=module.policies,
            interfaces=optimized_interfaces, events=module.events,
            dependencies=tuple(unique_deps), metadata=module.metadata,
        )
