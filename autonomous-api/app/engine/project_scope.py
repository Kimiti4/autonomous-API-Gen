"""Explicit project intent and lifecycle scope for ESAP."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProjectIntent(str, Enum):
    CREATE = "create"
    MAINTAIN = "maintain"
    IMPROVE = "improve"


class ChangeKind(str, Enum):
    NEW_PROJECT = "new_project"
    EXISTING_PROJECT = "existing_project"


@dataclass(frozen=True)
class ProjectScope:
    intent: ProjectIntent
    change_kind: ChangeKind

    @classmethod
    def create_new(cls) -> "ProjectScope":
        return cls(ProjectIntent.CREATE, ChangeKind.NEW_PROJECT)

    @classmethod
    def maintain_existing(cls) -> "ProjectScope":
        return cls(ProjectIntent.MAINTAIN, ChangeKind.EXISTING_PROJECT)

    @classmethod
    def improve_existing(cls) -> "ProjectScope":
        return cls(ProjectIntent.IMPROVE, ChangeKind.EXISTING_PROJECT)

    def validate(self) -> None:
        if self.intent is ProjectIntent.CREATE and self.change_kind is not ChangeKind.NEW_PROJECT:
            raise ValueError("create-requires-new-project")
        if self.intent in (ProjectIntent.MAINTAIN, ProjectIntent.IMPROVE) and self.change_kind is not ChangeKind.EXISTING_PROJECT:
            raise ValueError("existing-project-intent-requires-existing-project")


def validate_project_scope(scope: ProjectScope) -> ProjectScope:
    if not isinstance(scope, ProjectScope):
        raise ValueError("invalid-project-scope")
    scope.validate()
    return scope
