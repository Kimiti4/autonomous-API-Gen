"""Explicit software-generation scope contracts for ESAP."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GenerationScope(str, Enum):
    FULL_APPLICATION = "full_application"
    FRONTEND_ONLY = "frontend_only"
    BACKEND_ONLY = "backend_only"
    API_CONTRACT_ONLY = "api_contract_only"


@dataclass(frozen=True)
class ScopeContract:
    """Explicitly declares which software surface ESAP is permitted to change."""

    scope: GenerationScope
    preserve_frontend: bool
    preserve_backend: bool
    preserve_api_contract: bool

    @classmethod
    def for_scope(cls, scope: GenerationScope) -> "ScopeContract":
        return cls(
            scope=scope,
            preserve_frontend=scope in (
                GenerationScope.BACKEND_ONLY,
                GenerationScope.API_CONTRACT_ONLY,
            ),
            preserve_backend=scope in (
                GenerationScope.FRONTEND_ONLY,
                GenerationScope.API_CONTRACT_ONLY,
            ),
            preserve_api_contract=scope is GenerationScope.FRONTEND_ONLY,
        )

    def allows(self, surface: str) -> bool:
        if surface == "frontend":
            return not self.preserve_frontend
        if surface == "backend":
            return not self.preserve_backend
        if surface == "api_contract":
            return not self.preserve_api_contract
        raise ValueError(f"unknown-software-surface:{surface}")


def validate_scope(scope: GenerationScope) -> ScopeContract:
    if not isinstance(scope, GenerationScope):
        raise ValueError("invalid-generation-scope")
    return ScopeContract.for_scope(scope)
