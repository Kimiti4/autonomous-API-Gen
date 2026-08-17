"""R2.10.3-E — architecture boundaries primitive (constraint on relationships).

A boundary is a SEMANTIC constraint on relationships between genes — NOT a
module, a service, or a deployment unit. It declares what may or may not
cross it. A backend may realize it as a module / package / process /
service / network boundary / repository / container, but NONE of those
realizations is part of this primitive.

This elevates R2.8.6's architectural-integrity semantics — protected
boundary + forbidden dependency — from anti-gaming infrastructure into the
constitutional ISR as a first-class gene. The gene DECLARES the constraint;
the existing R2.8.6 enforcement machinery is what upholds it (wiring the
enforcement to read from the gene is a follow-up integration, deliberately
NOT part of this landing).

Deliberately the minimum carrier: ``member_refs`` + ``forbidden_dependency_refs``
+ ``protected`` is exactly the semantic content R2.8.6 enforced on the FSM
substrate, now generalized. Allowed crossings and richer dependency-direction
semantics are future extensions — added only when a concrete substrate needs
them, per "complexity must always provide measurable architectural value."

Composes by reference, never by responsibility: capabilities reference
boundaries, reliability requirements target boundaries, boundaries constrain
relationships. No inheritance, no shared mutable state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from constitutional_architecture.isr.semantics.projection import canonical_form, canonicalize

if TYPE_CHECKING:
    from constitutional_architecture.isr.model.isr import ISR


class BoundaryValidationError(ValueError):
    """A boundary violates its construction or structural contract."""


@dataclass(frozen=True)
class ArchitecturalBoundary:
    """A semantic constraint on relationships between genes.

    NOT a module, a service, or a deployment unit. Declares what may or may
    not cross the boundary. A backend may realize it as a module / package /
    process / service / network boundary / repository / container, but NONE
    of those realizations is part of this primitive.

    ``member_refs`` name the enclosed genes (by ISR identity); 
    ``forbidden_dependency_refs`` name genes the members must NOT depend on;
    ``protected`` marks removal as a constitutional violation (the R2.8.6
    protected-boundary semantics, elevated to the ISR); ``crossing_invariants``
    declare semantic invariants governing what may cross.
    """

    boundary_id: str
    member_refs: tuple[str, ...]  # genes enclosed (by id)
    forbidden_dependency_refs: tuple[str, ...] = ()  # genes members must NOT depend on
    protected: bool = False  # removal = constitutional violation
    crossing_invariants: tuple[str, ...] = ()  # invariants governing crossings

    def __post_init__(self) -> None:
        if not self.boundary_id:
            raise BoundaryValidationError("boundary_id is required")
        if not self.member_refs:
            raise BoundaryValidationError("a boundary must enclose something")
        overlap = set(self.member_refs) & set(self.forbidden_dependency_refs)
        if overlap:
            raise BoundaryValidationError(
                f"genes cannot be both members and forbidden dependencies: "
                f"{sorted(overlap)}"
            )


# -- realization-neutrality lint (the boundary's double guard) ------------------

BOUNDARY_MECHANISM_TERMS: frozenset[str] = frozenset({
    # realization technologies — never the semantic constraint
    "package", "namespace", "container", "pod", "process_id",
    "service_mesh", "network_zone", "vpc", "subnet", "region",
    "deployment_unit", "kubernetes", "docker",
})


def boundary_mechanism_hits(boundary: ArchitecturalBoundary) -> tuple[str, ...]:
    """Which realization terms (if any) leaked into a boundary's semantic form."""
    lowered = canonicalize(boundary).lower()
    return tuple(term for term in BOUNDARY_MECHANISM_TERMS if term in lowered)


def assert_boundary_technology_agnostic(boundary: ArchitecturalBoundary) -> None:
    """Gate: no realization technology may leak into the semantic representation.

    ``member_refs`` may legitimately reference ISR genes (modules, services,
    capabilities) — those are semantic references, not realizations. The lint
    rejects realization TECHNOLOGY terms, not references to ISR genes.
    """
    hits = boundary_mechanism_hits(boundary)
    if hits:
        raise BoundaryValidationError(
            f"boundary '{boundary.boundary_id}' couples to realization(s): {hits}"
        )


# -- structural validation (pre-execution) -----------------------------------

def _gene_ids(system: Any) -> set[str]:
    """ISR gene identities a boundary may reference.

    Modules, services, workflows, interfaces, policies, entities (the
    dependency-graph nodes), and business capabilities — the R2.9.7
    ArchitecturalSkeleton identity space generalized. References are always
    declared identities — never inferred structure.
    """
    ids: set[str] = set()
    for module in system.modules:
        ids.add(module.id)
        ids.update(service.id for service in module.services)
        ids.update(workflow.id for workflow in module.workflows)
        ids.update(interface.id for interface in module.interfaces)
        ids.update(policy.id for policy in module.policies)
        ids.update(entity.id for entity in module.entities)
    ids.update(capability.capability_id for capability in system.business_capabilities)
    return ids


def validate_system_boundary_constraints(system: Any) -> tuple[str, ...]:
    """Structural validation for one system's architectural boundaries.

    Rejects, pre-execution: duplicate boundary ids, dangling member refs,
    dangling forbidden-dependency refs. Construction already rejects
    member-also-forbidden overlap and empty members. Empty tuple means valid.
    """
    errors: list[str] = []
    gene_ids = _gene_ids(system)
    seen: set[str] = set()
    for boundary in system.architectural_boundaries:
        if boundary.boundary_id in seen:
            errors.append(
                f"duplicate architectural boundary id '{boundary.boundary_id}'"
            )
        seen.add(boundary.boundary_id)
        for member_ref in boundary.member_refs:
            if member_ref not in gene_ids:
                errors.append(
                    f"architectural boundary '{boundary.boundary_id}' encloses "
                    f"unknown gene '{member_ref}'"
                )
        for forbidden_ref in boundary.forbidden_dependency_refs:
            if forbidden_ref not in gene_ids:
                errors.append(
                    f"architectural boundary '{boundary.boundary_id}' forbids "
                    f"dependency on unknown gene '{forbidden_ref}'"
                )
    return tuple(errors)


# -- projection (semantics only) ---------------------------------------------

def project_architectural_boundaries(isr: Any) -> tuple[dict[str, Any], ...]:
    """Backend-independent semantic projection of architectural boundaries.

    Returns boundary semantics (enclosed members, forbidden dependencies,
    protected flag, crossing invariants). Never packages, containers,
    processes, network zones, or deployment units — those are
    compiler-backend realizations of the constraint declared here.
    """
    return tuple(
        canonical_form(boundary)
        for boundary in getattr(isr.system, "architectural_boundaries", ())
    )