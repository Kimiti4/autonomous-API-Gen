"""R2.10.4/R2.10.5 — IdentityIndex: the single identity namespace, as a DERIVED PROJECTION.

Every R2.10 semantic gene is addressed by (domain, gene_id) and resolved
through this index — never by raw projection paths. The rule (learned the
hard way in R2.10.3-J, where a path-vs-identity comparison silently
fail-opened the protection gate):

    identity is resolved through the index; paths are only a projection
    artifact. Never compare an identity to a path.

R2.10.5 invariant (LOCKED before implementation): the index is a PROJECTION,
not a source of truth. ``IdentityIndex`` is a frozen dataclass with no
mutation surface — no add_/remove_/replace_/set_ methods — and is
constructible only through ``derive(isr)``. The ISR is the source of truth;
the index is derived from it deterministically. Gene replacement is a
module-level function (``identity_index_replace_gene``) that produces a new
ISR version; it never mutates the index.

The index owns:

  * ``path_identities``   — projection path -> semantic identity id for the
    ten protected-identity domains (the R2.10.3-J walk, preserved exactly).
  * ``genes`` / ``gene_hashes`` — (domain, gene_id) -> gene object /
    canonical hash, using the same canonicalization as the ISR's content
    hash (``canonicalize``), so per-gene hashes compose with the
    whole-ISR identity.
  * ``resolvable_ids``    — the universe a cross-gene reference may point
    at (identity ids + module/entity/interface/event/transition/constraint
    ids).
  * ``dangling_references`` — every cross-gene reference that no longer
    resolves, per domain, as stable description strings.

This is the load-bearing mechanism of the SemanticEvolutionGate and the
UniversalEvolutionLoop: locality, reference integrity, and the J protection
diff all share the ONE namespace, so a change can never be judged in a
different namespace than it was authored in.
"""
from __future__ import annotations

import dataclasses
import hashlib
from dataclasses import dataclass
from typing import Any

from constitutional_architecture.isr.semantics.projection import canonicalize


# -- the identity domains ------------------------------------------------------

DOMAINS: tuple[str, ...] = (
    "capability",
    "requirement",
    "acceptance_criterion",
    "boundary",
    "testing_anchor",
    "reliability",
    "deployment",
    "documentation",
    "migration",
    "temporal",
    "behavior",
)

# system-level fields + their id attributes, per domain
_SYSTEM_FIELD: dict[str, str] = {
    "capability": "business_capabilities",
    "requirement": "requirements",
    "acceptance_criterion": "acceptance_criteria",
    "boundary": "architectural_boundaries",
    "testing_anchor": "testing_anchors",
    "reliability": "reliability_requirements",
    "deployment": "deployment_intents",
    "documentation": "documentation_intents",
}

_ID_ATTR: dict[str, str] = {
    "capability": "capability_id",
    "requirement": "requirement_id",
    "acceptance_criterion": "criterion_id",
    "boundary": "boundary_id",
    "testing_anchor": "anchor_id",
    "reliability": "requirement_id",
    "deployment": "deployment_id",
    "documentation": "documentation_id",
}


def _gene_hash(value: Any) -> str:
    """Hash one gene subtree with the SAME canonicalization as the ISR's
    content hash — per-gene hashes compose with whole-ISR identity."""
    return hashlib.sha256(canonicalize(value).encode("utf-8")).hexdigest()


