from __future__ import annotations

from typing import Optional

from constitutional_architecture.verification.verification_result import VerificationLevel
from constitutional_architecture.verification.verifiers.verifier_interface import Verifier


class VerificationRegistry:
    def __init__(self) -> None:
        self._verifiers: dict[str, Verifier] = {}

    def register(self, verifier: Verifier) -> None:
        if verifier.name in self._verifiers:
            raise ValueError(f"Verifier '{verifier.name}' already registered")
        self._verifiers[verifier.name] = verifier

    def unregister(self, name: str) -> None:
        if name not in self._verifiers:
            raise ValueError(f"Verifier '{name}' not found")
        del self._verifiers[name]

    def get(self, name: str) -> Optional[Verifier]:
        return self._verifiers.get(name)

    def get_by_level(self, level: VerificationLevel) -> list[Verifier]:
        return [v for v in self._verifiers.values() if v.level == level]

    def get_up_to_level(self, max_level: VerificationLevel) -> list[Verifier]:
        eligible = [v for v in self._verifiers.values() if v.level <= max_level]
        return sorted(eligible, key=lambda v: v.level.value)

    @property
    def all_names(self) -> list[str]:
        return list(self._verifiers.keys())

    @property
    def count(self) -> int:
        return len(self._verifiers)

    def __contains__(self, name: str) -> bool:
        return name in self._verifiers
