from __future__ import annotations

import hashlib
from typing import Any, Optional


class CompilationCache:
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def compute_key(self, isr_hash: str, config_hash: str, compiler_version: str) -> str:
        raw = f"{isr_hash}:{config_hash}:{compiler_version}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def get(self, key: str) -> Optional[Any]:
        return self._store.get(key)

    def put(self, key: str, value: Any) -> None:
        self._store[key] = value

    def clear(self) -> None:
        self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)
