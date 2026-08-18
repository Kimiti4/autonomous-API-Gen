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

from .identity_index import IdentityIndex
from .isr_capability_audit import gene_index

# R2.10.5: the self-governance reference — J-carrier changes (evolution
# objectives / protected regions / evolution policies) are authorized only
# through this governance seam, exactly like CONSTITUTIONAL regions.
SELF_GOVERNANCE_REF = "self_governance"

_J_CARRIER_PREFIXES = (
    "system.evolution_objectives[",
    "system.protected_regions[",
    "system.evolution_policies[",
)


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
    transferable beyond the FSM substrate. ``regions_evaluated`` records
    every policy region the candidate actually put in play (R2.10.4: the
    multi-region evidence — each triggered region is judged, none
    short-circuits another).
    """

    protected_ok: bool
    kind: Optional[ProtectionKind] = None
    affected_subjects: tuple[str, ...] = ()
    authorized_by: Optional[str] = None
    notes: tuple[str, ...] = ()
    regions_evaluated: tuple[str, ...] = ()


_STRICTNESS = {
    ProtectionKind.IMMUTABLE: 3,
    ProtectionKind.CONSTITUTIONAL: 2,
    ProtectionKind.PRESERVATION: 1,
}


class EvolutionProtectionEvaluator:
    """Semantic projection consumed by the R2.8 gate stack.

    Feasibility gate, never a fitness penalty: a violating candidate is
    removed from the feasible search space before objective evaluation.
    """

    def __init__(
        self,
        authority: Any = None,
        identity_index: Any = None,
    ) -> None:
        self._authority = authority
        self._identity_index = identity_index or IdentityIndex

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
        # Every region the candidate puts in play is judged independently
        # (R2.10.4 multi-region semantics): violations accumulate, the
        # strictest kind wins, and every triggered region is evidenced in
        # ``regions_evaluated`` — no region short-circuits another.
        region_violations: list[tuple[ProtectionKind, frozenset[str], tuple[str, ...]]] = []
        regions_evaluated: list[str] = []
        for region_ref in policy.protected_region_refs:
            region = self._resolve_region(parent, region_ref)
            if region is None:
                continue
            affected = frozenset(region.subject_refs) & diff.affected_subjects
            if not affected:
                continue
            regions_evaluated.append(region_ref)
            if region.protection_kind is ProtectionKind.IMMUTABLE:
                region_violations.append(
                    (
                        ProtectionKind.IMMUTABLE,
                        affected,
                        (f"region '{region_ref}' is IMMUTABLE",),
                    )
                )
            elif region.protection_kind is ProtectionKind.CONSTITUTIONAL:
                if not self._valid_authorization(authorization, region_ref, affected):
                    region_violations.append(
                        (
                            ProtectionKind.CONSTITUTIONAL,
                            affected,
                            (
                                f"region '{region_ref}' is CONSTITUTIONAL: "
                                "external governance authorization required",
                            ),
                        )
                    )
                # externally authorized -> this region is satisfied
            elif region.protection_kind is ProtectionKind.PRESERVATION:
                violated = tuple(
                    inv.statement
                    for inv in region.invariants
                    if not self._invariant_holds(inv, diff)
                )
                if violated:
                    region_violations.append(
                        (ProtectionKind.PRESERVATION, affected, violated)
                    )
        # Constitutional objectives are feasibility gates: their subjects must
        # remain present in any feasible candidate (the never-sacrifice
        # guarantee closed at the objective level).
        objective_removed: list[tuple[frozenset[str], tuple[str, ...]]] = []
        for objective_ref in policy.objective_refs:
            objective = self._resolve_objective(parent, objective_ref)
            if objective is None or objective.tier is not ObjectiveTier.CONSTITUTIONAL:
                continue
            removed = frozenset(objective.subject_refs) & diff.removed_subjects
            if removed:
                objective_removed.append(
                    (
                        removed,
                        (
                            f"constitutional objective '{objective_ref}' subjects "
                            f"removed: {sorted(removed)} — presence gate",
                        ),
                    )
                )
        # R2.10.5 self-governance (accumulated, CONSTITUTIONAL kind): a
        # candidate that weakens its OWN evolution-policy carriers
        # (objectives / regions / policies) is eroding the very gate it is
        # judged under. The parent's regions already judge it; this closes
        # the gap when the delta touches no protected gene. Only actual
        # WEAKENING is flagged (carrier removals, subject-ref reductions,
        # protection downgrades) — content-only differences that do not
        # reduce the governance surface (e.g. an invariant bound) are not
        # weakening. Governance-issued authorization (SELF_GOVERNANCE_REF)
        # permits an authorized constitutional change — the one legitimate
        # carrier mutation.
        carrier_paths = frozenset(
            path
            for path in diff.affected_subjects
            if path.startswith(_J_CARRIER_PREFIXES)
        )
        if carrier_paths:
            weakened = self._self_governance_weakened(parent, candidate)
            if weakened:
                regions_evaluated.append(SELF_GOVERNANCE_REF)
                if not self._valid_authorization(
                    authorization, SELF_GOVERNANCE_REF, carrier_paths
                ):
                    region_violations.append(
                        (
                            ProtectionKind.CONSTITUTIONAL,
                            carrier_paths,
                            (
                                "self-governance: "
                                + "; ".join(weakened)
                                + " — governance authorization required",
                            ),
                        )
                    )
        evaluated = tuple(sorted(regions_evaluated))
        if region_violations:
            strictest = max(
                region_violations, key=lambda v: _STRICTNESS[v[0]]
            )
            affected = frozenset().union(
                *(affected for _, affected, _ in region_violations)
            )
            notes = tuple(
                note
                for _, _, region_notes in region_violations
                for note in region_notes
            )
            return ProtectionResult(
                False,
                strictest[0],
                tuple(sorted(affected)),
                notes=notes,
                regions_evaluated=evaluated,
            )
        if objective_removed:
            removed = frozenset().union(
                *(removed for removed, _ in objective_removed)
            )
            notes = tuple(
                note
                for _, region_notes in objective_removed
                for note in region_notes
            )
            return ProtectionResult(
                False,
                None,
                tuple(sorted(removed)),
                notes=notes,
                regions_evaluated=evaluated,
            )
        return ProtectionResult(True, None, (), regions_evaluated=evaluated)

    # -- semantic diff (gene-index based, representation-agnostic) ---------------

    # The shared IdentityIndex (R2.10.4, derived projection R2.10.5) is the
    # ONE identity namespace: path -> semantic identity id for the ten
    # protected-identity domains. Paths outside these domains stay unkeyed
    # (the path itself is the subject). Each ISR derives its own projection;
    # the namespace is shared by construction, never by instance.

    def _semantic_diff(self, parent: Any, candidate: Any) -> EvolutionDiff:
        before = gene_index(parent)
        after = gene_index(candidate)
        parent_identities = self._identity_index.derive(parent).path_identities
        candidate_identities = self._identity_index.derive(candidate).path_identities
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

    # -- R2.10.5 self-governance (the candidate's own declaration) ---------------

    def _self_governance_weakened(self, parent: Any, candidate: Any) -> tuple[str, ...]:
        """Does the candidate's evolution-policy declaration weaken the
        PARENT's? Carrier removals, subject-ref reductions, and protection
        downgrades are weakening; content-only differences that do not
        reduce the governance surface (e.g. an invariant bound, a priority,
        a weight) are not — the parent's declaration governs the judgment
        regardless, so only the candidate's future-governance surface
        matters. Empty tuple = declaration intact (or strictly stronger).
        """
        system = parent.system
        candidate_system = candidate.system
        problems: list[str] = []

        parent_regions = {r.region_id: r for r in system.protected_regions}
        candidate_regions = {r.region_id: r for r in candidate_system.protected_regions}
        for region_id, region in parent_regions.items():
            candidate_region = candidate_regions.get(region_id)
            if candidate_region is None:
                problems.append(f"protected region '{region_id}' removed")
                continue
            if not set(region.subject_refs) <= set(candidate_region.subject_refs):
                problems.append(
                    f"protected region '{region_id}' subject_refs reduced"
                )
            if _STRICTNESS[candidate_region.protection_kind] < _STRICTNESS[region.protection_kind]:
                problems.append(
                    f"protected region '{region_id}' protection downgraded "
                    f"({region.protection_kind.value} -> "
                    f"{candidate_region.protection_kind.value})"
                )

        parent_objectives = {o.objective_id: o for o in system.evolution_objectives}
        candidate_objectives = {
            o.objective_id: o for o in candidate_system.evolution_objectives
        }
        for objective_id, objective in parent_objectives.items():
            candidate_objective = candidate_objectives.get(objective_id)
            if candidate_objective is None:
                problems.append(f"evolution objective '{objective_id}' removed")
                continue
            if (
                objective.tier is ObjectiveTier.CONSTITUTIONAL
                and candidate_objective.tier is not ObjectiveTier.CONSTITUTIONAL
            ):
                problems.append(
                    f"constitutional objective '{objective_id}' downgraded "
                    "to OPTIMIZATION"
                )
            if not set(objective.subject_refs) <= set(candidate_objective.subject_refs):
                problems.append(
                    f"evolution objective '{objective_id}' subject_refs reduced"
                )

        parent_policies = {p.policy_id: p for p in system.evolution_policies}
        candidate_policies = {
            p.policy_id: p for p in candidate_system.evolution_policies
        }
        for policy_id, policy in parent_policies.items():
            candidate_policy = candidate_policies.get(policy_id)
            if candidate_policy is None:
                problems.append(f"evolution policy '{policy_id}' removed")
                continue
            if not set(policy.objective_refs) <= set(candidate_policy.objective_refs):
                problems.append(
                    f"evolution policy '{policy_id}' objective_refs reduced"
                )
            if not set(policy.protected_region_refs) <= set(
                candidate_policy.protected_region_refs
            ):
                problems.append(
                    f"evolution policy '{policy_id}' protected_region_refs reduced"
                )
        return tuple(problems)

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