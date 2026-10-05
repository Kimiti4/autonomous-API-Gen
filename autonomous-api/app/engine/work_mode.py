"""Governed ESAP work modes, including bounded existing-project surfaces."""

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
    FRONTEND_ONLY = "frontend_only"
    BACKEND_ONLY = "backend_only"
    API_CONTRACT_ONLY = "api_contract_only"


@dataclass(frozen=True)
class WorkModeContract:
    mode: WorkMode
    requires_existing_project: bool = False
    allowed_surfaces: tuple[str, ...] = ("frontend", "backend", "api_contract")

    @classmethod
    def for_mode(cls, mode: WorkMode) -> "WorkModeContract":
        if not isinstance(mode, WorkMode):
            raise ValueError("invalid-work-mode")
        existing = {
            WorkMode.MAINTAIN, WorkMode.IMPROVE, WorkMode.DOCUMENT, WorkMode.SEO,
            WorkMode.TEST, WorkMode.MIGRATE, WorkMode.REFACTOR,
            WorkMode.FRONTEND_ONLY, WorkMode.BACKEND_ONLY, WorkMode.API_CONTRACT_ONLY,
        }
        surfaces = {
            WorkMode.FRONTEND_ONLY: ("frontend",),
            WorkMode.BACKEND_ONLY: ("backend",),
            WorkMode.API_CONTRACT_ONLY: ("api_contract",),
        }
        return cls(
            mode=mode,
            requires_existing_project=mode in existing,
            allowed_surfaces=surfaces.get(mode, ("frontend", "backend", "api_contract")),
        )

    def validate_project_kind(self, project_kind: str) -> None:
        if project_kind not in {"new_project", "existing_project"}:
            raise ValueError("invalid-project-kind")
        if self.requires_existing_project and project_kind != "existing_project":
            raise ValueError(f"{self.mode.value}-requires-existing-project")

    def allows_surface(self, surface: str) -> bool:
        if surface not in {"frontend", "backend", "api_contract"}:
            raise ValueError(f"unknown-software-surface:{surface}")
        return surface in self.allowed_surfaces
