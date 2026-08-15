from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from constitutional_architecture.verification.verification_context import VerificationContext
from constitutional_architecture.verification.verification_result import (
    VerificationCheck,
    VerificationLevel,
    VerificationResult,
)


class Verifier(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    @abstractmethod
    def level(self) -> VerificationLevel:
        ...

    @property
    def requires_artifacts(self) -> bool:
        return self.level >= VerificationLevel.L1_STATIC

    @abstractmethod
    def verify(self, ctx: VerificationContext) -> VerificationResult:
        ...

    def can_verify(self, ctx: VerificationContext) -> bool:
        if self.requires_artifacts and not ctx.has_artifacts:
            return False
        return True
