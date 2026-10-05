"""Unified ESAP work-intent routing for Bucket 2 capability scopes.

Routes create/maintain/improve requests through explicit project and generation
contracts. This is planning/authorization metadata only; execution remains
behind the governed transaction pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .generation_scope import GenerationScope, ScopeContract, validate_scope
from .project_scope import ProjectIntent, ProjectScope, validate_project_scope


class WorkMode(str, Enum):
    CREATE = "create"
    MAINTAIN = "maintain"
    IMPROVE = "improve"


@dataclass(frozen=True)
class GovernedWorkRequest:
    project: ProjectScope
    generation: ScopeContract
    mode: WorkMode

    def validate(self) -> None:
        validate_project_scope(self.project)
        validate_scope(self.generation.scope)
        if self.mode.value != self.project.intent.value:
            raise ValueError("work-mode-project-intent-mismatch")


def route_work(
    *,
    mode: WorkMode,
    scope: GenerationScope,
    existing_project: bool,
) -> GovernedWorkRequest:
    if not isinstance(mode, WorkMode):
        raise ValueError("invalid-work-mode")

    if mode is WorkMode.CREATE:
        project = ProjectScope.create_new() if not existing_project else None
    elif mode is WorkMode.MAINTAIN:
        project = ProjectScope.maintain_existing() if existing_project else None
    else:
        project = ProjectScope.improve_existing() if existing_project else None

    if project is None:
        raise ValueError("work-mode-existing-project-mismatch")

    request = GovernedWorkRequest(project=project, generation=validate_scope(scope), mode=mode)
    request.validate()
    return request
