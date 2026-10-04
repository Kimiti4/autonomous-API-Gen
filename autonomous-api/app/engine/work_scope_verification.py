"""Bind materialized ESAP work domains to scope-derived verification."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from .scope_verification import ChangeScope, DerivedVerificationPlan, derive_verification_plan
from .verification_command_planner import CompiledVerificationPlan, VerificationCommandRule, compile_verification_commands


DOMAIN_SCOPE_MAP: Mapping[str, ChangeScope] = {
    "frontend": ChangeScope.FRONTEND,
    "backend": ChangeScope.BACKEND,
    "api": ChangeScope.API,
    "data": ChangeScope.DATA,
    "database": ChangeScope.DATA,
    "security": ChangeScope.SECURITY,
    "operations": ChangeScope.OPERATIONS,
    "ops": ChangeScope.OPERATIONS,
    "documentation": ChangeScope.DOCUMENTATION,
    "docs": ChangeScope.DOCUMENTATION,
}


@dataclass(frozen=True)
class WorkVerificationPlan:
    domains: tuple[str, ...]
    scopes: tuple[ChangeScope, ...]
    obligations: DerivedVerificationPlan
    executable: CompiledVerificationPlan


def derive_work_verification_plan(
    domains: Iterable[str],
    *,
    workspace_id: str,
    command_rules: Sequence[VerificationCommandRule],
) -> WorkVerificationPlan:
    normalized = tuple(dict.fromkeys(domains))
    if not normalized:
        raise ValueError("missing-work-domains")

    scopes: list[ChangeScope] = []
    for domain in normalized:
        scope = DOMAIN_SCOPE_MAP.get(domain.lower())
        if scope is None:
            raise ValueError("missing-domain-scope:" + domain)
        if scope not in scopes:
            scopes.append(scope)

    obligations = derive_verification_plan(tuple(scopes))
    executable = compile_verification_commands(
        obligations,
        workspace_id=workspace_id,
        command_rules=command_rules,
    )
    return WorkVerificationPlan(
        domains=normalized,
        scopes=tuple(scopes),
        obligations=obligations,
        executable=executable,
    )
