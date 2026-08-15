"""
Phase 28 — Lineage Repository.

Tracks relationships between changes, artifacts, approvals, and evidence
(Milestone 4). Answers, forward and backward:
    where did this artifact come from,
    what proposal caused it,
    what policies were evaluated,
    who approved it,
    what evidence supported it,
    what rollback path exists.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from constitutional_architecture.governance.schemas import ChangeLineage


class LineageRepository:
    def __init__(self) -> None:
        self._links: List[ChangeLineage] = []
        self._by_id: Dict[str, ChangeLineage] = {}

    def record(
        self,
        parent_artifact_type: str,
        parent_artifact_id: str,
        parent_artifact_hash: str,
        child_artifact_type: str,
        child_artifact_id: str,
        child_artifact_hash: str,
        change_type: str,
        *,
        cause_ref: Optional[str] = None,
        decision_ref: Optional[str] = None,
        approval_refs: Optional[List[str]] = None,
        evidence_refs: Optional[List[str]] = None,
        rollback_plan_ref: Optional[str] = None,
    ) -> ChangeLineage:
        link = ChangeLineage(
            id=f"lineage_{uuid.uuid4().hex[:10]}",
            parent_artifact_type=parent_artifact_type,
            parent_artifact_id=parent_artifact_id,
            parent_artifact_hash=parent_artifact_hash,
            child_artifact_type=child_artifact_type,
            child_artifact_id=child_artifact_id,
            child_artifact_hash=child_artifact_hash,
            change_type=change_type,
            cause_ref=cause_ref,
            decision_ref=decision_ref,
            approval_refs=approval_refs or [],
            evidence_refs=evidence_refs or [],
            rollback_plan_ref=rollback_plan_ref,
        )
        self._links.append(link)
        self._by_id[link.id] = link
        return link

    def trace_backward(
        self, artifact_type: str, artifact_id: str
    ) -> List[ChangeLineage]:
        """Who produced this artifact, and what governed it?"""
        return [
            link
            for link in self._links
            if link.child_artifact_type == artifact_type
            and link.child_artifact_id == artifact_id
        ]

    def trace_forward(
        self, artifact_type: str, artifact_id: str
    ) -> List[ChangeLineage]:
        """What did this artifact produce?"""
        return [
            link
            for link in self._links
            if link.parent_artifact_type == artifact_type
            and link.parent_artifact_id == artifact_id
        ]

    def by_decision(self, decision_ref: str) -> List[ChangeLineage]:
        return [
            link
            for link in self._links
            if link.decision_ref == decision_ref
        ]

    def ancestors(
        self, artifact_type: str, artifact_id: str
    ) -> List[ChangeLineage]:
        """Full backward chain to the root cause, in order."""
        chain: List[ChangeLineage] = []
        seen: set[tuple] = set()
        current_type, current_id = artifact_type, artifact_id
        while (current_type, current_id) not in seen:
            seen.add((current_type, current_id))
            parents = self.trace_backward(current_type, current_id)
            if not parents:
                break
            link = parents[0]
            chain.append(link)
            current_type, current_id = link.parent_artifact_type, link.parent_artifact_id
        return chain

    def all(self) -> List[ChangeLineage]:
        return list(self._links)
