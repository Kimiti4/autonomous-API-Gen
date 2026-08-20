"""R2.10.32.9 — External tool availability: which evidence producers are
actually present.

The honesty of 32.9 is measured by how truthfully it reports
TOOL_NOT_INSTALLED, not by whether every tool happens to be present.
Absence is a state, never an omission — this is what keeps the
certification's quality dimensions honest about what was and wasn't
evidenced. The Implementation Quality dimension reads this report and
marks itself PROVEN only for the tools actually executed, UNPROVEN for
those absent (vacuity policy: tool unavailable != tool found zero
defects).
"""
from dataclasses import dataclass
from typing import Mapping

from tiannara.application.quality.tool_adapters import (
    AnalyzerRegistry,
    ToolExecutionState,
)

__all__ = [
    "REQUIRED_EXTERNAL_TOOLS",
    "ToolAvailabilityProbe",
    "ToolAvailabilityReport",
    "implementation_quality_dimension_state",
]


REQUIRED_EXTERNAL_TOOLS: tuple[str, ...] = (
    "ruff",
    "pylint",
    "mypy",
    "bandit",
    "eslint",
    "tsc",
    "sonar",
    "spotbugs",
    "pmd",
    "golangci_lint",
    "clippy",
)


@dataclass(frozen=True)
class ToolAvailabilityReport:
    """Which external producers are actually present. Absence is a state,
    never an omission."""

    states: Mapping[str, ToolExecutionState]  # tool_id -> state
    available: tuple[str, ...]
    not_installed: tuple[str, ...]


class ToolAvailabilityProbe:
    """Probes the 32.8 registry — availability and execution share one
    source of truth."""

    def probe(self, registry: AnalyzerRegistry) -> ToolAvailabilityReport:
        states = {
            tool: registry.execution_state(tool)
            for tool in REQUIRED_EXTERNAL_TOOLS
        }
        return ToolAvailabilityReport(
            states=states,
            available=tuple(
            t
            for t, s in states.items()
            if s is ToolExecutionState.ANALYSIS_COMPLETED
        ),
        not_installed=tuple(
            t
            for t, s in states.items()
            if s is ToolExecutionState.TOOL_NOT_INSTALLED
        ),
        )


def implementation_quality_dimension_state(
    report: ToolAvailabilityReport,
) -> str:
    """The dimension's state from the availability report, per the vacuity
    policy: PROVEN only for executed producers; a missing producer marks
    the dimension UNPROVEN (or PARTIALLY_PROVEN where some tools ran)."""
    if report.available and not report.not_installed:
        return "PROVEN"
    if report.available:
        return "PARTIALLY_PROVEN"
    return "UNPROVEN"