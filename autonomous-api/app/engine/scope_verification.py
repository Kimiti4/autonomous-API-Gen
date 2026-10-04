"""Derive executable verification requirements from ESAP change scope."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping, Sequence
from .verification_acceptance import VerificationAcceptancePolicy
from .verification_executor import VerificationKind, VerificationSpec


class ChangeScope(str, Enum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    API = "api"
    DATA = "data"
    SECURITY = "security"
    OPERATIONS = "operations"
    DOCUMENTATION = "documentation"


@dataclass(frozen=True)
class ScopeVerificationRule:
    scope: ChangeScope
    required_kinds: tuple[VerificationKind, ...]
    artifact_kinds: tuple[VerificationKind, ...] = ()


@dataclass(frozen=True)
class DerivedVerificationPlan:
    scopes: tuple[ChangeScope, ...]
    required_kinds: tuple[VerificationKind, ...]
    require_artifacts_for: tuple[VerificationKind, ...]
    acceptance: VerificationAcceptancePolicy


DEFAULT_SCOPE_RULES: tuple[ScopeVerificationRule, ...] = (
    ScopeVerificationRule(ChangeScope.FRONTEND, (VerificationKind.BUILD, VerificationKind.TEST)),
    ScopeVerificationRule(ChangeScope.BACKEND, (VerificationKind.TEST, VerificationKind.TYPECHECK)),
    ScopeVerificationRule(ChangeScope.API, (VerificationKind.TEST, VerificationKind.SMOKE_TEST)),
    ScopeVerificationRule(ChangeScope.DATA, (VerificationKind.TEST,)),
    ScopeVerificationRule(ChangeScope.SECURITY, (VerificationKind.TEST, VerificationKind.SMOKE_TEST)),
    ScopeVerificationRule(ChangeScope.OPERATIONS, (VerificationKind.TEST, VerificationKind.SMOKE_TEST)),
    ScopeVerificationRule(ChangeScope.DOCUMENTATION, (VerificationKind.LINT,)),
)


def derive_verification_plan(
    scopes: Iterable[ChangeScope],
    *,
    rules: Sequence[ScopeVerificationRule] = DEFAULT_SCOPE_RULES,
) -> DerivedVerificationPlan:
    normalized = tuple(dict.fromkeys(scopes))
    by_scope = {rule.scope: rule for rule in rules}
    required: list[VerificationKind] = []
    artifacts: list[VerificationKind] = []
    for scope in normalized:
        rule = by_scope.get(scope)
        if rule is None:
            raise ValueError("missing-verification-rule:" + scope.value)
        for kind in rule.required_kinds:
            if kind not in required:
                required.append(kind)
        for kind in rule.artifact_kinds:
            if kind not in artifacts:
                artifacts.append(kind)
    return DerivedVerificationPlan(
        scopes=normalized,
        required_kinds=tuple(required),
        require_artifacts_for=tuple(artifacts),
        acceptance=VerificationAcceptancePolicy(
            required_kinds=tuple(k.value for k in required),
            require_artifacts_for=tuple(k.value for k in artifacts),
        ),
    )
