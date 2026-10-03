"""Architecture-diff and migration planning primitives."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ArchitectureChange:
    change_id: str
    artifact_type: str
    artifact_id: str
    action: str  # add, remove, modify, migrate
    rationale: str


@dataclass(frozen=True)
class MigrationStep:
    step_id: str
    change_id: str
    phase: str
    dependencies: tuple[str, ...] = ()
    rollback: str | None = None
    verification_obligations: tuple[str, ...] = ()


@dataclass(frozen=True)
class MigrationPlan:
    evolution_id: str
    parent_architecture_id: str
    target_architecture_id: str
    changes: tuple[ArchitectureChange, ...]
    steps: tuple[MigrationStep, ...]


def diff_artifacts(
    before: dict[str, Iterable[str]],
    after: dict[str, Iterable[str]],
) -> tuple[ArchitectureChange, ...]:
    changes: list[ArchitectureChange] = []
    for kind in sorted(set(before) | set(after)):
        old, new = set(before.get(kind, ())), set(after.get(kind, ()))
        for item in sorted(new - old):
            changes.append(ArchitectureChange(
                f"{kind}:add:{item}", kind, item, "add", "present in target only"))
        for item in sorted(old - new):
            changes.append(ArchitectureChange(
                f"{kind}:remove:{item}", kind, item, "remove", "present in parent only"))
    return tuple(changes)


def validate_migration(plan: MigrationPlan) -> tuple[str, ...]:
    errors = []
    change_ids = {c.change_id for c in plan.changes}
    step_ids = {s.step_id for s in plan.steps}

    if plan.parent_architecture_id == plan.target_architecture_id:
        errors.append("target-equals-parent")

    for step in plan.steps:
        if step.change_id not in change_ids:
            errors.append(f"step-references-unknown-change:{step.step_id}")
        for dep in step.dependencies:
            if dep not in step_ids:
                errors.append(f"unknown-step-dependency:{step.step_id}:{dep}")
        if step.phase in {"deploy", "cutover"} and not step.verification_obligations:
            errors.append(f"missing-verification:{step.step_id}")

    return tuple(errors)


def topological_steps(plan: MigrationPlan) -> tuple[str, ...]:
    remaining = {s.step_id: set(s.dependencies) for s in plan.steps}
    ordered: list[str] = []
    while remaining:
        ready = sorted(k for k, deps in remaining.items() if not deps)
        if not ready:
            raise ValueError("migration-dependency-cycle")
        for step_id in ready:
            ordered.append(step_id)
            del remaining[step_id]
            for deps in remaining.values():
                deps.discard(step_id)
    return tuple(ordered)
