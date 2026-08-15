"""R2 -- deterministic failure classifier (R2.2).

Maps a backend execution outcome (command + exit code + bounded stdout/stderr)
to a technology-neutral FailureObservation. No external API, no
non-determinism: classification is driven purely by exit code, phase, and known
compiler/test diagnostic patterns. The first Evolution Engine must run keyless,
so this is deliberately rule-based.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from tiannara.domain.models.observation import (
    FailureCategory,
    FailureObservation,
    FailurePhase,
    Severity,
)
from tiannara.domain.services.canonical import canonical_hash

_OUTPUT_LIMIT = 8000

_RULES: list[tuple[FailureCategory, Severity, float, re.Pattern[str]]] = [
    (FailureCategory.SYNTAX_FAILURE, Severity.HIGH, 0.92,
     re.compile(r"syntax error|string not terminated|non-default argument|"
                r"unexpected literal|missing semicolon|expected '|expected \""
                r"|unmatched|illegal character", re.IGNORECASE)),
    (FailureCategory.TYPE_FAILURE, Severity.HIGH, 0.9,
     re.compile(r"mismatched types|type mismatch|cannot use .* as \w+|incompatible type|"
                r"does not implement|cannot assign", re.IGNORECASE)),
    (FailureCategory.DEPENDENCY_FAILURE, Severity.HIGH, 0.88,
     re.compile(r"cannot find (package|module)|no required module|undefined: \S+|"
                r"unknown import|package .* is not in std|module .* not found|"
                r"no Go files|No such file or directory.*go\.mod", re.IGNORECASE)),
    (FailureCategory.RUNTIME_FAILURE, Severity.MEDIUM, 0.78,
     re.compile(r"connection refused|connection reset|no such host|read-only file|"
                r"no route to host|ECONNREFUSED|panic:|nil pointer|address already in use|"
                r"bind.*denied|permission denied|timeout.*deadline", re.IGNORECASE)),
    (FailureCategory.TEST_FAILURE, Severity.MEDIUM, 0.72,
     re.compile(r"\bFAIL\b|assert|Error:|Traceback \(most recent|FAILED|"
                r"panic:|test timed out", re.IGNORECASE)),
]


@dataclass(frozen=True)
class FailureEvidenceInput:
    execution_id: str
    backend_id: str
    phase: FailurePhase
    command: tuple[str, ...]
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    affected_artifacts: tuple[str, ...] = field(default_factory=tuple)

    def bounded_text(self) -> str:
        return (self.stdout + "\n" + self.stderr)[:_OUTPUT_LIMIT]


class FailureClassifier:
    def classify(self, inp: FailureEvidenceInput) -> Optional[FailureObservation]:
        if inp.exit_code == 0:
            return None
        text = inp.bounded_text()
        for category, severity, confidence, pattern in _RULES:
            if pattern.search(text):
                return FailureObservation(
                    execution_id=inp.execution_id,
                    backend_id=inp.backend_id,
                    phase=inp.phase,
                    category=category,
                    severity=severity,
                    command=list(inp.command),
                    exit_code=inp.exit_code,
                    diagnostics=self._diagnostics(text, pattern),
                    affected_artifacts=list(inp.affected_artifacts),
                    confidence=confidence,
                    evidence_hash=self._hash(inp, category),
                    stdout_excerpt=inp.stdout[:1000],
                    stderr_excerpt=inp.stderr[:1000],
                )
        default = (
            FailureCategory.BUILD_FAILURE if inp.phase in (FailurePhase.COMPILE, FailurePhase.BUILD)
            else FailureCategory.RUNTIME_FAILURE
        )
        return FailureObservation(
            execution_id=inp.execution_id,
            backend_id=inp.backend_id,
            phase=inp.phase,
            category=default,
            severity=Severity.LOW,
            command=list(inp.command),
            exit_code=inp.exit_code,
            diagnostics=[],
            affected_artifacts=list(inp.affected_artifacts),
            confidence=0.4,
            evidence_hash=self._hash(inp, default),
            stdout_excerpt=inp.stdout[:1000],
            stderr_excerpt=inp.stderr[:1000],
        )

    @staticmethod
    def _diagnostics(text: str, pattern: re.Pattern[str]) -> list[str]:
        matched = [ln.strip() for ln in text.splitlines() if pattern.search(ln)]
        return (matched or [text[:200]])[:5]

    @staticmethod
    def _hash(inp: FailureEvidenceInput, category: FailureCategory) -> str:
        return canonical_hash(
            {
                "execution_id": inp.execution_id,
                "backend_id": inp.backend_id,
                "phase": inp.phase.value,
                "command": list(inp.command),
                "exit_code": inp.exit_code,
                "category": category.value,
                "artifacts": list(inp.affected_artifacts),
                "text": inp.bounded_text(),
            }
        )
