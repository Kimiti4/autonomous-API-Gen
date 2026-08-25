"""Per-cell analyzer evidence capture."""
from __future__ import annotations

from dataclasses import dataclass

from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
from tiannara.application.quality.tool_adapters import ToolExecutionState
from tiannara.domain.services.canonical import canonical_hash


def artifact_identity(artifact) -> str:
    return artifact.get("provenance", {}).get("artifact_hash", "unknown")


@dataclass(frozen=True)
class AnalyzerExecution:
    analyzer_id: str
    analyzer_version: str
    configuration_identity: str
    execution_state: ToolExecutionState
    raw_output_identity: str
    findings_ref: str


@dataclass(frozen=True)
class AnalyzerExecutionEvidence:
    cell_id: str
    artifact_identity: str
    executions: tuple[AnalyzerExecution, ...]
    complete: bool


class AnalyzerEvidenceCapture:
    def __init__(self, ledger: EvolutionLedger, registry):
        self._ledger = ledger
        self._registry = registry

    def capture(self, cell_id, artifact, required_analyzers) -> AnalyzerExecutionEvidence:
        executions = []
        for analyzer_id in required_analyzers:
            tool = self._registry.resolve(analyzer_id) if hasattr(self._registry, "resolve") else None
            if tool is None:
                executions.append(AnalyzerExecution(analyzer_id, "unknown", "unknown", ToolExecutionState.TOOL_NOT_INSTALLED, "", ""))
                continue
            try:
                # Try to execute
                result = tool.execute(artifact, {"analyzer": analyzer_id}) if hasattr(tool, "execute") else tool.invoke(artifact)
                state = getattr(result, "state", ToolExecutionState.ANALYSIS_COMPLETED)
                raw_id = getattr(result, "raw_output_identity", canonical_hash(str(result)))
                version = getattr(getattr(tool, "identity", None), "analyzer_version", "1.0.0")
                findings_ref = f"findings-{cell_id}-{analyzer_id}"
                # Record to ledger
                ev = EvolutionEvent(event_id=findings_ref, evolution_id=cell_id, sequence=0, event_type=EventType.CERTIFICATION, subject_id=cell_id, payload={"analyzer_id": analyzer_id, "raw_identity": raw_id})
                self._ledger.append_event(ev, evolution_id=cell_id)
                executions.append(AnalyzerExecution(analyzer_id, str(version), "config-1", state, str(raw_id), findings_ref))
            except Exception:
                executions.append(AnalyzerExecution(analyzer_id, "unknown", "unknown", ToolExecutionState.TOOL_EXECUTION_FAILED, "", ""))
        complete = all(e.execution_state is ToolExecutionState.ANALYSIS_COMPLETED for e in executions)
        evidence = AnalyzerExecutionEvidence(cell_id, artifact_identity(artifact), tuple(executions), complete)
        # Record aggregate
        ev2 = EvolutionEvent(event_id=f"analyzer-evidence-{cell_id}", evolution_id=cell_id, sequence=0, event_type=EventType.CERTIFICATION, subject_id=cell_id, payload={"cell_id": cell_id, "complete": complete})
        self._ledger.append_event(ev2, evolution_id=cell_id)
        return evidence
