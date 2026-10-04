"""Broader governed ESAP work-mode contracts for Bucket 2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WorkMode(str, Enum):
    GENERATE = "generate"
    MAINTAIN = "maintain"
    IMPROVE = "improve"
    DOCUMENT = "document"
    SEO = "seo"
    TEST = "test"
    ARCHITECTURE = "architecture"
    MIGRATE = "migrate"
    REFACTOR = "refactor"
    CROSS_STACK = "cross_stack"


@dataclass(frozen=True)
class WorkModeContract:
    mode: WorkMode
    requires_existing_project: bool = False

    @classmethod
    def for_mode(cls, mode: WorkMode) -> "WorkModeContract":
        if not isinstance(mode, WorkMode):
            raise ValueError("invalid-work-mode")
        return cls(
            mode=mode,
            requires_existing_project=mode
            in {
                WorkMode.MAINTAIN,
                WorkMode.IMPROVE,
                WorkMode.DOCUMENT,
                WorkMode.SEO,
                WorkMode.TEST,
                WorkMode.MIGRATE,
                WorkMode.REFACTOR,
            },
        )

    def validate_project_kind(self, project_kind: str) -> None:
        if project_kind not in {"new_project", "existing_project"}:
            raise ValueError("invalid-project-kind")
        if self.requires_existing_project and project_kind != "existing_project":
            raise ValueError(f"{self.mode.value}-requires-existing-project")

    def allows_surface(self, surface: str) -> bool:
        if surface not in {"frontend", "backend", "api_contract"}:
            raise ValueError(f"unknown-software-surface:{surface}")
        if self.mode is WorkMode.FRONTEND_ONLY:
            return surface == "frontend"
        return True
