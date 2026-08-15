from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CompilerMetrics:
    total_compilations: int = 0
    total_artifacts: int = 0
    total_errors: int = 0
    total_warnings: int = 0
    total_time_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0

    def record_compilation(self, elapsed_ms: float, artifacts: int, errors: int, warnings: int) -> None:
        self.total_compilations += 1
        self.total_artifacts += artifacts
        self.total_errors += errors
        self.total_warnings += warnings
        self.total_time_ms += elapsed_ms

    def record_cache(self, hit: bool) -> None:
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
