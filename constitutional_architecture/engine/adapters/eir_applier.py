import uuid
from typing import Any

from constitutional_architecture.isr.eir.model import EIR, Transformation
from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.event import Event, EventPattern, EventGuarantee
from constitutional_architecture.isr.model.fields import Field, FieldCardinality, FieldType
from constitutional_architecture.isr.model.interface import Endpoint, HttpMethod, Interface, InterfaceType
from constitutional_architecture.isr.model.isr import ISR, ISRProvenance
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.policy import Policy, PolicyType
from constitutional_architecture.isr.model.service import Operation, OperationType, Service, ServiceDependency
from constitutional_architecture.isr.model.system import System


class EIRApplier:
    def apply(self, isr: ISR, eir: EIR) -> ISR:
        modules = list(isr.system.modules)
        for t in eir.transformations:
            modules = self._apply_transformation(modules, t)
        return ISR(
            system=System(
                id=isr.system.id,
                name=isr.system.name,
                modules=tuple(modules),
            ),
            version=isr.version + 1,
            provenance=ISRProvenance(
                parent_hash=isr.content_hash,
                mutation_description=f"EIR: {eir.summary or eir.id[:12]}",
            ),
        )

    def _apply_transformation(
        self, modules: list[Module], t: Transformation
    ) -> list[Module]:
        if t.transformation_type == "structural_add_entity":
            mod_id = t.target_node_id.replace("mod:", "")
            entity = Entity(
                id=t.parameters.get("entity_id", uuid.uuid4().hex[:8]),
                name=t.parameters.get("entity_name", "NewEntity"),
                fields=tuple(
                    Field(
                        name=f.name, field_type=FieldType(f.field_type) if isinstance(f.field_type, str) else f.field_type,
                        cardinality=FieldCardinality(f.cardinality) if isinstance(f.cardinality, str) else f.cardinality,
                    )
                    for f in t.parameters.get("fields", [])
                ) if "fields" in t.parameters else (),
            )
            return self._update_module(modules, mod_id, entities=lambda es: es + (entity,))

        elif t.transformation_type == "structural_split_module":
            mod_id = t.target_node_id.replace("mod:", "")
            source = next((m for m in modules if m.id == mod_id), None)
            if source is None:
                return modules
            new_mod_id = t.parameters.get("new_module_id", uuid.uuid4().hex[:8])
            new_mod_name = t.parameters.get("new_module_name", "SplitModule")
            moved_ids = set(t.parameters.get("moved_ids", []))
            kept_entities = tuple(e for e in source.entities if e.id not in moved_ids)
            moved_entities = tuple(e for e in source.entities if e.id in moved_ids)
            kept_services = tuple(s for s in source.services if s.id not in moved_ids)
            moved_services = tuple(s for s in source.services if s.id in moved_ids)
            new_module = Module(
                id=new_mod_id, name=new_mod_name, entities=moved_entities, services=moved_services,
            )
            updated = self._update_module(modules, mod_id, entities=lambda _: kept_entities, services=lambda _: kept_services)
            return list(updated) + [new_module]

        elif t.transformation_type == "structural_extract_interface":
            svc_id = t.target_node_id.replace("svc:", "")
            service, mod_idx, _ = self._find_service(modules, svc_id)
            if service is None:
                return modules
            iface_id = t.parameters.get("interface_id", uuid.uuid4().hex[:8])
            iface_name = t.parameters.get("interface_name", f"{service.name}API")
            iface = Interface(
                id=iface_id, name=iface_name,
                interface_type=InterfaceType.REST,
                endpoints=tuple(
                    Endpoint(id=f"ep-{uuid.uuid4().hex[:4]}", name=f"{op.name}Endpoint", method=HttpMethod.POST, path=f"/{op.name.lower()}")
                    for op in service.operations
                ),
            )
            mod = modules[mod_idx]
            modules[mod_idx] = Module(
                id=mod.id, name=mod.name, description=mod.description,
                entities=mod.entities, services=mod.services,
                interfaces=mod.interfaces + (iface,),
                policies=mod.policies, events=mod.events, workflows=mod.workflows,
            )
            return modules

        elif t.transformation_type == "security_add_policy":
            iface_id = t.target_node_id.replace("iface:", "")
            for idx, mod in enumerate(modules):
                new_ifaces = []
                changed = False
                for iface in mod.interfaces:
                    if iface.id == iface_id:
                        pol_id = t.parameters.get("policy_id", uuid.uuid4().hex[:8])
                        pol = Policy(
                            id=pol_id,
                            name=t.parameters.get("policy_name", "AuthPolicy"),
                            policy_type=PolicyType.AUTHENTICATION,
                            strategy=t.parameters.get("strategy", "OAuth2"),
                        )
                        modules[idx] = Module(
                            id=mod.id, name=mod.name, description=mod.description,
                            entities=mod.entities, services=mod.services,
                            interfaces=mod.interfaces,
                            policies=mod.policies + (pol,),
                            events=mod.events, workflows=mod.workflows,
                        )
                        changed = True
                    new_ifaces.append(iface)
            return modules

        return modules

    def _find_service(
        self, modules: list[Module], svc_id: str
    ) -> tuple[Service | None, int, int]:
        for mi, mod in enumerate(modules):
            for si, svc in enumerate(mod.services):
                if svc.id == svc_id:
                    return svc, mi, si
        return None, -1, -1

    def _update_module(
        self, modules: list[Module], mod_id: str,
        entities=None, services=None, interfaces=None,
        policies=None, events=None,
    ) -> list[Module]:
        result = list(modules)
        for idx, mod in enumerate(result):
            if mod.id == mod_id:
                result[idx] = Module(
                    id=mod.id, name=mod.name, description=mod.description,
                    entities=entities(mod.entities) if entities else mod.entities,
                    services=services(mod.services) if services else mod.services,
                    interfaces=interfaces(mod.interfaces) if interfaces else mod.interfaces,
                    policies=policies(mod.policies) if policies else mod.policies,
                    events=events(mod.events) if events else mod.events,
                    workflows=mod.workflows,
                )
        return result
