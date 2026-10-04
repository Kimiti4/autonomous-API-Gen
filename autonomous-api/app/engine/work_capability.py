"""Authoritative Bucket 2 capability contract combining project, mode and surface."""

from __future__ import annotations

from dataclasses import dataclass

from .generation_scope import GenerationScope, ScopeContract, validate_scope
from .project_scope import ProjectScope, validate_project_scope
from .scope_authorization import MutationIntent, authorize_mutations
from .work_mode import WorkMode, WorkModeContract


@dataclass(frozen=True)
class WorkCapabilityContract:
    project: ProjectScope
    mode: WorkModeContract
    generation: ScopeContract

    @classmethod
    def create(cls, project: ProjectScope, mode: WorkMode, generation: GenerationScope) -> "WorkCapabilityContract":
        project = validate_project_scope(project)
        mode_contract = WorkModeContract.for_mode(mode)
        mode_contract.validate_project_kind(project.change_kind.value)
        return cls(project, mode_contract, validate_scope(generation))

    def authorize(self, mutations: tuple[MutationIntent, ...]) -> tuple[MutationIntent, ...]:
        return authorize_mutations(self.generation, mutations)

    def allows_surface(self, surface: str) -> bool:
        return self.generation.allows(surface)


def validate_work_capability(contract: WorkCapabilityContract) -> WorkCapabilityContract:
    if not isinstance(contract, WorkCapabilityContract):
        raise ValueError("invalid-work-capability")
    validate_project_scope(contract.project)
    contract.mode.validate_project_kind(contract.project.change_kind.value)
    validate_scope(contract.generation.scope)
    return contract
