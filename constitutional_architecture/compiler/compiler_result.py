from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from constitutional_architecture.compiler.quality.diagnostics import Diagnostic


@dataclass(frozen=True)
class CapabilityReport:
    resolved: dict[str, str] = field(default_factory=dict)
    unresolved: tuple[str, ...] = ()
    hints_applied: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class VerificationResult:
    passed: bool = False
    checks_run: int = 0
    checks_passed: int = 0
    checks_failed: int = 0


@dataclass(frozen=True)
class CompilationResult:
    isr_hash: str = ""
    config_hash: str = ""
    compiler_version: str = ""
    artifacts: tuple[Any, ...] = ()
    artifact_count: int = 0
    diagnostics: tuple[Diagnostic, ...] = ()
    error_count: int = 0
    warning_count: int = 0
    compilation_time_ms: float = 0.0
    pass_timings: dict[str, float] = field(default_factory=dict)
    targets_compiled: tuple[str, ...] = ()
    capability_report: CapabilityReport = field(default_factory=CapabilityReport)
    verification: VerificationResult = field(default_factory=VerificationResult)
    source_map_entries: int = 0
    success: bool = False
