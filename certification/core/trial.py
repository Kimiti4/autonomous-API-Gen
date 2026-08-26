"""Trial — the unit of CBC-1 behavioral certification."""
from __future__ import annotations
from enum import Enum
from typing import List
from pydantic import BaseModel, ConfigDict, Field


class TrialStage(str, Enum):
    STRUCTURAL = "structural"
    SEMANTIC = "semantic"
    BUILD = "build"
    TEST = "test"
    DEPLOY = "deploy"
    RUNTIME = "runtime"
    DESTROY = "destroy"
    VERIFY = "verify"


class StageEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)
    stage: TrialStage
    passed: bool
    started_at: str
    completed_at: str
    logs_hash: str
    detail: str = ""


class TrialMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)
    compiler_correctness: dict = Field(default_factory=dict)
    functional_correctness: dict = Field(default_factory=dict)
    engineering_quality: dict = Field(default_factory=dict)
    operational_correctness: dict = Field(default_factory=dict)
    isr_semantic_conformance: float = 0.0


class Trial(BaseModel):
    model_config = ConfigDict(frozen=True)
    trial_id: str
    intent: str
    category: str
    novelty_class: str
    requirement_graph_hash: str
    genome_hash: str
    isr_revision_id: str
    backend: str
    compiler_version: str
    repo_hash: str
    stages: List[StageEvidence] = Field(default_factory=list)
    metrics: TrialMetrics = Field(default_factory=TrialMetrics)
    verdict: str = "NOT_CERTIFIED"


REQUIRED_STAGES = [
    TrialStage.STRUCTURAL,
    TrialStage.SEMANTIC,
    TrialStage.BUILD,
    TrialStage.TEST,
    TrialStage.DEPLOY,
    TrialStage.RUNTIME,
    TrialStage.DESTROY,
    TrialStage.VERIFY,
]


def compose_verdict(stages: dict[TrialStage, bool], evidence_present: bool) -> str:
    """All required stages must have passed and evidence must be present."""
    if not evidence_present:
        return "NOT_CERTIFIED"
    for s in REQUIRED_STAGES:
        if not stages.get(s):
            return "NOT_CERTIFIED"
    return "CERTIFIED"
