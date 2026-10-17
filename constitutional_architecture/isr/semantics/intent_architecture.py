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
    architecture_ref = getattr(system, "intent_architecture_ref", None)
    if architecture_ref is not None:
        if not architecture_ref.projection_complete:
            errors.extend(
                f"typed architecture projection incomplete: {item}"
                for item in architecture_ref.projection_blockers
            )
            if not architecture_ref.projection_blockers:
                errors.append("typed architecture projection is marked incomplete without blockers")
        required_postures = (
            "security_posture",
            "infrastructure_posture",
            "deployment_posture",
            "testing_posture",
            "documentation_posture",
            "operational_posture",
        )
        for posture_name in required_postures:
            if getattr(system, posture_name, None) is None:
                errors.append(
                    "typed architecture projection is missing first-class "
                    + posture_name.replace("_", " ")
                )
    capabilities = {
        item.capability_id for item in getattr(system, "business_capabilities", ())
    }
    service_owner: dict[str, str] = {}
    component_ids: set[str] = set()
    entity_owner: dict[str, str] = {}
    event_owner: dict[str, str] = {}
    api_ids: set[str] = set()
    allowed_communication_styles = {
        "synchronous_request_response", "asynchronous_event", "batch", "streaming"
    }
    allowed_interaction_styles = {"request_response", "event_driven", "batch", "streaming"}
    allowed_operation_semantics = {"command", "query"}
    allowed_event_ordering = {"none", "partition_ordered", "totally_ordered"}

    for module in modules:
        for term, definition in getattr(module, "ubiquitous_language", ()):
            if not term.strip() or not definition.strip():
                errors.append(f"module '{module.id}' has an empty ubiquitous-language term or definition")
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
            if service.is_stateless is not None and not isinstance(service.is_stateless, bool):
                errors.append(
                    f"service '{service.id}' has invalid statefulness value "
                    f"{service.is_stateless!r}; expected bool or unknown"
                )
            for capability_id in service.exposed_capability_refs:
                if capability_id not in capabilities:
                    errors.append(
                        f"service '{service.id}' exposes unknown capability '{capability_id}'"
                    )
            unknown_styles = set(service.communication_styles) - allowed_communication_styles
            if unknown_styles:
                errors.append(
                    f"service '{service.id}' has unsupported communication styles: "
                    + ", ".join(sorted(unknown_styles))
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
        for entity in module.entities:
            for relationship in entity.relationships:
                if relationship.target_entity_id not in entity_owner and relationship.target_entity_id not in {
                    candidate.id
                    for candidate_module in modules
                    for candidate in candidate_module.entities
                }:
                    errors.append(
                        f"entity '{entity.id}' references unknown entity "
                        f"'{relationship.target_entity_id}'"
                    )
        for event in module.events:
            if event.id in event_owner:
                errors.append(f"duplicate event ID '{event.id}'")
            event_owner[event.id] = module.id
            if event.ordering_semantics not in allowed_event_ordering:
                errors.append(
                    f"event '{event.id}' has unsupported ordering semantics "
                    f"'{event.ordering_semantics}'"
                )
        for api in getattr(module, "api_contracts", ()):
            if api.api_id in api_ids:
                errors.append(f"duplicate API contract ID '{api.api_id}'")
            api_ids.add(api.api_id)
            if api.interaction_style not in allowed_interaction_styles:
                errors.append(
                    f"API '{api.api_id}' has unsupported interaction style '{api.interaction_style}'"
                )
            for operation in api.operations:
                if operation.semantics not in allowed_operation_semantics:
                    errors.append(
                        f"API '{api.api_id}' operation '{operation.name}' has unsupported "
                        f"semantics '{operation.semantics}'"
                    )
                if not isinstance(operation.idempotent, bool):
                    errors.append(
                        f"API '{api.api_id}' operation '{operation.name}' has non-boolean idempotency"
                    )

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
