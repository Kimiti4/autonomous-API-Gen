"""R2.10.3-J — EvolutionProtectionEvaluator: the constitutional feasibility gate.

The crucial constitutional boundary: protected-region constraints are a
FEASIBILITY GATE that removes violating candidates from the feasible search
space BEFORE objective evaluation — never a fitness penalty, which a
sufficiently large competing fitness could overwhelm.

Formally, the J invariant:

    for all candidates C:
        violates_protected_region(C)  =>  C not in FeasibleCandidates

regardless of fitness(C), objective_score(C), novelty(C), performance(C), or
selection_probability(C). No objective may override a protected region, and
constitutional objectives are feasibility gates themselves (their subjects
must remain present in any feasible candidate).

The evaluator operates ONLY on an explicit semantic diff (EvolutionDiff)
derived from the ISR's gene index — never on implementation structure — so
it cannot become a hidden implementation-specific analyzer. ProtectionResult
is a PROJECTION output: affected_subjects is computed by the projection, not
owned by J; the ISR stays authoritative for semantic identity, which keeps J
transferable when the underlying representation evolves beyond FSMs.

CONSTITUTIONAL authorizations are governance-owned
(constitutional_architecture.governance). The evaluator RECEIVES one as an
opaque validated value (never imports or constructs it — module-boundary
test) and verifies its anchor against the governance authority. Without a
governance-issued authorization, no CONSTITUTIONAL change can ever be
authorized: ordinary evolution cannot satisfy a constitutional
authorization, because the process being constrained does not control the
constraint.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from constitutional_architecture.isr.semantics.evolution_policy import (
    ObjectiveTier,
    ProtectionKind,
)
from constitutional_architecture.isr.semantics.requirement import ObligationKind

from .isr_capability_audit import gene_index


@dataclass(frozen=True)
class EvolutionDiff:
    """Explicit semantic diff between parent and candidate.

    Subjects are semantic IDENTITY ids (capability ids, workflow ids,
    boundary ids, anchor ids, ... — the ten protected-identity domains),
    resolved from the gene index so region ``subject_refs`` intersect the
    diff directly. A gene path that belongs to no protected identity stays
    as its path. The preservation evaluator operates ONLY on this — never
    on implementation structure — so it cannot become a hidden
    implementation-specific analyzer.
    """

    added_subjects: frozenset[str]
    removed_subjects: frozenset[str]
    changed_subjects: frozenset[str]
    ordering_changes: tuple[str, ...] = ()

    @property
    def affected_subjects(self) -> frozenset[str]:
        return self.added_subjects | self.removed_subjects | self.changed_subjects


@dataclass(frozen=True)
class ProtectionResult:
    """The protection projection's result.

    ``affected_subjects`` is a PROJECTION OUTPUT, not a J-owned semantic
    primitive — the ISR stays authoritative for identity, which keeps J
    transferable beyond the FSM substrate.
    """

    protected_ok: bool
    kind: Optional[ProtectionKind] = None
    affected_subjects: tuple[str, ...] = ()
    authorized_by: Optional[str] = None
    notes: tuple[str, ...] = ()


class EvolutionProtectionEvaluator:
    """Semantic projection consumed by the R2.8 gate stack.

    Feasibility gate, never a fitness penalty: a violating candidate is
    removed from the feasible search space before objective evaluation.
    """

    def __init__(self, authority: Any = None) -> None:
        self._authority = authority

    # -- the gate ---------------------------------------------------------------

    def evaluate(
        self,
        parent: Any,
        candidate: Any,
        policy: Any,
        authorization: Any = None,
    ) -> ProtectionResult:
        diff = self._semantic_diff(parent, candidate)
        # Regions and objectives resolve from the PARENT constitution: the
        # gate judges the candidate against the current declaration, never
        # against a declaration the candidate itself could have weakened.
        for region_ref in policy.protected_region_refs:
            region = self._resolve_region(parent, region_ref)
            if region is None:
                continue
            affected = frozenset(region.subject_refs) & diff.affected_subjects
            if not affected:
                continue
            if region.protection_kind is ProtectionKind.IMMUTABLE:
                return ProtectionResult(
                    False,
                    ProtectionKind.IMMUTABLE,
                    tuple(sorted(affected)),
                    notes=(f"region '{region_ref}' is IMMUTABLE",),
                )
            if region.protection_kind is ProtectionKind.CONSTITUTIONAL:
                if not self._valid_authorization(authorization, region_ref, affected):
                    return ProtectionResult(
                        False,
                        ProtectionKind.CONSTITUTIONAL,
                        tuple(sorted(affected)),
                        notes=(f"region '{region_ref}' is CONSTITUTIONAL: "
                               "external governance authorization required",),
                    )
                # externally authorized -> this region is satisfied
            elif region.protection_kind is ProtectionKind.PRESERVATION:
                violated = tuple(
                    inv.statement
                    for inv in region.invariants
                    if not self._invariant_holds(inv, diff)
                )
                if violated:
                    return ProtectionResult(
                        False,
                        ProtectionKind.PRESERVATION,
                        tuple(sorted(affected)),
                        notes=violated,
                    )
        # Constitutional objectives are feasibility gates: their subjects must
        # remain present in any feasible candidate (the never-sacrifice
        # guarantee closed at the objective level).
        for objective_ref in policy.objective_refs:
            objective = self._resolve_objective(parent, objective_ref)
            if objective is None or objective.tier is not ObjectiveTier.CONSTITUTIONAL:
                continue
            removed = frozenset(objective.subject_refs) & diff.removed_subjects
            if removed:
                return ProtectionResult(
                    False,
                    None,
                    tuple(sorted(removed)),
                    notes=(
                        f"constitutional objective '{objective_ref}' subjects "
                        f"removed: {sorted(removed)} — presence gate",
                    ),
                )
        return ProtectionResult(True, None, ())

    # -- semantic diff (gene-index based, representation-agnostic) ---------------

    def _identity_index(self, isr: Any) -> dict[str, str]:
        """gene path -> semantic identity id for the ten protected-identity
        domains (capabilities, requirements, acceptance criteria, boundaries,
        testing anchors, reliability requirements, deployment intents,
        migrations, temporal constraints, documentation intents, behaviors).
        Paths outside these domains stay unkeyed (the path itself is the
        subject)."""
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

    def _semantic_diff(self, parent: Any, candidate: Any) -> EvolutionDiff:
        before = gene_index(parent)
        after = gene_index(candidate)
        parent_identities = self._identity_index(parent)
        candidate_identities = self._identity_index(candidate)
        added = frozenset(path for path in after if path not in before)
        removed = frozenset(path for path in before if path not in after)
        changed = frozenset(
            path for path in before
            if path in after and before[path] != after[path]
        )
        ordering = tuple(
            sorted(
                path for path in changed
                if ".transitions[" in path
            )
        )

        def resolve(paths: frozenset[str]) -> frozenset[str]:
            subjects = set()
            for path in paths:
                subjects.add(
                    parent_identities.get(path)
                    or candidate_identities.get(path)
                    or path
                )
            return frozenset(subjects)

        def resolve_one(path: str) -> str:
            return (
                parent_identities.get(path)
                or candidate_identities.get(path)
                or path
            )

        return EvolutionDiff(
            added_subjects=resolve(added),
            removed_subjects=resolve(removed),
            changed_subjects=resolve(changed),
            ordering_changes=tuple(resolve_one(path) for path in ordering),
        )

    # -- resolution ----------------------------------------------------------------

    def _resolve_region(self, isr: Any, region_ref: str) -> Any:
        for region in isr.system.protected_regions:
            if region.region_id == region_ref:
                return region
        return None

    def _resolve_objective(self, isr: Any, objective_ref: str) -> Any:
        for objective in isr.system.evolution_objectives:
            if objective.objective_id == objective_ref:
                return objective
        return None

    # -- authorization verification -------------------------------------------------

    def _valid_authorization(
        self, authorization: Any, region_ref: str, affected: frozenset[str]
    ) -> bool:
        if authorization is None:
            return False
        # The authorization is opaque to the evolution package: it must cover
        # the affected subjects AND its anchor must verify against the
        # governance authority. Ordinary evolution can neither create nor
        # forge one (module-boundary test).
        try:
            if not authorization.covers(region_ref, affected):
                return False
            return self._anchor_verifies(authorization.anchor_ref)
        except AttributeError:
            return False

    def _anchor_verifies(self, anchor_ref: str) -> bool:
        if self._authority is None:
            return False  # no governance authority -> nothing can be authorized
        try:
            return bool(self._authority.verifies(anchor_ref))
        except AttributeError:
            return False

    # -- preservation predicates (one predicate model, shared with F) --------------

    def _invariant_holds(self, invariant: Any, diff: EvolutionDiff) -> bool:
        subjects = frozenset(invariant.subject_refs)
        kind = invariant.kind
        if kind is ObligationKind.PRESENCE:
            return not (subjects & diff.removed_subjects)  # subjects remain
        if kind is ObligationKind.ABSENCE:
            return not (subjects & diff.added_subjects)  # never appears
        if kind is ObligationKind.INVARIANT:
            return not (subjects & diff.changed_subjects)  # content unchanged
        if kind is ObligationKind.ORDERING:
            return not (subjects & set(diff.ordering_changes))  # ordering preserved
        if kind is ObligationKind.THRESHOLD:
            return self._threshold_holds(invariant, diff)
        return False

    def _threshold_holds(self, invariant: Any, diff: EvolutionDiff) -> bool:
        """Structural threshold on the diff: how many of the invariant's
        subjects changed, against the declared bound. Richer threshold
        evaluation against measured values belongs to the evaluation system
        (the ISR declares what evidence must establish; evaluation determines
        it) — noted as the integration point, not reached into here."""
        bound = invariant.bound
        if bound is None:
            return False
        subjects = frozenset(invariant.subject_refs)
        changed_count = len(subjects & diff.changed_subjects)
        return float(changed_count) <= float(bound)