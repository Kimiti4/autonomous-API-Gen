import uuid
from typing import Any

from constitutional_architecture.engine.mutations.base import MutationOperator
from constitutional_architecture.isr.model.isr import ISR, ISRProvenance
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.system import System


class SplitModuleMutation(MutationOperator):
    identifier = "structural_split_module"
    description = "Split a module into two by redistributing entities"

    def apply(self, isr: ISR, target_id: str, params: dict[str, Any] | None = None) -> ISR:
        params = params or {}
        mod_id = target_id.replace("mod:", "")
        source = next((m for m in isr.system.modules if m.id == mod_id), None)
        if source is None:
            return isr

        new_mod_id = params.get("new_module_id", uuid.uuid4().hex[:8])
        new_mod_name = params.get("new_module_name", f"{source.name}Split")
        extract_names = set(params.get("extract_entities", []))

        kept_entities = tuple(e for e in source.entities if e.name not in extract_names)
        moved_entities = tuple(e for e in source.entities if e.name in extract_names)

        new_module = Module(id=new_mod_id, name=new_mod_name, entities=moved_entities)

        updated_modules = []
        for m in isr.system.modules:
            if m.id == mod_id:
                updated_modules.append(Module(
                    id=m.id, name=m.name, description=m.description,
                    entities=kept_entities, services=m.services,
                    interfaces=m.interfaces, policies=m.policies,
                    events=m.events, workflows=m.workflows,
                ))
            else:
                updated_modules.append(m)
        updated_modules.append(new_module)

        return ISR(
            system=System(id=isr.system.id, name=isr.system.name, modules=tuple(updated_modules)),
            version=isr.version + 1,
            provenance=ISRProvenance(
                parent_hash=isr.content_hash,
                mutation_description=f"Split module '{source.name}' -> '{new_mod_name}'",
            ),
        )
