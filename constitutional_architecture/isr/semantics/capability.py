"""R2.10.3-B — business capabilities primitive (first-class semantic genes).

A capability is WHAT the system can do, independent of HOW. It is a
first-class ISR gene, NEVER an alias for Workflow/Module and NEVER inferred
from implementation structure. It references behaviors, interfaces, and
constraints by IDENTITY — never by content, and never owns or wraps them.

This is what lets the Evolution Engine eventually ask "can I replace the
architecture implementing this capability?" — the capability's identity
must not change when a referenced gene evolves, so the capability can
anchor architectural replacement.

``requirement_refs`` was reserved through R2.10.3-E: carried empty,
identity-neutral, unvalidated. R2.10.3-F (requirements_acceptance_traceability)
ACTIVATES the reservation — ``Requirement`` exists, and reference integrity is
now enforced (see ``validate_system_capability_constraints``). The construct
itself is untouched by the activation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from constitutional_architecture.isr.semantics.projection import canonical_form

if TYPE_CHECKING:
    from constitutional_architecture.isr.model.isr import ISR


class CapabilityValidationError(ValueError):
    """A capability violates its construction or structural contract."""


@dataclass(frozen=True)
class BusinessCapability:
    """A first-class semantic ISR gene: WHAT the system can do, independent of HOW.

    References behaviors, interfaces, constraints, and requirements by IDENTITY,
    never by content, and never owns or wraps them. This is explicitly NOT an
    alias for Workflow/Module — it is a semantic layer above implementation, so
    the Evolution Engine can reason about replacing the architecture that
    realizes a capability without touching the capability itself.

    requirement_refs was reserved (carried empty, unvalidated) until
    requirements_acceptance_traceability landed (R2.10.3-F), which ACTIVATED
    its reference integrity without touching this construct: a capability with
    empty requirement_refs is byte-identical before and after activation.
    """

    capability_id: str
    intent: str
    behavior_refs: tuple[str, ...] = ()
    interface_refs: tuple[str, ...] = ()
    constraint_refs: tuple[str, ...] = ()
    requirement_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.capability_id:
            raise CapabilityValidationError("capability_id is required")
        if not self.intent:
            raise CapabilityValidationError(
                "intent is required: a capability IS its semantic meaning"
            )


def _behavior_ids(system: Any) -> set[str]:
    return {
        workflow.id
        for module in system.modules
        for workflow in module.workflows
    }


def _interface_ids(system: Any) -> set[str]:
    return {
        interface.id
        for module in system.modules
        for interface in module.interfaces
    }


def _constraint_ids(system: Any) -> set[str]:
    ids = {constraint.id for constraint in system.constraints}
    for module in system.modules:
        for entity in module.entities:
            ids.update(constraint.id for constraint in entity.constraints)
    return ids


def validate_system_capability_constraints(system: Any) -> tuple[str, ...]:
    """Reference integrity for one system's capability map.

    Rejects, pre-execution: duplicate capability ids, dangling
    behavior/interface/constraint references. Since R2.10.3-F
    (requirements_acceptance_traceability), ``requirement_refs`` is ACTIVE:
    dangling requirement references are rejected against
    ``System.requirements``. Empty tuple means valid.
    """
    errors: list[str] = []
    behavior_ids = _behavior_ids(system)
    interface_ids = _interface_ids(system)
    constraint_ids = _constraint_ids(system)
    requirement_ids = {r.requirement_id for r in system.requirements}
    seen: set[str] = set()
    for capability in system.business_capabilities:
        if capability.capability_id in seen:
            errors.append(
                f"duplicate business capability id '{capability.capability_id}'"
            )
        seen.add(capability.capability_id)
        for behavior_ref in capability.behavior_refs:
            if behavior_ref not in behavior_ids:
                errors.append(
                    f"business capability '{capability.capability_id}' references "
                    f"unknown behavior '{behavior_ref}'"
                )
        for interface_ref in capability.interface_refs:
            if interface_ref not in interface_ids:
                errors.append(
                    f"business capability '{capability.capability_id}' references "
                    f"unknown interface '{interface_ref}'"
                )
        for constraint_ref in capability.constraint_refs:
            if constraint_ref not in constraint_ids:
                errors.append(
                    f"business capability '{capability.capability_id}' references "
                    f"unknown constraint '{constraint_ref}'"
                )
        for requirement_ref in capability.requirement_refs:
            if requirement_ref not in requirement_ids:
                errors.append(
                    f"business capability '{capability.capability_id}' references "
                    f"unknown requirement '{requirement_ref}'"
                )
    return tuple(errors)


def project_business_capabilities(isr: Any) -> tuple[dict[str, Any], ...]:
    """Backend-independent semantic projection of the capability map.

    Returns capability semantics (intent + reference identities). Never
    Python classes, REST routes, microservices, or database tables — those
    are compiler-backend realizations of the referenced genes, not the
    capability.
    """
    return tuple(
        canonical_form(capability)
        for capability in getattr(isr.system, "business_capabilities", ())
    )