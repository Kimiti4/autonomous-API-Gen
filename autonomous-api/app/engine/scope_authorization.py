"""Governed mutation authorization for ESAP generation scopes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .generation_scope import ScopeContract, validate_scope


@dataclass(frozen=True)
class MutationIntent:
    """A proposed mutation against one governed software surface."""

    surface: str
    operation: str
    target: str

    def __post_init__(self) -> None:
        if not self.surface:
            raise ValueError("missing-mutation-surface")
        if not self.operation:
            raise ValueError("missing-mutation-operation")
        if not self.target:
            raise ValueError("missing-mutation-target")


class ScopeViolation(PermissionError):
    """Raised when a mutation is outside the declared generation scope."""


def authorize_mutation(contract: ScopeContract, mutation: MutationIntent) -> None:
    """Fail closed when a proposed mutation is outside the authorized scope."""
    if not contract.allows(mutation.surface):
        raise ScopeViolation(
            f"scope-violation:{contract.scope.value}:{mutation.surface}"
        )


def authorize_mutations(
    contract: ScopeContract,
    mutations: Iterable[MutationIntent],
) -> tuple[MutationIntent, ...]:
    """Validate the complete mutation set before execution."""
    authorized = tuple(mutations)
    for mutation in authorized:
        authorize_mutation(contract, mutation)
    return authorized


def authorize_scope_mutations(scope, mutations: Iterable[MutationIntent]) -> tuple[MutationIntent, ...]:
    """Convenience boundary: validate scope and authorize all mutations."""
    return authorize_mutations(validate_scope(scope), mutations)
