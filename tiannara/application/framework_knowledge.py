"""Versioned, evidence-oriented framework knowledge contracts.

This layer deliberately stores framework metadata and reasoning constraints, not
a hardcoded implementation of expert programming knowledge. It gives the
reasoner a structured, provenance-aware knowledge surface that can be refreshed
from authoritative documentation, source, release notes, and verified builds.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping, Tuple

@dataclass(frozen=True)
class FrameworkKnowledgeClaim:
    claim_id: str
    statement: str
    source_kind: str
    source_ref: str
    confidence: str = "bounded"
    version_range: str = "*"

@dataclass(frozen=True)
class FrameworkKnowledgePack:
    framework_id: str
    language: str
    versions: Tuple[str, ...]
    concepts: Tuple[str, ...]
    capabilities: Mapping[str, str]
    constraints: Tuple[str, ...]
    anti_patterns: Tuple[str, ...]
    claims: Tuple[FrameworkKnowledgeClaim, ...] = field(default_factory=tuple)

    def claims_for(self, version: str) -> Tuple[FrameworkKnowledgeClaim, ...]:
        return tuple(c for c in self.claims if c.version_range == "*" or c.version_range == version)

    def capability(self, name: str) -> str | None:
        return self.capabilities.get(name)
