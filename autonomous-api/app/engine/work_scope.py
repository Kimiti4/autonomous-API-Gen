"""Unified governed work scope for ESAP project and software-surface intent."""

from __future__ import annotations

from dataclasses import dataclass

from .generation_scope import GenerationScope, ScopeContract, validate_scope
from .project_scope import ProjectScope, validate_project_scope
from .scope_authorization import MutationIntent, authorize_mutations


@dataclass(frozen=True)
class WorkScope:
    """Complete declaration of what ESAP may do to a project."""

    project: ProjectScope
    generation: ScopeContract

    @classmethod
    def create(
        cls,
        project: ProjectScope,
        generation: GenerationScope,
    ) -> "WorkScope":
        return cls(
            project=validate_project_scope(project),
            generation=validate_scope(generation),
        )

    def authorize(self, mutations: tuple[MutationIntent, ...]) -> tuple[MutationIntent, ...]:
        return authorize_mutations(self.generation, mutations)


def validate_work_scope(scope: WorkScope) -> WorkScope:
    if not isinstance(scope, WorkScope):
        raise ValueError("invalid-work-scope")
    validate_project_scope(scope.project)
    validate_scope(scope.generation.scope)
    return scope