def _path_identities(isr: Any) -> dict[str, str]:
    """Projection path -> semantic identity id for the ten protected
    identity domains (capabilities, requirements, acceptance criteria,
    boundaries, testing anchors, reliability requirements, deployment
    intents, migrations, temporal constraints, documentation intents,
    behaviors). Paths outside these domains stay unkeyed (the path
    itself is the subject)."""
    system = isr.system
    index: dict[str, str] = {}
    for ci, capability in enumerate(system.business_capabilities):
        index[f"system.business_capabilities[{ci}]"] = capability.capability_id
    for ri, requirement in enumerate(system.reliability_requirements):
        index[f"system.reliability_requirements[{ri}]"] = requirement.requirement_id
    for bi, boundary in enumerate(system.architectural_boundaries):
        index[f"system.architectural_boundaries[{bi}]"] = boundary.boundary_id
    for ri, requirement in enumerate(system.requirements):
        index[f"system.requirements[{ri}]"] = requirement.requirement_id
    for ci, criterion in enumerate(system.acceptance_criteria):
        index[f"system.acceptance_criteria[{ci}]"] = criterion.criterion_id
    for di, intent in enumerate(system.deployment_intents):
        index[f"system.deployment_intents[{di}]"] = intent.deployment_id
    for ai, anchor in enumerate(system.testing_anchors):
        index[f"system.testing_anchors[{ai}]"] = anchor.anchor_id
    for di, intent in enumerate(system.documentation_intents):
        index[f"system.documentation_intents[{di}]"] = intent.documentation_id
    for mi, module in enumerate(system.modules):
        base = f"system.modules[{mi}]"
        for wi, workflow in enumerate(module.workflows):
            wbase = f"{base}.workflows[{wi}]"
            index[wbase] = workflow.id
            for sti in range(len(workflow.states)):
                index[f"{wbase}.states[{sti}]"] = workflow.id
            for ti in range(len(workflow.transitions)):
                index[f"{wbase}.transitions[{ti}]"] = workflow.id
        for mi_i, migration in enumerate(module.data_migrations):
            index[f"{base}.data_migrations[{mi_i}]"] = migration.migration_id
        for tci, constraint in enumerate(module.temporal_constraints):
            index[f"{base}.temporal_constraints[{tci}]"] = constraint.constraint_id
    return index


def _genes(isr: Any) -> dict[tuple[str, str], Any]:
    """Every first-class semantic gene, keyed by (domain, gene_id)."""
    system = isr.system
    genes: dict[tuple[str, str], Any] = {}
    for capability in system.business_capabilities:
        genes[("capability", capability.capability_id)] = capability
    for requirement in system.requirements:
        genes[("requirement", requirement.requirement_id)] = requirement
    for criterion in system.acceptance_criteria:
        genes[("acceptance_criterion", criterion.criterion_id)] = criterion
    for boundary in system.architectural_boundaries:
        genes[("boundary", boundary.boundary_id)] = boundary
    for anchor in system.testing_anchors:
        genes[("testing_anchor", anchor.anchor_id)] = anchor
    for requirement in system.reliability_requirements:
        genes[("reliability", requirement.requirement_id)] = requirement
    for intent in system.deployment_intents:
        genes[("deployment", intent.deployment_id)] = intent
    for intent in system.documentation_intents:
        genes[("documentation", intent.documentation_id)] = intent
    for module in system.modules:
        for workflow in module.workflows:
            genes[("behavior", workflow.id)] = workflow
        for migration in module.data_migrations:
            genes[("migration", migration.migration_id)] = migration
        for constraint in module.temporal_constraints:
            genes[("temporal", constraint.constraint_id)] = constraint
    return genes


def _resolvable_ids(isr: Any) -> frozenset[str]:
    """Everything a cross-gene reference may point at: identity ids plus
    the structural ids (modules, entities, interfaces, events,
    transitions, constraints)."""
    system = isr.system
    ids = {gene_id for (_, gene_id) in _genes(isr)}
    ids.update(module.id for module in system.modules)
    for module in system.modules:
        ids.update(entity.id for entity in module.entities)
        ids.update(interface.id for interface in module.interfaces)
        ids.update(event.id for event in module.events)
        for workflow in module.workflows:
            ids.update(transition.id for transition in workflow.transitions)
    ids.update(constraint.id for constraint in system.constraints)
    for module in system.modules:
        for entity in module.entities:
            ids.update(constraint.id for constraint in entity.constraints)
    return frozenset(ids)


