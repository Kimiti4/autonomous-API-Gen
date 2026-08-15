import uuid
from typing import Any

from constitutional_architecture.engine.mutations.base import MutationOperator
from constitutional_architecture.isr.model.isr import ISR, ISRProvenance
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.policy import Policy, PolicyType
from constitutional_architecture.isr.model.system import System


class ReplaceAuthStrategyMutation(MutationOperator):
    identifier = "security_replace_auth_strategy"
    description = "Replace the authorization strategy across one or more interfaces"

    def apply(self, isr: ISR, target_id: str, params: dict[str, Any] | None = None) -> ISR:
        params = params or {}
        iface_id = target_id.replace("iface:", "")
        new_strategy = params.get("strategy", "OAuth2")
        new_policy_type_str = params.get("policy_type", "authorization")

        modules = list(isr.system.modules)
        for mi, mod in enumerate(modules):
            new_policies = list(mod.policies)
            changed = False

            for pi in range(len(new_policies)):
                pol = new_policies[pi]
                secured_ifaces = [i for i in mod.interfaces if i.secured_by_policy_id == pol.id]
                if any(i.id == iface_id for i in secured_ifaces):
                    new_policies[pi] = Policy(
                        id=pol.id, name=pol.name,
                        policy_type=PolicyType(new_policy_type_str) if new_policy_type_str != pol.policy_type.value else pol.policy_type,
                        strategy=new_strategy,
                    )
                    changed = True

            if changed:
                modules[mi] = Module(
                    id=mod.id, name=mod.name, description=mod.description,
                    entities=mod.entities, services=mod.services,
                    interfaces=mod.interfaces, policies=tuple(new_policies),
                    events=mod.events, workflows=mod.workflows,
                )
                break

        return ISR(
            system=System(id=isr.system.id, name=isr.system.name, modules=tuple(modules)),
            version=isr.version + 1,
            provenance=ISRProvenance(
                parent_hash=isr.content_hash,
                mutation_description=f"Replaced auth strategy to '{new_strategy}' for interface '{iface_id}'",
            ),
        )
