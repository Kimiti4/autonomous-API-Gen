"""Context assembly — builds ContextGraphs from ISR slices and evidence.

The EvidenceSource port is the seam where the Constitutional Knowledge Base
will plug in. Until then, StaticEvidenceSource serves authored fragment
libraries (committed JSONL) — a real source, real content, no fabrication.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, runtime_checkable

from tiannara.domain.models.context_graph import (
    ContextGraph,
    ContextKind,
    ContextNode,
    EvidenceFragment,
)
from tiannara.domain.models.intelligence import TaskKind
from tiannara.domain.models.system_model import Priority, SystemModel


@runtime_checkable
class EvidenceSource(Protocol):
    def query(self, task_kind: TaskKind, limit: int) -> list[EvidenceFragment]:
        ...


class StaticEvidenceSource:
    """Serves committed evidence fragments from memory or JSONL files."""

    def __init__(self, fragments: list[EvidenceFragment]) -> None:
        self._fragments = list(fragments)

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "StaticEvidenceSource":
        fragments: list[EvidenceFragment] = []
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    fragments.append(EvidenceFragment.model_validate_json(line))
        return cls(fragments)

    def query(self, task_kind: TaskKind, limit: int) -> list[EvidenceFragment]:
        matched = [
            fragment
            for fragment in self._fragments
            if not fragment.task_kinds or task_kind.value in fragment.task_kinds
        ]
        matched.sort(key=lambda f: (-f.relevance, f.fragment_id))
        return matched[: max(0, limit)]


class IsrContextExtractor:
    """Deterministic ISR slicing into prioritized context nodes.

    Focus semantics: with no subject_ref, capabilities are MUST; with a
    subject_ref, the matched capability/service is promoted to MUST and the
    rest demote — the model sees the subject sharply, surroundings softly.
    Security posture is always MUST.
    """

    def extract(
        self, model: SystemModel, subject_ref: str | None = None
    ) -> list[ContextNode]:
        nodes: list[ContextNode] = []
        focused = subject_ref is not None

        nodes.append(
            ContextNode(
                node_id="isr-security",
                kind=ContextKind.SECURITY_POSTURE,
                priority=Priority.MUST,
                title="Security posture",
                payload=model.security.model_dump(mode="json"),
            )
        )

        for capability in model.capabilities:
            is_focus = subject_ref == capability.id
            priority = Priority.MUST if (is_focus or not focused) else Priority.SHOULD
            nodes.append(
                ContextNode(
                    node_id=f"isr-cap-{capability.id}",
                    kind=ContextKind.CAPABILITY,
                    priority=priority,
                    title=capability.name,
                    payload=capability.model_dump(mode="json"),
                )
            )

        for service in model.services:
            is_focus = subject_ref == service.id
            priority = (
                Priority.MUST
                if is_focus
                else (Priority.SHOULD if not focused else Priority.COULD)
            )
            nodes.append(
                ContextNode(
                    node_id=f"isr-svc-{service.id}",
                    kind=ContextKind.SERVICE,
                    priority=priority,
                    title=service.name,
                    payload=service.model_dump(mode="json"),
                )
            )

        data_priority = Priority.SHOULD if not focused else Priority.COULD
        for data_model in model.data_models:
            nodes.append(
                ContextNode(
                    node_id=f"isr-data-{data_model.id}",
                    kind=ContextKind.DATA_MODEL,
                    priority=data_priority,
                    title=data_model.name,
                    payload=data_model.model_dump(mode="json"),
                )
            )

        nodes.append(
            ContextNode(
                node_id="isr-ops",
                kind=ContextKind.OPERATIONAL_POLICY,
                priority=data_priority,
                title="Operational policies",
                payload=model.operational_policies.model_dump(mode="json"),
            )
        )
        nodes.append(
            ContextNode(
                node_id="isr-testing",
                kind=ContextKind.TESTING_POLICY,
                priority=Priority.COULD,
                title="Testing policy",
                payload=model.testing.model_dump(mode="json"),
            )
        )
        nodes.append(
            ContextNode(
                node_id="isr-docs",
                kind=ContextKind.DOCUMENTATION_POLICY,
                priority=Priority.COULD,
                title="Documentation policy",
                payload=model.documentation.model_dump(mode="json"),
            )
        )
        return nodes


class ContextAssembler:
    def __init__(
        self,
        evidence_source: EvidenceSource | None = None,
        extractor: IsrContextExtractor | None = None,
    ) -> None:
        self._evidence = evidence_source
        self._extractor = extractor or IsrContextExtractor()

    def assemble_graph(
        self,
        task_kind: TaskKind,
        isr: SystemModel | None = None,
        subject_ref: str | None = None,
        extra_nodes: tuple[ContextNode, ...] = (),
        evidence_limit: int = 3,
    ) -> ContextGraph:
        nodes: list[ContextNode] = []
        if isr is not None:
            nodes.extend(self._extractor.extract(isr, subject_ref))
        if self._evidence is not None and evidence_limit > 0:
            for fragment in self._evidence.query(task_kind, evidence_limit):
                nodes.append(self._evidence_node(fragment))
        nodes.extend(extra_nodes)
        return ContextGraph.derive(
            task_kind=task_kind, nodes=nodes, subject_ref=subject_ref
        )

    @staticmethod
    def _evidence_node(fragment: EvidenceFragment) -> ContextNode:
        return ContextNode(
            node_id=f"ev-{fragment.fragment_id}",
            kind=ContextKind.EVIDENCE,
            priority=Priority.SHOULD,
            title=fragment.title,
            payload={
                "kind": fragment.kind,
                "relevance": fragment.relevance,
                **fragment.payload,
            },
        )