def _dangling_references(isr: Any) -> tuple[str, ...]:
    """Every cross-gene reference that does not resolve, as stable
    description strings (deterministic order). Empty tuple = intact."""
    system = isr.system
    identities = {gene_id for (_, gene_id) in _genes(isr)}
    behavior_ids = {
        workflow.id for module in system.modules for workflow in module.workflows
    }
    interface_ids = {
        interface.id for module in system.modules for interface in module.interfaces
    }
    constraint_ids = {constraint.id for constraint in system.constraints}
    for module in system.modules:
        for entity in module.entities:
            constraint_ids.update(
                constraint.id for constraint in entity.constraints
            )
    requirement_ids = {r.requirement_id for r in system.requirements}
    criterion_ids = {c.criterion_id for c in system.acceptance_criteria}
    module_ids = {module.id for module in system.modules}
    entity_ids = {
        entity.id for module in system.modules for entity in module.entities
    }
    transition_ids = {
        transition.id
        for module in system.modules
        for workflow in module.workflows
        for transition in workflow.transitions
    }
    event_ids = {
        event.id for module in system.modules for event in module.events
    }
    migration_ids = {
        migration.migration_id
        for module in system.modules
        for migration in module.data_migrations
    }

    dangles: list[str] = []

    def check(owner: str, field: str, refs: Any, universe: frozenset[str]) -> None:
        for ref in refs:
            if ref not in universe:
                dangles.append(f"{owner} {field} '{ref}'")

    for capability in system.business_capabilities:
        owner = f"capability '{capability.capability_id}'"
        check(owner, "behavior_ref", capability.behavior_refs, frozenset(behavior_ids))
        check(owner, "interface_ref", capability.interface_refs, frozenset(interface_ids))
        check(owner, "constraint_ref", capability.constraint_refs, frozenset(constraint_ids))
        check(owner, "requirement_ref", capability.requirement_refs, frozenset(requirement_ids))
    for requirement in system.requirements:
        owner = f"requirement '{requirement.requirement_id}'"
        check(owner, "target_ref", requirement.target_refs, identities)
        check(owner, "acceptance_ref", requirement.acceptance_refs, frozenset(criterion_ids))
        check(
            owner, "constraint_ref", requirement.constraint_refs,
            frozenset(constraint_ids | behavior_ids),
        )
    for criterion in system.acceptance_criteria:
        check(
            f"acceptance_criterion '{criterion.criterion_id}'",
            "subject_ref", criterion.subject_refs, identities,
        )
    for requirement in system.reliability_requirements:
        check(
            f"reliability '{requirement.requirement_id}'",
            "target_ref", requirement.target_refs, identities,
        )
    for intent in system.deployment_intents:
        owner = f"deployment '{intent.deployment_id}'"
        check(owner, "target_ref", intent.target_refs, identities)
        rollback = getattr(intent, "rollback_target_ref", None)
        if rollback and rollback not in identities:
            dangles.append(f"{owner} rollback_target_ref '{rollback}'")
    for boundary in system.architectural_boundaries:
        owner = f"boundary '{boundary.boundary_id}'"
        check(owner, "member_ref", boundary.member_refs, frozenset(module_ids))
        check(
            owner, "forbidden_dependency_ref",
            boundary.forbidden_dependency_refs, frozenset(module_ids),
        )
    for anchor in system.testing_anchors:
        owner = f"testing_anchor '{anchor.anchor_id}'"
        check(owner, "subject_ref", anchor.subject_refs, identities)
        check(owner, "obligation_ref", anchor.obligation_refs, frozenset(criterion_ids))
    for intent in system.documentation_intents:
        check(
            f"documentation '{intent.documentation_id}'",
            "subject_ref", intent.subject_refs, identities,
        )
    for module in system.modules:
        for migration in module.data_migrations:
            owner = f"migration '{migration.migration_id}'"
            if migration.source_schema_ref not in entity_ids:
                dangles.append(
                    f"{owner} source_schema_ref '{migration.source_schema_ref}'"
                )
            if migration.target_schema_ref not in entity_ids:
                dangles.append(
                    f"{owner} target_schema_ref '{migration.target_schema_ref}'"
                )
            check(owner, "preservation_ref", migration.preservation_refs, frozenset(entity_ids))
            rollback = getattr(migration, "rollback_target_ref", None)
            if rollback and rollback not in entity_ids:
                dangles.append(f"{owner} rollback_target_ref '{rollback}'")
            check(owner, "depends_on", migration.depends_on, frozenset(migration_ids))
        for constraint in module.temporal_constraints:
            owner = f"temporal '{constraint.constraint_id}'"
            if (
                constraint.target_ref not in transition_ids
                and constraint.target_ref not in behavior_ids
            ):
                dangles.append(f"{owner} target_ref '{constraint.target_ref}'")
            reference_ref = getattr(constraint, "reference_ref", None)
            if reference_ref and reference_ref not in event_ids:
                dangles.append(f"{owner} reference_ref '{reference_ref}'")
    return tuple(dangles)


