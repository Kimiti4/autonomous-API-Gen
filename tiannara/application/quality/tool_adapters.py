"""R2.10.32.8 — External Tool Adapters: evidence production as a plugin
boundary.

32.7 defined the evidence-production contract; 32.8 proves it against
the contract's execution states and output shapes with a deterministic
exemplar adapter, then makes external tools registrations rather than
redesigns. The governing rule: an adapter TRANSLATES tool output into
the analyzer contract's shape; it never interprets architectural
meaning. Normalization is structural (Ruff's F401 becomes
category="unused_import"), never semantic (it does not become
architectural_violation=true) — that mapping, where it exists at all, is
a declared certification concern, not an adapter decision.

The five rules this module makes mechanical:

    1. External tools are plugins: the registry is the only dispatch
       surface; certification logic contains no `if analyzer == "ruff"`.
    2. Tool failure is never a clean result: TOOL_EXECUTION_FAILED,
       TOOL_TIMEOUT, TOOL_NOT_INSTALLED, TOOL_INVALID_OUTPUT are
       distinct states — a missing analyzer never reads as zero
       findings (the vacuity policy applied to evidence production).
    3. Raw provenance is preserved: the normalized evidence points back
       to a content-addressed raw result (the platform's canonical
       content-addressing), so a finding is auditable to the exact tool
       output that produced it.
    4. Normalization is structural, not semantic.
    5. Tool absence is epistemically visible: a tool that is not
       installed is TOOL_NOT_INSTALLED, surfaced as NOT_AVAILABLE in
       the dimensions it covers — never PASS, never silently omitted.

No real-tool dependencies yet: the exemplar proves the adapter pattern
against deterministic simulated output across all five execution states.
Ruff/Pylint/MyPy/Bandit/ESLint/tsc/Sonar/SpotBugs/PMD/golangci-lint/
Clippy become adapters implementing the identical surface once the
pattern is validated — a dozen adapters built against an unvalidated
pattern is a tooling-integration project; one adapter that exercises
every state is a proven contract.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Optional, Protocol

from tiannara.evidence.integrity import canonical_json, sha256_hex
from tiannara.application.quality.analyzer_contract import (
    AnalyzerFinding,
    AnalyzerIdentity,
    derive_execution_identity,
)

__all__ = [
    "AnalyzerRegistry",
    "ExemplarToolAdapter",
    "ExternalToolAdapter",
    "InvalidToolOutput",
    "ToolExecution",
    "ToolExecutionState",
    "content_address",
]


class ToolExecutionState(str, Enum):
    """Tool failure is never a clean result. A missing or failed analyzer
    is epistemically visible — never '0 findings', never PASS."""

    ANALYSIS_COMPLETED = "ANALYSIS_COMPLETED"
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_NOT_INSTALLED = "TOOL_NOT_INSTALLED"
    TOOL_INVALID_OUTPUT = "TOOL_INVALID_OUTPUT"


class InvalidToolOutput(ValueError):
    """Tool output cannot be normalized into the contract's shape."""


def content_address(payload: Any) -> str:
    """Content-address a raw tool output (or finding item) using the
    platform's canonical content-addressing: the address changes iff the
    content changes, so a finding's evidence_refs chain to the exact
    tool output that produced it."""
    return sha256_hex(canonical_json(payload))


@dataclass(frozen=True)
class ToolExecution:
    """One tool execution, carrying raw provenance: the normalized
    evidence points back to a content-addressed raw result, so a finding
    is auditable to the exact tool output that produced it."""

    state: ToolExecutionState
    analyzer_id: str
    analyzer_version: Optional[str]
    artifact_identity: str
    configuration_identity: str
    execution_identity: str
    raw_output_identity: Optional[str]  # content-addressed raw result
    normalized_findings: tuple[AnalyzerFinding, ...]


class ExternalToolAdapter(Protocol):
    """An adapter translates tool output into the analyzer contract's
    shape. It never decides architectural meaning — normalization is
    structural, and 'this finding implies an architectural violation' is
    a certification mapping, never an adapter judgment."""

    @property
    def identity(self) -> AnalyzerIdentity: ...

    def execute(self, artifact, configuration) -> ToolExecution: ...

    def normalize(self, raw_output) -> tuple[AnalyzerFinding, ...]: ...


