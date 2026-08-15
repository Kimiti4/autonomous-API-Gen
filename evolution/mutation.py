"""
Architecture mutation engine.

This engine mutates ISR payloads according to explicit mutation specifications.
"""

from __future__ import annotations

from typing import Any

from .errors import MutationError
from .models import MutationOperationType, MutationSpec
from .utils import deep_copy

from constitutional_architecture.governance.governance_design_fitness import (
    baseline_governance_design,
)


def _split_path(path: str) -> list[str]:
    return [segment for segment in str(path).split(".") if segment]


def _get_container(obj: Any, path: str) -> Any:
    if not path:
        return obj

    current = obj

    for segment in _split_path(path):
        if isinstance(current, dict):
            if segment not in current:
                raise MutationError(f"Path segment not found: {segment}")

            current = current[segment]

        elif isinstance(current, list):
            try:
                index = int(segment)
            except ValueError as exc:
                raise MutationError(
                    f"List index must be numeric: {segment}"
                ) from exc

            if index < 0 or index >= len(current):
                raise MutationError(
                    f"List index out of range: {segment}"
                )

            current = current[index]

        else:
            raise MutationError(
                f"Cannot traverse path segment {segment} on non-container."
            )

    return current


def _get_parent_and_key(obj: Any, path: str) -> tuple[Any, str]:
    segments = _split_path(path)

    if not segments:
        raise MutationError("Mutation path must not be empty.")

    parent = obj

    for segment in segments[:-1]:
        if isinstance(parent, dict):
            if segment not in parent:
                raise MutationError(f"Path segment not found: {segment}")

            parent = parent[segment]

        elif isinstance(parent, list):
            try:
                index = int(segment)
            except ValueError as exc:
                raise MutationError(
                    f"List index must be numeric: {segment}"
                ) from exc

            if index < 0 or index >= len(parent):
                raise MutationError(
                    f"List index out of range: {segment}"
                )

            parent = parent[index]

        else:
            raise MutationError(
                f"Cannot traverse path segment {segment} on non-container."
            )

    return parent, segments[-1]


def _set_value(obj: Any, path: str, value: Any) -> None:
    parent, key = _get_parent_and_key(obj, path)

    if isinstance(parent, dict):
        parent[key] = value
        return

    if isinstance(parent, list):
        try:
            index = int(key)
        except ValueError as exc:
            raise MutationError(
                f"List index must be numeric: {key}"
            ) from exc

        if index == len(parent):
            parent.append(value)
        elif 0 <= index < len(parent):
            parent[index] = value
        else:
            raise MutationError(f"List index out of range: {key}")

        return

    raise MutationError("Cannot set value on non-container parent.")


def _remove_item(obj: Any, path: str) -> None:
    parent, key = _get_parent_and_key(obj, path)

    if isinstance(parent, dict):
        if key not in parent:
            raise MutationError(f"Key not found for removal: {key}")

        del parent[key]
        return

    if isinstance(parent, list):
        try:
            index = int(key)
        except ValueError as exc:
            raise MutationError(
                f"List index must be numeric: {key}"
            ) from exc

        if index < 0 or index >= len(parent):
            raise MutationError(f"List index out of range: {key}")

        del parent[index]
        return

    raise MutationError("Cannot remove item from non-container parent.")


def _merge_object(obj: Any, path: str, value: Any) -> None:
    parent, key = _get_parent_and_key(obj, path)

    if not isinstance(parent, dict):
        raise MutationError(
            "MERGE_OBJECT can only be applied to dictionary parents."
        )

    existing = parent.get(key)

    if isinstance(existing, dict) and isinstance(value, dict):
        merged = deep_copy(existing)
        merged.update(deep_copy(value))
        parent[key] = merged
    else:
        parent[key] = deep_copy(value)


class MutationEngine:
    """Applies mutation specifications to ISR payloads."""

    def apply(
        self,
        base_isr: dict[str, Any],
        spec: MutationSpec,
    ) -> dict[str, Any]:
        candidate = deep_copy(base_isr)

        for operation in spec.operations:
            if operation.operation == MutationOperationType.SET_VALUE:
                _set_value(candidate, operation.path, operation.value)

            elif operation.operation == MutationOperationType.ADD_ITEM:
                container = _get_container(candidate, operation.path)

                if not isinstance(container, list):
                    raise MutationError(
                        f"ADD_ITEM target path must be a list: {operation.path}"
                    )

                container.append(operation.value)

            elif operation.operation == MutationOperationType.REMOVE_ITEM:
                _remove_item(candidate, operation.path)

            elif operation.operation == MutationOperationType.MERGE_OBJECT:
                _merge_object(candidate, operation.path, operation.value)

            else:
                raise MutationError(
                    f"Unsupported mutation operation: {operation.operation}"
                )

        candidate.setdefault("evolution", {})
        candidate["evolution"].setdefault("mutations", [])

        candidate["evolution"]["mutations"].append(
            {
                "mutation_id": spec.id,
                "operator": spec.operator,
                "chromosome_family": spec.chromosome_family,
                "gene_id": spec.gene_id,
                "rationale": spec.rationale,
            }
        )

        # Baseline governance floor: every expressed architecture is born governed.
        # Mutations that set "governance" (e.g. strengthen_governance) take precedence;
        # this only fills the gap for non-governance mutations so candidates never
        # fail-closed to 0.0 on the governance selection gate.
        candidate.setdefault("governance", baseline_governance_design())

        return candidate