@dataclass(frozen=True)
class IdentityIndex:
    """The single identity namespace, as a DERIVED PROJECTION of one ISR.

    R2.10.5 invariant (locked): the index is a frozen dataclass with no
    mutation surface (no add_/remove_/replace_/set_ methods) and is
    constructed only through ``derive(isr)`` — the ISR is the source of
    truth, the index is derived from it deterministically. Gene
    replacement lives OUTSIDE the class (``identity_index_replace_gene``)
    and produces a new ISR version; it never mutates the index.
    """

    path_identities: dict[str, str]
    genes: dict[tuple[str, str], Any]
    gene_hashes: dict[tuple[str, str], str]
    resolvable_ids: frozenset[str]
    dangling_references: tuple[str, ...]

    @classmethod
    def derive(cls, isr: Any) -> "IdentityIndex":
        """Derive the index from one ISR, deterministically."""
        genes = _genes(isr)
        return cls(
            path_identities=_path_identities(isr),
            genes=genes,
            gene_hashes={key: _gene_hash(gene) for key, gene in genes.items()},
            resolvable_ids=_resolvable_ids(isr),
            dangling_references=_dangling_references(isr),
        )

    # -- read-only lookups (no mutation surface) -------------------------------

    def identity_for_path(self, path: str) -> str:
        return self.path_identities.get(path) or path

    def gene_hash(self, domain: str, gene_id: str) -> str:
        try:
            return self.gene_hashes[(domain, gene_id)]
        except KeyError as exc:
            raise KeyError(
                f"no '{domain}' gene '{gene_id}' in the identity index"
            ) from exc

    def genes_by_domain(self) -> dict[str, tuple[tuple[str, Any], ...]]:
        """(domain -> ((gene_id, gene), ...)) grouping, deterministic."""
        grouped: dict[str, list[tuple[str, Any]]] = {}
        for (domain, gene_id), gene in self.genes.items():
            grouped.setdefault(domain, []).append((gene_id, gene))
        return {
            domain: tuple(items)
            for domain, items in sorted(grouped.items())
        }


# -- deterministic single-gene replacement (module-level, never on the class) --

def identity_index_replace_gene(
    index: IdentityIndex, isr: Any, domain: str, gene_id: str, new_gene: Any
):
    """Return a new ISR version with exactly one gene replaced.

    Replacement is mechanical (no validation sweep): the evolution gates
    evaluate the candidate and its proofs; structural validation stays a
    separate pre-execution concern. The gene must be a member of the
    index's identity namespace — unknown genes raise KeyError (rejection
    before evaluation), never silently ignored. The index itself is never
    mutated: this is the module-level seam the R2.10.5 invariant demands.
    """
    if (domain, gene_id) not in index.genes:
        raise KeyError(f"no '{domain}' gene '{gene_id}' in the identity index")
    system = isr.system
    if domain in ("behavior", "migration", "temporal"):
        for mi, module in enumerate(system.modules):
            new_module = _replace_in_module(
                module, domain, gene_id, new_gene
            )
            if new_module is not None:
                return isr.with_system(
                    dataclasses.replace(
                        system,
                        modules=(
                            system.modules[:mi]
                            + (new_module,)
                            + system.modules[mi + 1:]
                        ),
                    )
                )
        raise KeyError(f"no '{domain}' gene '{gene_id}' in the ISR")
    field = _SYSTEM_FIELD[domain]
    id_attr = _ID_ATTR[domain]
    items = getattr(system, field)
    for i, item in enumerate(items):
        if getattr(item, id_attr) == gene_id:
            return isr.with_system(
                dataclasses.replace(
                    system,
                    **{field: items[:i] + (new_gene,) + items[i + 1:]},
                )
            )
    raise KeyError(f"no '{domain}' gene '{gene_id}' in the ISR")


def _replace_in_module(
    module: Any, domain: str, gene_id: str, new_gene: Any
) -> Any:
    if domain == "behavior":
        for wi, workflow in enumerate(module.workflows):
            if workflow.id == gene_id:
                return dataclasses.replace(
                    module,
                    workflows=(
                        module.workflows[:wi]
                        + (new_gene,)
                        + module.workflows[wi + 1:]
                    ),
                )
    elif domain == "migration":
        for mi_i, migration in enumerate(module.data_migrations):
            if migration.migration_id == gene_id:
                return dataclasses.replace(
                    module,
                    data_migrations=(
                        module.data_migrations[:mi_i]
                        + (new_gene,)
                        + module.data_migrations[mi_i + 1:]
                    ),
                )
    elif domain == "temporal":
        for tci, constraint in enumerate(module.temporal_constraints):
            if constraint.constraint_id == gene_id:
                return dataclasses.replace(
                    module,
                    temporal_constraints=(
                        module.temporal_constraints[:tci]
                        + (new_gene,)
                        + module.temporal_constraints[tci + 1:]
                    ),
                )
    return None