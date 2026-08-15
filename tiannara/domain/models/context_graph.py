"""Context Graph — the canonical representation of what an intelligence
task needs to know.

If the ISR is the canonical representation of a software system, the
Context Graph is the canonical representation of a prompt's inputs.
Prompts are compiled artifacts: the PromptCompiler weaves a Context Graph,
a TokenBudget, and a TaskInstruction into a CompiledPrompt, exactly as a
compiler backend weaves the ISR into a deployable bundle.

Properties encoded here:
  * determinism — identical graphs hash identically across platforms;
  * prioritised context — MUST/SHOULD/COULD govern budget behaviour;
  * evidence as data — historical knowledge enters through typed fragments,
    never through ad-hoc string concatenation.
"""

from __future__ import annotations

import enum
import json
from typing import Any

from pydantic import BaseModel, Field, model_validator

from ..services.canonical import canonical_hash
from .intelligence import TaskKind
from .system_model import Priority


class ContextKind(str, enum.Enum):
    REQUIREMENT = "requirement"
    CAPABILITY = "capability"
    SERVICE = "service"
    DATA_MODEL = "data_model"
    SECURITY_POSTURE = "security_posture"
    OPERATIONAL_POLICY = "operational_policy"
    TESTING_POLICY = "testing_policy"
    DOCUMENTATION_POLICY = "documentation_policy"
    EVIDENCE = "evidence"
    CONSTRAINT = "constraint"
    EXAMPLE = "example"


class ContextNode(BaseModel):
    """One unit of context. Rendered deterministically; never truncated.

    A node either fits the budget whole or is dropped (SHOULD/COULD);
    MUST nodes that do not fit fail compilation. Truncation of mandatory
    context would be fabrication by omission.
    """

    node_id: str = Field(min_length=1)
    kind: ContextKind
    priority: Priority = Priority.SHOULD
    title: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)

    def render(self) -> str:
        header = f"### [{self.kind.value}:{self.priority.value}] {self.title or self.node_id}"
        body = json.dumps(self.payload, sort_keys=True, indent=2, ensure_ascii=True)
        return f"{header}\n{body}"


class EvidenceFragment(BaseModel):
    """A unit of historical/architectural knowledge served into context.

    The Constitutional Knowledge Base, when built, will surface fragments
    through the same shape; authored pattern libraries serve through it now.
    """

    fragment_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    task_kinds: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class ContextGraph(BaseModel):
    graph_id: str = Field(min_length=1)
    task_kind: TaskKind
    subject_ref: str | None = None
    nodes: list[ContextNode] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_node_ids(self) -> "ContextGraph":
        ids = [node.node_id for node in self.nodes]
        if len(ids) != len(set(ids)):
            duplicates = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"duplicate context node ids: {duplicates}")
        return self

    def content_hash(self) -> str:
        return canonical_hash(self.model_dump(mode="json", exclude={"graph_id"}))

    @classmethod
    def derive(
        cls,
        task_kind: TaskKind,
        nodes: list[ContextNode],
        subject_ref: str | None = None,
    ) -> "ContextGraph":
        provisional = cls(
            graph_id="pending", task_kind=task_kind, subject_ref=subject_ref, nodes=nodes
        )
        digest = provisional.content_hash()
        return provisional.model_copy(update={"graph_id": f"cg-{digest[:16]}"})
