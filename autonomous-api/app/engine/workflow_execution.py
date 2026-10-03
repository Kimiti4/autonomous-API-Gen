"""Executable workflow specification adapters and evidence records."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Mapping, Any
from .workflow_graph import WorkflowScenario


@dataclass(frozen=True)
class WorkflowExecution:
    scenario_id: str
    observed_nodes: tuple[str, ...]
    passed: bool
    evidence: tuple[str, ...]
    failure_reason: str | None = None


@dataclass(frozen=True)
class WorkflowEvidence:
    evidence_id: str
    scenario_id: str
    result: str  # pass, fail, inconclusive
    observations: tuple[str, ...]
    artifacts: tuple[str, ...] = ()


def execute_scenario(
    scenario: WorkflowScenario,
    runner: Callable[[WorkflowScenario], Mapping[str, Any]],
) -> WorkflowExecution:
    result = runner(scenario)
    observed = tuple(result.get("observed_nodes", ()))
    passed = bool(result.get("passed", False))
    evidence = tuple(result.get("evidence", ()))
    reason = result.get("failure_reason")
    return WorkflowExecution(
        scenario.scenario_id, observed, passed, evidence, reason
    )


def materialize_evidence(
    execution: WorkflowExecution,
    evidence_id: str,
) -> WorkflowEvidence:
    if execution.passed:
        result = "pass"
    elif execution.failure_reason:
        result = "fail"
    else:
        result = "inconclusive"
    return WorkflowEvidence(
        evidence_id,
        execution.scenario_id,
        result,
        execution.evidence + execution.observed_nodes,
    )


def execution_is_actionable(execution: WorkflowExecution) -> bool:
    return bool(execution.evidence) and (
        execution.passed or execution.failure_reason is not None
    )
