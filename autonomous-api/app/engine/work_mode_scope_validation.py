"""Governed capability validation for Bucket 2 mode/surface combinations."""

from __future__ import annotations

from .generation_scope import GenerationScope
from .work_capability import WorkCapabilityContract
from .work_mode import WorkMode


def validate_mode_surface(contract: WorkCapabilityContract) -> None:
    mode = contract.mode.mode
    scope = contract.generation.scope

    # Architecture/documentation/SEO/test work may intentionally target a
    # single surface; full-stack remains available when explicitly requested.
    allowed = {
        WorkMode.DOCUMENT: {
            GenerationScope.FULL_APPLICATION, GenerationScope.FRONTEND_ONLY,
            GenerationScope.BACKEND_ONLY, GenerationScope.API_CONTRACT_ONLY,
        },
        WorkMode.SEO: {
            GenerationScope.FULL_APPLICATION, GenerationScope.FRONTEND_ONLY,
        },
        WorkMode.TEST: {
            GenerationScope.FULL_APPLICATION, GenerationScope.FRONTEND_ONLY,
            GenerationScope.BACKEND_ONLY, GenerationScope.API_CONTRACT_ONLY,
        },
        WorkMode.ARCHITECTURE: {
            GenerationScope.FULL_APPLICATION, GenerationScope.FRONTEND_ONLY,
            GenerationScope.BACKEND_ONLY, GenerationScope.API_CONTRACT_ONLY,
        },
        WorkMode.MIGRATE: {
            GenerationScope.FULL_APPLICATION, GenerationScope.FRONTEND_ONLY,
            GenerationScope.BACKEND_ONLY, GenerationScope.API_CONTRACT_ONLY,
        },
        WorkMode.REFACTOR: {
            GenerationScope.FULL_APPLICATION, GenerationScope.FRONTEND_ONLY,
            GenerationScope.BACKEND_ONLY, GenerationScope.API_CONTRACT_ONLY,
        },
        WorkMode.CROSS_STACK: {GenerationScope.FULL_APPLICATION},
    }
    if mode in allowed and scope not in allowed[mode]:
        raise ValueError(f"incompatible-work-mode-and-generation-scope:{mode.value}:{scope.value}")
