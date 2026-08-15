"""
Phase 16.1 — Governance Chromosome: Capability Schema & Registry.

The capability ledger is the constitutional source for every UI projection
(Decision ESAP-HIL-ARCH-001 / D-1). It lives in the ISR Governance
chromosome, is owned by the CKB, and is consumed — never mutated — by the
projection pipeline.

Migration doctrine (ratified): renames are additive —
    deprecate(old) + introduce(new)
— with a compatibility window of schema versions during which BOTH claims
are emitted. The registry therefore never edits a capability record in
place; it appends lifecycle transitions.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field


class CapabilityStatus(str, Enum):
    ACTIVE = "active"
    INTRODUCED = "introduced"      # compatibility window open, claims emitted
    DEPRECATED = "deprecated"      # compatibility window open, claims emitted
    RETIRED = "retired"            # window closed, claims no longer emitted


class Capability(BaseModel):
    """A single ledger entry on the Governance chromosome."""

    id: str
    name: str
    family: str
    description: str = ""
    status: CapabilityStatus = CapabilityStatus.ACTIVE
    replaces: Optional[str] = None       # capability this one supersedes
    introduced_at: Optional[int] = None  # schema version of introduction
    deprecated_at: Optional[int] = None  # schema version of deprecation


class CapabilityAlias(BaseModel):
    alias: str
    target: str


class CapabilityRegistry(BaseModel):
    """
    Deny-by-default ledger. Capabilities must be registered before they can
    ever be granted; unknown ids resolve to nothing (denial).
    """

    SCHEMA_VERSION: str = "governance.1"
    compatibility_window: int = 2  # schema versions both claims are emitted

    schema_version: int = 1
    capabilities: Dict[str, Capability] = Field(default_factory=dict)
    aliases: Dict[str, str] = Field(default_factory=dict)

    def register(self, cap: Capability) -> None:
        if cap.id in self.capabilities:
            raise ValueError(f"Capability {cap.id} already registered.")
        self.capabilities[cap.id] = cap

    def get(self, cap_id: str) -> Optional[Capability]:
        return self.capabilities.get(cap_id)

    def add_alias(self, alias: str, target: str) -> None:
        if target not in self.capabilities:
            raise ValueError(f"Alias target {target} is not registered.")
        self.aliases[alias] = target

    def advance_schema_version(self) -> int:
        self.schema_version += 1
        return self.schema_version

    def deprecate(self, cap_id: str) -> Capability:
        cap = self._require(cap_id)
        cap.status = CapabilityStatus.DEPRECATED
        cap.deprecated_at = self.schema_version
        return cap

    def introduce(
        self,
        cap_id: str,
        name: str,
        family: str,
        *,
        replaces: Optional[str] = None,
        description: str = "",
    ) -> Capability:
        """
        Additive migration: deprecate(old) + introduce(new). Both records
        coexist; both claims are emitted for the compatibility window.
        """
        if cap_id in self.capabilities:
            raise ValueError(f"Capability {cap_id} already registered.")
        if replaces is not None:
            self._require(replaces).status = CapabilityStatus.DEPRECATED
            self.capabilities[replaces].deprecated_at = self.schema_version
        new = Capability(
            id=cap_id,
            name=name,
            family=family,
            description=description,
            status=CapabilityStatus.INTRODUCED,
            replaces=replaces,
            introduced_at=self.schema_version,
        )
        self.capabilities[cap_id] = new
        return new

    def retire(self, cap_id: str) -> Capability:
        cap = self._require(cap_id)
        cap.status = CapabilityStatus.RETIRED
        return cap

    def _require(self, cap_id: str) -> Capability:
        cap = self.capabilities.get(cap_id)
        if cap is None:
            raise KeyError(f"Unknown capability {cap_id}.")
        return cap

    def _resolve(self, cap_id: str) -> str:
        seen: Set[str] = set()
        while cap_id in self.aliases and cap_id not in seen:
            seen.add(cap_id)
            cap_id = self.aliases[cap_id]
        return cap_id

    def _emits_claims(self, cap: Capability) -> bool:
        if cap.status is CapabilityStatus.RETIRED:
            return False
        if cap.status is CapabilityStatus.DEPRECATED:
            window_open = (
                cap.deprecated_at is not None
                and (self.schema_version - cap.deprecated_at)
                < self.compatibility_window
            )
            return window_open
        return True

    def _successor(self, cap: Capability) -> Optional[Capability]:
        """New capability introduced to replace this one (window mapping)."""
        if cap.status is not CapabilityStatus.DEPRECATED:
            return None
        for other in self.capabilities.values():
            if other.replaces == cap.id:
                return other
        return None

    def claims_for(self, granted: Set[str]) -> frozenset[str]:
        """
        Effective capability claims for a principal given the raw grants.
        Deterministic: alias resolution, then window expansion (holding the
        deprecated capability also yields the successor's claim while the
        compatibility window is open), then retirement filtering.
        """
        claims: Set[str] = set()
        for raw in granted:
            cap = self.capabilities.get(self._resolve(raw))
            if cap is None or not self._emits_claims(cap):
                continue
            claims.add(cap.id)
            successor = self._successor(cap)
            if successor is not None and self._emits_claims(successor):
                claims.add(successor.id)
        return frozenset(sorted(claims))

    def valid_ids(self) -> List[str]:
        return sorted(
            cap_id
            for cap_id, cap in self.capabilities.items()
            if self._emits_claims(cap)
        )

    def ledger_hash(self) -> str:
        """Content-addressed fingerprint of the ledger (append-only record)."""
        payload = {
            "schema_version": self.schema_version,
            "compatibility_window": self.compatibility_window,
            "capabilities": {
                cid: cap.model_dump()
                for cid, cap in sorted(self.capabilities.items())
            },
            "aliases": dict(sorted(self.aliases.items())),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
