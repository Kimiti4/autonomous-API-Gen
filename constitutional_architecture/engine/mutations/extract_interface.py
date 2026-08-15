import uuid
from typing import Any

from constitutional_architecture.engine.mutations.base import MutationOperator
from constitutional_architecture.isr.model.interface import Endpoint, HttpMethod, Interface, InterfaceType
from constitutional_architecture.isr.model.isr import ISR, ISRProvenance
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.system import System


class ExtractInterfaceMutation(MutationOperator):
    identifier = "structural_extract_interface"
    description = "Extract a new interface from an existing service's operations"

    def apply(self, isr: ISR, target_id: str, params: dict[str, Any] | None = None) -> ISR:
        params = params or {}
        svc_id = target_id.replace("svc:", "")

        modules = list(isr.system.modules)
        for mi, mod in enumerate(modules):
            for si, svc in enumerate(mod.services):
                if svc.id == svc_id:
                    iface_id = params.get("interface_id", uuid.uuid4().hex[:8])
                    iface_name = params.get("name", f"{svc.name}API")
                    iface = Interface(
                        id=iface_id, name=iface_name,
                        interface_type=InterfaceType.REST,
                        endpoints=tuple(
                            Endpoint(
                                id=f"ep-{uuid.uuid4().hex[:4]}",
                                name=f"{op.name}Endpoint",
                                method=HttpMethod.POST,
                                path=f"/{op.name.lower()}",
                            )
                            for op in svc.operations
                        ),
                    )
                    modules[mi] = Module(
                        id=mod.id, name=mod.name, description=mod.description,
                        entities=mod.entities, services=mod.services,
                        interfaces=mod.interfaces + (iface,),
                        policies=mod.policies, events=mod.events, workflows=mod.workflows,
                    )
                    return ISR(
                        system=System(id=isr.system.id, name=isr.system.name, modules=tuple(modules)),
                        version=isr.version + 1,
                        provenance=ISRProvenance(
                            parent_hash=isr.content_hash,
                            mutation_description=f"Extracted interface '{iface_name}' from service '{svc.name}'",
                        ),
                    )
        return isr
