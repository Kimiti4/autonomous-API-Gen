"""33.6 Reuse 32.7 Analyzer contract -- observation only."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from tiannara.domain.services.canonical import canonical_hash
@dataclass(frozen=True)
class SecurityFinding:
    finding_id: str; analyzer_id: str; artifact_hash: str; severity: str
class SecurityAnalyzer(Protocol):
    @property
    def identity(self): ...
    def analyze(self, artifact) -> tuple[SecurityFinding, ...]: ...
@dataclass(frozen=True)
class ReferenceSecurityAnalyzer:
    analyzer_id: str = "ref-sec"
    version: str = "1.0.0"
    @property
    def identity(self): return type("I",(),{"analyzer_id": self.analyzer_id, "analyzer_version": self.version})()
    def analyze(self, artifact):
        return (SecurityFinding(f"finding-{artifact.get('artifact_hash','')[:6]}", self.analyzer_id, artifact.get("artifact_hash",""), "LOW"),)
    def execution_identity(self, artifact): return canonical_hash(artifact.get("artifact_hash",""))
