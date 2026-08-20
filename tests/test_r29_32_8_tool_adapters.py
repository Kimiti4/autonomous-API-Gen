"""R2.10.32.8 — External Tool Adapters: evidence production as a plugin
boundary.

The acceptance surface:

    * the registry is the only dispatch surface — tools are registered
      implementations, never special cases;
    * tool absence is epistemically visible: a missing analyzer is
      TOOL_NOT_INSTALLED, never PASS, never silently omitted;
    * the exemplar exercises every execution state — the contract is
      proven against all five failure/output modes, not just the happy
      path;
    * tool failure never reads as a clean result (vacuity policy);
    * normalized findings point at content-addressed raw output;
    * normalization is structural, not semantic: the adapter translates
      categories, never architectural meaning, and has no
      verdict/obligation surface;
    * the exemplar reuses 32.7's deterministic execution identity;
    * the recipe ISR and capability matrix are byte-identical (Option A).
"""
import ast
import inspect

import pytest

from tiannara.application.quality.analyzer_contract import AnalyzerIdentity
from tiannara.application.quality.tool_adapters import (
    AnalyzerRegistry,
    ExemplarToolAdapter,
    ToolExecution,
    ToolExecutionState,
    content_address,
)

from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"

EXEMPLAR_IDENTITY = AnalyzerIdentity(
    analyzer_id="exemplar",
    analyzer_version="1.0.0",
    supported_languages=("python",),
    supported_evidence_classes=("exemplar_inspection",),
)

EXEMPLAR_SIMULATED_MODES = {
    "completed": {
        "findings": (
            {
                "artifact": "ac-artifact-hash",
                "config": "exemplar-config-v1",
                "execution": "exemplar-exec-1",
                "severity": "WARNING",
                "category": "unused_import",
                "message": "unused import re",
                "location": "mod_a.py:12",
            },
            {
                "artifact": "ac-artifact-hash",
                "config": "exemplar-config-v1",
                "execution": "exemplar-exec-1",
                "severity": "ADVISORY",
                "category": "line_too_long",
                "message": "line exceeds length",
                "location": "mod_a.py:34",
            },
        )
    },
    "failed": None,
    "timeout": None,
    "not_installed": None,
    "invalid_output": {
        "findings": ({"message": "missing required fields"},)
    },
}

MODES = (
    "completed",
    "failed",
    "timeout",
    "not_installed",
    "invalid_output",
)


def _artifact() -> dict:
    return {
        "modules": (),
        "provenance": {
            "artifact_hash": "ac-artifact-hash",
            "backend_id": "ac-backend",
        },
    }


def _configuration(mode: str) -> dict:
    return {"configuration_id": "exemplar-config-v1", "mode": mode}


class ToolAdapterHarness:
    """The 32.8 machinery: the registry with the exemplar adapter
    registered, and the simulated-mode driver."""

    def __init__(self) -> None:
        self._recipe = CampaignReadinessHarness()
        self._registry = AnalyzerRegistry()
        self._exemplar = ExemplarToolAdapter(
            EXEMPLAR_IDENTITY, EXEMPLAR_SIMULATED_MODES
        )
        self._registry.register(self._exemplar)

    def registry(self) -> AnalyzerRegistry:
        return self._registry

    def run_exemplar(self, mode: str) -> ToolExecution:
        return self._exemplar.execute(_artifact(), _configuration(mode))

    def matrix_summary(self):
        return self._recipe.matrix_summary()

    def recipe_isr_hash(self):
        return self._recipe.recipe_isr_hash()


@pytest.fixture(scope="module")
def adapter_harness() -> ToolAdapterHarness:
    return ToolAdapterHarness()


def test_registry_is_the_only_dispatch_surface(adapter_harness):
    """No tool-specific branching in certification logic: the registry
    resolves."""
    registry = adapter_harness.registry()
    assert registry.resolve("exemplar") is not None
    assert registry.resolve("nonexistent") is None


def test_tool_absence_is_epistemically_visible(adapter_harness):
    """A missing analyzer is NOT_AVAILABLE — never PASS, never silently
    omitted."""
    state = adapter_harness.registry().execution_state(
        "ruff_not_installed"
    )
    assert state is ToolExecutionState.TOOL_NOT_INSTALLED
    assert state is not ToolExecutionState.ANALYSIS_COMPLETED


def test_every_execution_state_is_reachable(adapter_harness):
    """The exemplar exercises the full state space — the contract is
    proven against every failure mode, not just the happy path."""
    states = {
        adapter_harness.run_exemplar(mode).state for mode in MODES
    }
    assert states == {
        ToolExecutionState.ANALYSIS_COMPLETED,
        ToolExecutionState.TOOL_EXECUTION_FAILED,
        ToolExecutionState.TOOL_TIMEOUT,
        ToolExecutionState.TOOL_NOT_INSTALLED,
        ToolExecutionState.TOOL_INVALID_OUTPUT,
    }


def test_failed_tool_is_not_a_clean_result(adapter_harness):
    """Tool failure never reads as zero findings."""
    execution = adapter_harness.run_exemplar("failed")
    assert execution.state is ToolExecutionState.TOOL_EXECUTION_FAILED
    assert execution.normalized_findings == ()
    assert execution.state is not ToolExecutionState.ANALYSIS_COMPLETED


def test_normalized_findings_point_at_content_addressed_raw(
    adapter_harness,
):
    execution = adapter_harness.run_exemplar("completed")
    assert execution.raw_output_identity is not None
    assert execution.raw_output_identity == content_address(
        EXEMPLAR_SIMULATED_MODES["completed"]
    )
    for finding in execution.normalized_findings:
        assert finding.evidence_refs  # auditable to raw output
        assert finding.evidence_refs[0] in {
            content_address(item)
            for item in EXEMPLAR_SIMULATED_MODES["completed"]["findings"]
        }


def test_normalization_is_structural_not_semantic(adapter_harness):
    """The adapter translates categories, never architectural meaning."""
    src = inspect.getsource(ExemplarToolAdapter.normalize).lower()
    assert "architectural_violation" not in src
    assert "certif" not in src
    assert "verdict" not in src


def test_adapter_has_no_verdict_or_obligation_surface(adapter_harness):
    tree = ast.parse(inspect.getsource(ExemplarToolAdapter))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ast.unparse(node.func)
            assert "render_verdict" not in fn
            assert "decide_obligation" not in fn


def test_execution_identity_deterministic(adapter_harness):
    e1 = adapter_harness.run_exemplar("completed")
    e2 = adapter_harness.run_exemplar("completed")
    assert e1.execution_identity == e2.execution_identity
    assert e1.normalized_findings == e2.normalized_findings


def test_matrix_and_recipe_identity_unchanged(adapter_harness):
    assert adapter_harness.matrix_summary() == (12, 18, 0, 0)
    assert adapter_harness.recipe_isr_hash() == RECIPE_HASH