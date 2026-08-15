"""Capability-driven backend selection.

Selection matches declared capabilities against compilation requirements.
Backend identity plays no role in matching — it appears in the resulting
plan purely as provenance. Policy is data; failure is loud and diagnostic.

This layer is selection-only: it never invokes a backend (that is Phase 16's
job). It operates entirely over declarations.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from tiannara.domain.models.backend_declaration import (
    BackendCapabilityDeclaration,
    CompilationPlan,
    CompilationRequirement,
    PlannedCompilation,
    derive_plan_id,
)

from .registry import CompilerRegistry


class BackendSelectionError(ValueError):
    """No registered backend can satisfy a requirement.

    Selection never fabricates a backend and never silently relaxes a
    requirement. The error carries the closest near-miss for diagnosis.
    """

    def __init__(
        self,
        requirement: CompilationRequirement,
        declarations: list[BackendCapabilityDeclaration],
    ) -> None:
        self.requirement = requirement
        kind_matches = [
            d for d in declarations if requirement.artifact_kind in d.artifact_kinds
        ]
        if not kind_matches:
            detail = (
                f"no registered backend produces artifact kind "
                f"'{requirement.artifact_kind.value}'"
            )
        else:
            def coverage(declaration: BackendCapabilityDeclaration) -> int:
                return len(
                    [
                        c
                        for c in requirement.required_capabilities
                        if c in declaration.capabilities
                    ]
                )

            closest = sorted(
                kind_matches, key=lambda d: (-coverage(d), d.backend_id)
            )[0]
            missing = [
                c.value
                for c in requirement.required_capabilities
                if c not in closest.capabilities
            ]
            detail = (
                f"closest backend '{closest.backend_id}' lacks capabilities: "
                f"{missing}"
            )
        super().__init__(
            f"cannot satisfy compilation requirement "
            f"({requirement.artifact_kind.value}, required="
            f"{[c.value for c in requirement.required_capabilities]}): {detail}"
        )


class SelectionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = "default"
    min_quality_profile: float = Field(default=0.0, ge=0.0, le=1.0)


DEFAULT_SELECTION_POLICY = SelectionPolicy()


class BackendSelector:
    def __init__(self, registry: CompilerRegistry) -> None:
        self._registry = registry

    def rank(
        self,
        requirement: CompilationRequirement,
        policy: SelectionPolicy = DEFAULT_SELECTION_POLICY,
    ) -> list[BackendCapabilityDeclaration]:
        """All satisfying declarations, deterministic order:
        quality descending, then backend_id ascending."""
        matched = []
        for declaration in self._registry.declarations():
            if declaration.quality_profile < policy.min_quality_profile:
                continue
            satisfied, _missing = declaration.supports(
                requirement.artifact_kind, requirement.required_capabilities
            )
            if satisfied:
                matched.append(declaration)
        return sorted(
            matched, key=lambda d: (-d.quality_profile, d.backend_id)
        )

    def select(
        self,
        requirement: CompilationRequirement,
        policy: SelectionPolicy = DEFAULT_SELECTION_POLICY,
    ) -> BackendCapabilityDeclaration:
        ranked = self.rank(requirement, policy)
        if ranked:
            return ranked[0]
        raise BackendSelectionError(requirement, self._registry.declarations())


def plan_compilation(
    registry: CompilerRegistry,
    requirements: list[CompilationRequirement],
    policy: SelectionPolicy = DEFAULT_SELECTION_POLICY,
) -> CompilationPlan:
    """Deterministic plan: one selected backend per requirement."""
    selector = BackendSelector(registry)
    planned: list[PlannedCompilation] = []
    for requirement in requirements:
        declaration = selector.select(requirement, policy)
        planned.append(
            PlannedCompilation(
                requirement=requirement,
                backend_id=declaration.backend_id,
                declaration=declaration,
            )
        )
    return CompilationPlan(
        plan_id=derive_plan_id(requirements, policy.name),
        policy_name=policy.name,
        planned=planned,
    )


def plan_compilation_across_backends(
    registry: CompilerRegistry,
    requirements: list[CompilationRequirement],
    policy: SelectionPolicy = DEFAULT_SELECTION_POLICY,
) -> CompilationPlan:
    """Phase-31 calibration seam: one plan entry per (requirement, backend).

    Unlike ``plan_compilation`` (which selects the single best backend per
    requirement for production), this emits *every* satisfying backend for each
    requirement -- so "compile the same ISR to every backend" is expressible.
    The production selector is untouched; this is an additive, opt-in planner.
    """
    selector = BackendSelector(registry)
    planned: list[PlannedCompilation] = []
    for requirement in requirements:
        for declaration in selector.rank(requirement, policy):
            planned.append(
                PlannedCompilation(
                    requirement=requirement,
                    backend_id=declaration.backend_id,
                    declaration=declaration,
                )
            )
    return CompilationPlan(
        plan_id="cal-" + derive_plan_id(requirements, policy.name)[len("plan-"):],
        policy_name=policy.name,
        planned=planned,
    )
