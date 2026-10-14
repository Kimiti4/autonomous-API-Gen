"""First-class identity and gate state for a typed architecture projection."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntentArchitectureReference:
    system_model_sha256: str
    projection_complete: bool
    projection_blockers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.system_model_sha256:
            raise ValueError("typed architecture projection requires a SystemModel hash")
        if self.projection_complete and self.projection_blockers:
            raise ValueError("a complete architecture projection cannot contain blockers")
        if not self.projection_complete and not self.projection_blockers:
            raise ValueError("an incomplete architecture projection must record blockers")


def validate_system_architecture_projection(system: object) -> tuple[str, ...]:
    """Validate first-class architecture references after lowering."""
    errors: list[str] = []
    modules = tuple(getattr(system, "modules", ()))
    if getattr(system, "intent_architecture_ref", None) is not None:
        if getattr(system, "security_posture", None) is None:
            errors.append("typed architecture projection is missing first-class security posture")
    capabilities = {
        item.capability_id for item in getattr(system, "business_capabilities", ())
    }
    service_owner: dict[str, str] = {}
    component_ids: set[str] = set()
    entity_owner: dict[str, str] = {}
    event_owner: dict[str, str] = {}
    api_ids: set[str] = set()

    for module in modules:
        for capability_id in getattr(module, "capability_refs", ()):
            if capability_id not in capabilities:
                errors.append(
                    f"module '{module.id}' references unknown capability '{capability_id}'"
                )
        for service in module.services:
            if service.id in service_owner:
                errors.append(f"duplicate service ID '{service.id}'")
            service_owner[service.id] = module.id
            if service.domain_id is not None and service.domain_id != module.id:
                errors.append(
                    f"service '{service.id}' domain '{service.domain_id}' does not match "
                    f"owning module '{module.id}'"
                )
            for capability_id in service.exposed_capability_refs:
                if capability_id not in capabilities:
                    errors.append(
                        f"service '{service.id}' exposes unknown capability '{capability_id}'"
                    )
        for component in getattr(module, "components", ()):
            if component.component_id in component_ids:
                errors.append(f"duplicate component ID '{component.component_id}'")
            component_ids.add(component.component_id)
            if component.service_id not in service_owner:
                errors.append(
                    f"component '{component.component_id}' references unknown service "
                    f"'{component.service_id}'"
                )
            elif service_owner[component.service_id] != module.id:
                errors.append(
                    f"component '{component.component_id}' is not colocated with its service"
                )
        for entity in module.entities:
            if entity.id in entity_owner:
                errors.append(f"duplicate entity ID '{entity.id}'")
            entity_owner[entity.id] = module.id
            if entity.owning_service_id is not None:
                if entity.owning_service_id not in service_owner:
                    errors.append(
                        f"entity '{entity.id}' references unknown owning service "
                        f"'{entity.owning_service_id}'"
                    )
                elif service_owner[entity.owning_service_id] != module.id:
                    errors.append(
                        f"entity '{entity.id}' is not colocated with its owning service"
                    )
        for event in module.events:
            if event.id in event_owner:
                errors.append(f"duplicate event ID '{event.id}'")
            event_owner[event.id] = module.id
        for api in getattr(module, "api_contracts", ()):
            if api.api_id in api_ids:
                errors.append(f"duplicate API contract ID '{api.api_id}'")
            api_ids.add(api.api_id)

    for module in modules:
        for component in getattr(module, "components", ()):
            if component.service_id not in service_owner:
                errors.append(
                    f"component '{component.component_id}' references unknown service "
                    f"'{component.service_id}'"
                )
        for event in module.events:
            if event.producer_service_id is not None:
                if event.producer_service_id not in service_owner:
                    errors.append(
                        f"event '{event.id}' references unknown producer service "
                        f"'{event.producer_service_id}'"
                    )
                elif service_owner[event.producer_service_id] != module.id:
                    errors.append(
                        f"event '{event.id}' is not colocated with its producer service"
                    )
            for consumer_id in event.consumer_service_ids:
                if consumer_id not in service_owner:
                    errors.append(
                        f"event '{event.id}' references unknown consumer service '{consumer_id}'"
                    )
            if event.payload_model_id is not None and event.payload_model_id not in entity_owner:
                errors.append(
                    f"event '{event.id}' references unknown payload model '{event.payload_model_id}'"
                )
        for api in getattr(module, "api_contracts", ()):
            if api.provider_service_id not in service_owner:
                errors.append(
                    f"API '{api.api_id}' references unknown provider service "
                    f"'{api.provider_service_id}'"
                )
            elif service_owner[api.provider_service_id] != module.id:
                errors.append(
                    f"API '{api.api_id}' is not colocated with its provider service"
                )
            for consumer_id in api.consumer_service_ids:
                if consumer_id not in service_owner:
                    errors.append(
                        f"API '{api.api_id}' references unknown consumer service '{consumer_id}'"
                    )

    return tuple(errors)
