from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from constitutional_architecture.compiler.compilation_config import CompilationConfig
from constitutional_architecture.compiler.quality.diagnostics import DiagnosticsCollector
from constitutional_architecture.isr.model.isr import ISR


@dataclass
class CompilerContext:
    _isr: ISR
    _config: CompilationConfig
    _current_isr: Optional[ISR] = None
    diagnostics: DiagnosticsCollector = field(default_factory=DiagnosticsCollector)
    source_map_entries: list[dict[str, Any]] = field(default_factory=list)
    capability_contracts: dict[str, Any] = field(default_factory=dict)
    bir: Optional[Any] = None
    compilation_plan: Optional[Any] = None
    artifacts: list[Any] = field(default_factory=list)
    backend_registry: Optional[Any] = None
    pass_timings: dict[str, float] = field(default_factory=dict)
    pass_metrics: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self._current_isr is None:
            self._current_isr = self._isr

    @property
    def isr(self) -> ISR:
        return self._current_isr

    @property
    def original_isr(self) -> ISR:
        return self._isr

    @property
    def config(self) -> CompilationConfig:
        return self._config

    @property
    def isr_hash(self) -> str:
        return self._isr.content_hash

    @property
    def current_isr_hash(self) -> str:
        return self._current_isr.content_hash if self._current_isr else self._isr.content_hash

    def update_isr(self, new_isr: ISR) -> None:
        self._current_isr = new_isr

    def add_source_mapping(self, entry: dict[str, Any]) -> None:
        self.source_map_entries.append(entry)

    def add_capability_contract(self, name: str, contract: Any) -> None:
        self.capability_contracts[name] = contract

    def record_pass_timing(self, pass_id: str, duration_ms: float) -> None:
        self.pass_timings[pass_id] = duration_ms

    def record_pass_metrics(self, pass_id: str, metrics: dict[str, Any]) -> None:
        self.pass_metrics[pass_id] = metrics