class AnalyzerRegistry:
    """The plugin boundary: external tools are registered implementations,
    never special cases. Certification logic contains no
    `if analyzer == 'ruff'`."""

    def __init__(self) -> None:
        self._adapters: dict[str, ExternalToolAdapter] = {}

    def register(self, adapter: ExternalToolAdapter) -> None:
        self._adapters[adapter.identity.analyzer_id] = adapter

    def resolve(self, analyzer_id: str) -> Optional[ExternalToolAdapter]:
        return self._adapters.get(analyzer_id)

    def execution_state(self, analyzer_id: str) -> ToolExecutionState:
        """Tool absence is a state, not an omission."""
        adapter = self.resolve(analyzer_id)
        return (
            ToolExecutionState.TOOL_NOT_INSTALLED
            if adapter is None
            else ToolExecutionState.ANALYSIS_COMPLETED
        )


def _artifact_identity(artifact) -> str:
    return artifact["provenance"]["artifact_hash"]


def _configuration_identity(configuration) -> str:
    return configuration["configuration_id"]


class ExemplarToolAdapter:
    """The first adapter proves the contract against every execution state
    and multiple output shapes, using deterministic simulated tool
    output so the pattern is validated without a runtime dependency.
    Real-tool adapters (Ruff, ESLint, Clippy, ...) implement the
    identical surface afterward.

    The exemplar demonstrates the translation discipline: raw tool
    output becomes normalized findings with the contract's provenance,
    raw output is content-addressed, and every failure mode surfaces as
    its own state.
    """

    def __init__(
        self,
        identity: AnalyzerIdentity,
        simulated_modes: Mapping[str, Any],
    ) -> None:
        self._identity = identity
        self._modes = simulated_modes  # mode -> simulated raw output (None = crash)

    @property
    def identity(self) -> AnalyzerIdentity:
        return self._identity

    def execute(self, artifact, configuration) -> ToolExecution:
        mode = configuration["mode"]
        artifact_id = _artifact_identity(artifact)
        configuration_id = _configuration_identity(configuration)
        execution_identity = derive_execution_identity(
            self._identity.analyzer_id,
            self._identity.analyzer_version,
            artifact_id,
            configuration_id,
        )
        if mode == "not_installed":
            return ToolExecution(
                ToolExecutionState.TOOL_NOT_INSTALLED,
                self._identity.analyzer_id,
                None,
                artifact_id,
                configuration_id,
                execution_identity,
                None,
                (),
            )
        if mode == "timeout":
            return ToolExecution(
                ToolExecutionState.TOOL_TIMEOUT,
                self._identity.analyzer_id,
                self._identity.analyzer_version,
                artifact_id,
                configuration_id,
                execution_identity,
                None,
                (),
            )
        raw = self._modes[mode]
        if raw is None:
            return ToolExecution(
                ToolExecutionState.TOOL_EXECUTION_FAILED,
                self._identity.analyzer_id,
                self._identity.analyzer_version,
                artifact_id,
                configuration_id,
                execution_identity,
                None,
                (),
            )
        raw_identity = content_address(raw)
        try:
            findings = self.normalize(raw)
        except InvalidToolOutput:
            return ToolExecution(
                ToolExecutionState.TOOL_INVALID_OUTPUT,
                self._identity.analyzer_id,
                self._identity.analyzer_version,
                artifact_id,
                configuration_id,
                execution_identity,
                raw_identity,
                (),
            )
        return ToolExecution(
            ToolExecutionState.ANALYSIS_COMPLETED,
            self._identity.analyzer_id,
            self._identity.analyzer_version,
            artifact_id,
            configuration_id,
            execution_identity,
            raw_identity,
            findings,
        )

    def normalize(self, raw_output) -> tuple[AnalyzerFinding, ...]:
        """Structural normalization only: tool-native concepts become
        contract categories; the adapter never interprets architectural
        meaning."""
        findings = []
        try:
            items = raw_output["findings"]
        except (KeyError, TypeError) as exc:
            raise InvalidToolOutput(
                "tool output carries no findings record"
            ) from exc
        for item in items:
            try:
                artifact_id = item["artifact"]
                configuration_id = item["config"]
                execution_id = item["execution"]
                severity = item["severity"]
                category = item["category"]
                message = item["message"]
                location = item.get("location")
            except (KeyError, TypeError) as exc:
                raise InvalidToolOutput(
                    f"tool output item missing required field {exc.args[0]}"
                ) from exc
            findings.append(
                AnalyzerFinding(
                    finding_id=f"exemplar-{content_address(item)[:12]}",
                    analyzer_id=self._identity.analyzer_id,
                    analyzer_version=self._identity.analyzer_version,
                    artifact_identity=artifact_id,
                    configuration_identity=configuration_id,
                    execution_identity=execution_id,
                    severity=severity,
                    category=category,
                    description=message,
                    location=location,
                    evidence_refs=(content_address(item),),
                    obligation_id=None,  # emergent unless a declared mapping exists
                )
            )
        return tuple(findings)