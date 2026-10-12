from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TRIAL_DIR = ROOT / "experiments" / "taskflow-native"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TRIAL_DIR))

from provider_free.run_trial import build_report  # noqa: E402


def test_trial_runner_records_blocked_preflight_without_claiming_generation():
    report = build_report()

    assert report["schema"] == "tiannara.taskflow.native-trial-preflight.v1"
    assert report["trial_id"] == "TASKFLOW-ESAP-NATIVE-001"
    assert report["status"] == "BLOCKED"
    assert report["generation_started"] is False
    assert report["system_model_constructed"] is False
    assert report["typed_isr_constructed"] is False
    assert report["backend_selected"] is False
    assert report["application_generated"] is False
    assert report["runtime_verified"] is False
    assert report["certified"] is False
    assert len(report["unresolved_mandatory_semantics"]) == 15
    assert report["semantic_resolution_record"]["graph_hash"] == report["requirement_graph_sha256"]


def test_trial_runner_does_not_treat_a_structurally_complete_ledger_as_trusted_evidence(monkeypatch):
    from provider_free import run_trial
    from tiannara.domain.models.semantic_resolution import (
        SemanticResolution,
        SemanticResolutionRecord,
        ResolutionKind,
        TASKFLOW_MANDATORY_FIELDS,
    )

    original = run_trial.adapt_taskflow_snapshot

    def complete_but_untrusted(*args, **kwargs):
        result = original(*args, **kwargs)
        ledger = SemanticResolutionRecord(
            graph_id=result.graph.graph_id,
            graph_hash=result.graph.content_hash(),
            required_fields=TASKFLOW_MANDATORY_FIELDS,
            resolutions=tuple(
                SemanticResolution(
                    field_path=field,
                    kind=ResolutionKind.SNAPSHOT,
                    value="caller-asserted-value",
                    source="unverified:caller",
                )
                for field in TASKFLOW_MANDATORY_FIELDS
            ),
        )
        return replace(result, semantic_resolutions=ledger)

    monkeypatch.setattr(run_trial, "adapt_taskflow_snapshot", complete_but_untrusted)
    report = run_trial.build_report()

    assert report["status"] == "BLOCKED"
    assert report["phase"] == "trusted_evidence_verification"
    assert report["generation_started"] is False
    assert report["certified"] is False
    assert report["unresolved_mandatory_semantics"] == []
    assert any("trusted evidence verification" in item for item in report["blockers"])
