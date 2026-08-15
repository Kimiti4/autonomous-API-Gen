"""
Phase 8: Component Evolution Runtime.

Components evolve their API contracts and State Machines within the ISR.
Mutating a component's API automatically flags dependent Pages for re-evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from constitutional_architecture.isr.profiles.frontend_model import (
    FrontendISRProfile, Component, PropertyDefinition, EventDefinition,
    ComponentNode,
)


@dataclass
class ComponentAPIMutation:
    component_id: str
    mutation_type: str
    description: str
    affected_pages: list[str] = field(default_factory=list)


class ComponentAPIMutator:
    def refactor_props_to_objects(self, profile: FrontendISRProfile, component_id: str) -> list[ComponentAPIMutation]:
        idx = -1
        for i, c in enumerate(profile.components):
            if c.id == component_id:
                idx = i
                break
        if idx == -1 or len(profile.components[idx].inputs) < 5:
            return []

        comp = profile.components[idx]
        groups: dict[str, list[PropertyDefinition]] = {}
        for prop in comp.inputs:
            prefix = prop.name.split("_")[0] if "_" in prop.name else "general"
            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(prop)

        new_inputs = []
        mutations: list[ComponentAPIMutation] = []
        for group_name, props in groups.items():
            if len(props) > 1:
                new_inputs.append(PropertyDefinition(
                    name=group_name,
                    type="object",
                    required=any(p.required for p in props),
                    default_value={p.name: p.default_value for p in props if p.default_value is not None},
                ))
                mutations.append(ComponentAPIMutation(
                    component_id=component_id,
                    mutation_type="group_props",
                    description=f"Grouped {len(props)} props under '{group_name}'",
                ))
            else:
                new_inputs.append(props[0])

        new_comp = Component(
            id=comp.id, name=comp.name, purpose=comp.purpose,
            inputs=tuple(new_inputs), outputs=comp.outputs,
            states=comp.states, variants=comp.variants,
            allowed_children=comp.allowed_children,
            allowed_parents=comp.allowed_parents,
            token_dependencies=comp.token_dependencies,
            accessibility_contract=comp.accessibility_contract,
            genome=comp.genome, fitness_targets=comp.fitness_targets,
        )

        affected = self._find_dependent_pages(profile, component_id)
        for page_id in affected:
            for m in mutations:
                m.affected_pages.append(page_id)

        return mutations

    def inject_state(self, profile: FrontendISRProfile, component_id: str, new_state: str) -> Optional[ComponentAPIMutation]:
        idx = -1
        for i, c in enumerate(profile.components):
            if c.id == component_id:
                idx = i
                break
        if idx == -1:
            return None
        comp = profile.components[idx]
        if new_state in comp.states:
            return None
        new_states = comp.states + (new_state,)
        return ComponentAPIMutation(
            component_id=component_id,
            mutation_type="inject_state",
            description=f"Injected state '{new_state}' into component",
            affected_pages=list(self._find_dependent_pages(profile, component_id)),
        )

    def _find_dependent_pages(self, profile: FrontendISRProfile, component_id: str) -> set[str]:
        affected: set[str] = set()
        for page in profile.pages:
            if self._references_component(page.component_tree, component_id):
                affected.add(page.id)
            for state_node in page.view_states.values():
                if self._references_component(state_node, component_id):
                    affected.add(page.id)
        return affected

    def _references_component(self, node: ComponentNode, component_id: str) -> bool:
        if node.component_ref == component_id:
            return True
        for child in node.children:
            if self._references_component(child, component_id):
                return True
        return False
