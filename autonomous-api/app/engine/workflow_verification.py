"""Workflow execution with invariant evaluation and counterexamples."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Mapping, Any
from .workflow_graph import WorkflowScenario
from .workflow_properties import PropertyAssertion, PropertyReport, evaluate_properties


@dataclass(frozen=True)
class WorkflowCounterexample:
    scenario_id: str
    violated_assertions: tuple[str, ...]
    reasons: tuple[str, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class VerifiedWorkflowExecution:
    scenario_id: str
    execution_passed: bool
    properties: PropertyReport
    counterexample: WorkflowCounterexample | None
    evidence: tuple[str, ...]

    @property
    def verified(self) -> bool:
        return self.execution_passed and self.properties.passed


def execute_and_verify(
    scenario: WorkflowScenario,
    runner: Callable[[WorkflowScenario], Mapping[str, Any]],
    assertions: tuple[PropertyAssertion, ...],
) -> VerifiedWorkflowExecution:
    observations = runner(scenario)
    execution_passed = bool(observations.get("passed", False))
    report = evaluate_properties(observations, assertions)
    evidence = tuple(observations.get("evidence", ()))

    violations = tuple(r for r in report.results if not r.passed)
    counterexample = None
    if violations:
        counterexample = WorkflowCounterexample(
            scenario.scenario_id,
            tuple(r.assertion_id for r in violations),
            tuple(r.reason for r in violations),
            evidence,
        )

    return VerifiedWorkflowExecution(
        scenario.scenario_id,
        execution_passed,
        report,
        counterexample,
        evidence,
    )


def counterexample_is_actionable(
    result: VerifiedWorkflowExecution,
) -> bool:
    return result.counterexample is not None and bool(
        result.counterexample.evidence
    )
