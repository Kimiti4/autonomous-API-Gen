"""
Phase 28 — Constitution Manager.

Creates, versions, activates, and deprecates constitutions (Milestone 1).
A constitution is the highest-level governance object; its content hash is
immutable once recorded, and activation is a monotonic lifecycle event.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from constitutional_architecture.governance.schemas import (
    ConstitutionISR,
    ConstitutionStatus,
    ExceptionPolicy,
    Invariant,
    utcnow,
)


class ConstitutionManager:
    """Versioned store for constitutions (in-memory for v0.1)."""

    def __init__(self) -> None:
        self._constitutions: Dict[str, ConstitutionISR] = {}
        self._versions: Dict[str, Dict[str, ConstitutionISR]] = {}

    def create(
        self,
        name: str,
        description: str = "",
        *,
        invariants: Optional[List[Invariant]] = None,
        policy_domains: Optional[List[str]] = None,
        exception_policy: Optional[ExceptionPolicy] = None,
        parent_id: Optional[str] = None,
        parent_version: Optional[str] = None,
        created_by: str = "governance_kernel",
    ) -> ConstitutionISR:
        if parent_id is not None and parent_id not in self._constitutions:
            raise KeyError(f"Parent constitution {parent_id} does not exist.")
        version = self._next_version(parent_id)
        constitution = ConstitutionISR(
            id=parent_id or self._new_id(),
            version=version,
            name=name,
            description=description,
            invariants=invariants or [],
            policy_domains=policy_domains or [],
            exception_policy=exception_policy or ExceptionPolicy(),
            parent_id=parent_id,
            parent_version=parent_version,
            created_by=created_by,
        )
        constitution.recompute_hash()
        self._versions.setdefault(constitution.id, {})[constitution.version] = (
            constitution
        )
        self._constitutions[constitution.id] = constitution
        return constitution

    def get(self, constitution_id: str) -> ConstitutionISR:
        return self._constitutions[constitution_id]

    def get_version(
        self, constitution_id: str, version: str
    ) -> ConstitutionISR:
        return self._versions[constitution_id][version]

    def activate(self, constitution_id: str) -> ConstitutionISR:
        constitution = self._constitutions[constitution_id]
        if constitution.status is ConstitutionStatus.REVOKED:
            raise ValueError("A revoked constitution cannot be activated.")
        constitution.status = ConstitutionStatus.ACTIVE
        constitution.effective_at = utcnow()
        return constitution

    def under_review(self, constitution_id: str) -> ConstitutionISR:
        constitution = self._constitutions[constitution_id]
        if constitution.status is ConstitutionStatus.ACTIVE:
            raise ValueError("An active constitution cannot return to review.")
        constitution.status = ConstitutionStatus.UNDER_REVIEW
        return constitution

    def deprecate(self, constitution_id: str) -> ConstitutionISR:
        constitution = self._constitutions[constitution_id]
        if constitution.status is ConstitutionStatus.REVOKED:
            raise ValueError("A revoked constitution cannot be deprecated.")
        constitution.status = ConstitutionStatus.DEPRECATED
        return constitution

    def revoke(self, constitution_id: str) -> ConstitutionISR:
        constitution = self._constitutions[constitution_id]
        constitution.status = ConstitutionStatus.REVOKED
        return constitution

    def active(self) -> List[ConstitutionISR]:
        return sorted(
            (
                c
                for c in self._constitutions.values()
                if c.status is ConstitutionStatus.ACTIVE
            ),
            key=lambda c: c.id,
        )

    def list(self) -> List[ConstitutionISR]:
        return sorted(self._constitutions.values(), key=lambda c: c.id)

    @staticmethod
    def _new_id() -> str:
        return f"constitution_{uuid.uuid4().hex[:10]}"

    def _next_version(self, parent_id: Optional[str]) -> str:
        if parent_id is None:
            return "0.1.0"
        parts = [int(p) for p in self._constitutions[parent_id].version.split(".")]
        parts[-1] += 1
        return ".".join(str(p) for p in parts)
