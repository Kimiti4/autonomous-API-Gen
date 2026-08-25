"""Provisioning ladder -- installed is not provisioned."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
from tiannara.application.quality.tool_adapters import ToolExecutionState


class ToolProvisioningState(str, Enum):
    TOOL_NOT_INSTALLED = "TOOL_NOT_INSTALLED"
    INSTALLED = "INSTALLED"
    EXECUTABLE = "EXECUTABLE"
    EXECUTED = "EXECUTED"
    EVIDENCE_PRODUCED = "EVIDENCE_PRODUCED"
    CERTIFICATION_ELIGIBLE = "CERTIFICATION_ELIGIBLE"


@dataclass(frozen=True)
class ToolProvisioningRecord:
    tool_id: str
    state: ToolProvisioningState
    version: str | None
    identity: str | None
    invocation_ref: str | None
    deterministic_verified: bool
    artifact_bound: bool
    ledger_address: str | None


@dataclass(frozen=True)
class ProvisioningVerdict:
    eligible: bool
    records: tuple[ToolProvisioningRecord, ...]
    ineligible_tools: tuple[str, ...]
    provisioning_event_ref: str


class ProvisioningIncomplete(RuntimeError):
    pass


class ProvisioningAcceptanceGate:
    REQUIRED_TOOLS = ("ruff", "pylint", "mypy", "bandit", "eslint", "tsc", "sonar", "spotbugs", "pmd", "golangci_lint", "clippy")

    def verify(self, registry, probe_artifact, ledger: EvolutionLedger) -> ProvisioningVerdict:
        records = tuple(self._verify_tool(registry.resolve(t) if hasattr(registry, "resolve") else registry.get(t), probe_artifact, ledger, t) for t in self.REQUIRED_TOOLS)
        ineligible = tuple(r.tool_id for r in records if r.state is not ToolProvisioningState.CERTIFICATION_ELIGIBLE)
        # Record provisioning verdict to ledger
        event = EvolutionEvent(
            event_id=f"provisioning-{canonical_hash(str(sorted(self.REQUIRED_TOOLS)))[:8]}",
            evolution_id="provisioning",
            sequence=0,
            event_type=EventType.CERTIFICATION,
            subject_id="provisioning",
            payload={"eligible": not bool(ineligible), "ineligible": list(ineligible), "records": [r.state.value for r in records]},
        )
        ref = ledger.append_event(event, evolution_id="provisioning")
        return ProvisioningVerdict(not bool(ineligible), records, ineligible, ref)

    def _verify_tool(self, tool, probe_artifact, ledger: EvolutionLedger, tool_id: str) -> ToolProvisioningRecord:
        if tool is None:
            return ToolProvisioningRecord(tool_id=tool_id, state=ToolProvisioningState.TOOL_NOT_INSTALLED, version=None, identity=None, invocation_ref=None, deterministic_verified=False, artifact_bound=False, ledger_address=None)
        # Check installed
        is_installed = getattr(tool, "is_installed", lambda: True)()
        if not is_installed:
            return ToolProvisioningRecord(tool_id=tool_id, state=ToolProvisioningState.TOOL_NOT_INSTALLED, version=None, identity=None, invocation_ref=None, deterministic_verified=False, artifact_bound=False, ledger_address=None)
        version = getattr(tool, "version", None)
        if callable(version):
            version = version()
        else:
            version = getattr(tool, "version", "1.0.0")
            if hasattr(tool, "identity"):
                try:
                    version = tool.identity.analyzer_version
                except Exception:
                    pass
        identity = getattr(tool, "identity", None)
        if identity is not None and hasattr(identity, "analyzer_id"):
            identity_str = identity.analyzer_id
        else:
            identity_str = tool_id
        is_executable = getattr(tool, "is_executable", lambda: True)()
        if not is_executable:
            return ToolProvisioningRecord(tool_id=tool_id, state=ToolProvisioningState.INSTALLED, version=str(version) if version else "1.0.0", identity=identity_str, invocation_ref=None, deterministic_verified=False, artifact_bound=False, ledger_address=None)
        # Try invoke
        invoke = getattr(tool, "invoke", None) or getattr(tool, "execute", None)
        if invoke is None:
            return ToolProvisioningRecord(tool_id=tool_id, state=ToolProvisioningState.EXECUTABLE, version=str(version), identity=identity_str, invocation_ref=None, deterministic_verified=False, artifact_bound=False, ledger_address=None)
        try:
            result1 = invoke(probe_artifact)
        except Exception:
            return ToolProvisioningRecord(tool_id=tool_id, state=ToolProvisioningState.EXECUTABLE, version=str(version), identity=identity_str, invocation_ref=None, deterministic_verified=False, artifact_bound=False, ledger_address=None)
        # Check execution state
        state1 = getattr(result1, "state", None) or getattr(result1, "status", None)
        if state1 is not ToolExecutionState.ANALYSIS_COMPLETED:
            # If result is dict-like, check
            return ToolProvisioningRecord(tool_id=tool_id, state=ToolProvisioningState.EXECUTABLE, version=str(version), identity=identity_str, invocation_ref=None, deterministic_verified=False, artifact_bound=False, ledger_address=None)
        try:
            result2 = invoke(probe_artifact)
        except Exception:
            return ToolProvisioningRecord(tool_id=tool_id, state=ToolProvisioningState.EXECUTED, version=str(version), identity=identity_str, invocation_ref=None, deterministic_verified=False, artifact_bound=False, ledger_address=None)
        id1 = getattr(result1, "raw_output_identity", None) or getattr(result1, "raw_output_hash", None) or str(result1)
        id2 = getattr(result2, "raw_output_identity", None) or getattr(result2, "raw_output_hash", None) or str(result2)
        if id1 != id2:
            return ToolProvisioningRecord(tool_id=tool_id, state=ToolProvisioningState.EXECUTED, version=str(version), identity=identity_str, invocation_ref=None, deterministic_verified=False, artifact_bound=False, ledger_address=None)
        # Evidence produced and ledger-addressed
        evidence_ref = f"tool-evidence-{tool_id}-{str(version)[:8]}"
        # Record to ledger
        ev = EvolutionEvent(
            event_id=evidence_ref,
            evolution_id=f"tool-{tool_id}",
            sequence=0,
            event_type=EventType.CERTIFICATION,
            subject_id=tool_id,
            payload={"tool_id": tool_id, "version": str(version), "raw_identity": str(id1)},
        )
        ledger.append_event(ev, evolution_id=f"tool-{tool_id}")
        return ToolProvisioningRecord(tool_id=tool_id, state=ToolProvisioningState.CERTIFICATION_ELIGIBLE, version=str(version), identity=identity_str, invocation_ref=evidence_ref, deterministic_verified=True, artifact_bound=True, ledger_address=evidence_ref)


def canonical_hash(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest()
