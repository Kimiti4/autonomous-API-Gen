"""Scope-discipline gate for autonomous ESAP work.

The requested scope is the source of truth. Autonomous implementation may
only execute declared work items; optional ideas are suggestions, never
implicit mutations. Completion must be certified before suggestions are
released.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .scope_authorization import MutationIntent


@dataclass(frozen=True)
class RequiredWorkItem:
    work_id: str
    title: str
    target: str


@dataclass(frozen=True)
class ScopeDisciplineDecision:
    authorized: tuple[MutationIntent, ...]
    rejected: tuple[MutationIntent, ...]
    reasons: tuple[str, ...]


def authorize_required_work(
    mutations: Iterable[MutationIntent],
    required_items: Iterable[RequiredWorkItem],
) -> ScopeDisciplineDecision:
    items = tuple(required_items)
    by_target = {item.target: item for item in items}
    authorized: list[MutationIntent] = []
    rejected: list[MutationIntent] = []
    reasons: list[str] = []

    for mutation in tuple(mutations):
        if mutation.target not in by_target:
            rejected.append(mutation)
            reasons.append(f"unrequested-work:{mutation.target}")
            continue
        authorized.append(mutation)

    return ScopeDisciplineDecision(
        tuple(authorized),
        tuple(rejected),
        tuple(sorted(set(reasons))),
    )


def require_no_scope_creep(decision: ScopeDisciplineDecision) -> None:
    if decision.rejected:
        raise ValueError("scope-creep-blocked:" + ",".join(decision.reasons))


def release_suggestions_only_after_certification(
    *,
    certified: bool,
    suggestions: Mapping[str, str],
) -> tuple[tuple[str, str], ...]:
    if not certified:
        return ()
    return tuple(sorted((feature, reason) for feature, reason in suggestions.items() if reason.strip()))
