import uuid
from typing import Any

from constitutional_architecture.engine.mutations.base import MutationOperator
from constitutional_architecture.isr.model.event import Event, EventPattern, EventGuarantee
from constitutional_architecture.isr.model.isr import ISR, ISRProvenance
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.service import ServiceDependency
from constitutional_architecture.isr.model.system import System


class IntroduceEventBusMutation(MutationOperator):
    identifier = "behavioural_introduce_event_bus"
    description = "Replace direct service-to-service calls with event-based communication"

    def apply(self, isr: ISR, target_id: str, params: dict[str, Any] | None = None) -> ISR:
        params = params or {}
        svc_id = target_id.replace("svc:", "")
        event_name = params.get("event_name", f"{svc_id}DomainEvent")

        modules = list(isr.system.modules)
        for mi, mod in enumerate(modules):
            new_services = list(mod.services)
            changed = False
            for si, svc in enumerate(new_services):
                if svc.id == svc_id:
                    event_id = uuid.uuid4().hex[:8]
                    evt = Event(
                        id=event_id,
                        name=event_name,
                        pattern=EventPattern.PUBLISH_SUBSCRIBE,
                        guarantee=EventGuarantee.AT_LEAST_ONCE,
                    )
                    new_deps = tuple(
                        d for d in svc.dependencies
                        if not any(other.id == d.target_service_id for other in mod.services
                                   if other.id != svc.id)
                    )
                    new_services[si] = svc  # keep unchanged; event added at module level
                    modules[mi] = Module(
                        id=mod.id, name=mod.name, description=mod.description,
                        entities=mod.entities, services=tuple(new_services),
                        interfaces=mod.interfaces, policies=mod.policies,
                        events=mod.events + (evt,), workflows=mod.workflows,
                    )
                    changed = True
                    break
            if changed:
                break

        return ISR(
            system=System(id=isr.system.id, name=isr.system.name, modules=tuple(modules)),
            version=isr.version + 1,
            provenance=ISRProvenance(
                parent_hash=isr.content_hash,
                mutation_description=f"Introduced event bus pattern via '{event_name}' for service '{svc_id}'",
            ),
        )
