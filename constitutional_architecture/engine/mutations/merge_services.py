import uuid
from typing import Any

from constitutional_architecture.engine.mutations.base import MutationOperator
from constitutional_architecture.isr.model.isr import ISR, ISRProvenance
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.service import Operation, Service
from constitutional_architecture.isr.model.system import System


class MergeServicesMutation(MutationOperator):
    identifier = "structural_merge_services"
    description = "Merge two services into one unified service"

    def apply(self, isr: ISR, target_id: str, params: dict[str, Any] | None = None) -> ISR:
        params = params or {}
        svc_a_id = target_id.replace("svc:", "")
        svc_b_id = params.get("target_service_id", "").replace("svc:", "")
        if not svc_b_id:
            return isr

        merged_name = params.get("merged_name", f"Unified{svc_a_id.title()}")

        modules = list(isr.system.modules)
        svc_a = svc_b = None
        mod_a_idx = mod_b_idx = -1
        svc_a_idx = svc_b_idx = -1

        for mi, mod in enumerate(modules):
            for si, svc in enumerate(mod.services):
                if svc.id == svc_a_id:
                    svc_a, mod_a_idx, svc_a_idx = svc, mi, si
                if svc.id == svc_b_id:
                    svc_b, mod_b_idx, svc_b_idx = svc, mi, si

        if svc_a is None or svc_b is None:
            return isr

        merged_id = params.get("merged_id", uuid.uuid4().hex[:8])
        merged = Service(
            id=merged_id,
            name=merged_name,
            operations=svc_a.operations + svc_b.operations,
            dependencies=svc_a.dependencies + tuple(
                d for d in svc_b.dependencies if d.target_service_id != svc_a.id
            ),
            is_stateless=svc_a.is_stateless and svc_b.is_stateless,
        )

        def _replace_svc(mod: Module, old_id: str, replacement: Service | None) -> Module:
            new_services = tuple(s for s in mod.services if s.id != old_id)
            if replacement is not None:
                new_services = new_services + (replacement,)
            return Module(
                id=mod.id, name=mod.name, description=mod.description,
                entities=mod.entities, services=new_services,
                interfaces=mod.interfaces, policies=mod.policies,
                events=mod.events, workflows=mod.workflows,
            )

        if mod_a_idx == mod_b_idx:
            mod = modules[mod_a_idx]
            other_svcs = tuple(s for s in mod.services if s.id not in (svc_a_id, svc_b_id))
            modules[mod_a_idx] = Module(
                id=mod.id, name=mod.name, description=mod.description,
                entities=mod.entities, services=other_svcs + (merged,),
                interfaces=mod.interfaces, policies=mod.policies,
                events=mod.events, workflows=mod.workflows,
            )
        else:
            modules[mod_a_idx] = _replace_svc(modules[mod_a_idx], svc_a_id, None)
            modules[mod_b_idx] = _replace_svc(modules[mod_b_idx], svc_b_id, merged)

        return ISR(
            system=System(id=isr.system.id, name=isr.system.name, modules=tuple(modules)),
            version=isr.version + 1,
            provenance=ISRProvenance(
                parent_hash=isr.content_hash,
                mutation_description=f"Merged services '{svc_a.name}' + '{svc_b.name}' -> '{merged_name}'",
            ),
        )
