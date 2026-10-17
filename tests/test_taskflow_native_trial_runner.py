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
    assert report["semantic_source_audit"]["summary"]["mandatory_fields"] == 15
    assert report["semantic_source_audit"]["summary"]["resolved_fields"] == 0
    assert report["semantic_source_audit"]["generation_authorized"] is False


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
    assert report["semantic_source_audit"]["summary"]["resolved_fields"] == 0
    assert any("No trusted resolution envelope" in item for item in report["blockers"])
    assert any("No out-of-repository trusted evidence key" in item for item in report["blockers"])
    assert report["trusted_evidence_verified"] is False



def test_trial_runner_loads_external_ledger_but_still_requires_trusted_envelope(monkeypatch, tmp_path):
    import json
    from provider_free import run_trial
    from tiannara.domain.models.semantic_resolution import (
        SemanticResolution,
        SemanticResolutionRecord,
        ResolutionKind,
        TASKFLOW_MANDATORY_FIELDS,
    )

    problem = (TRIAL_DIR / "PROBLEM.md").read_text(encoding="utf-8")
    acceptance = json.loads((ROOT / "golden-projects" / "taskflow" / "ACCEPTANCE.json").read_text(encoding="utf-8"))
    adapted = run_trial.adapt_taskflow_snapshot(
        problem,
        acceptance,
        problem_source="snapshot:experiments/taskflow-native/PROBLEM.md",
        acceptance_source="snapshot:golden-projects/taskflow/ACCEPTANCE.json",
    )
    ledger = SemanticResolutionRecord(
        graph_id=adapted.graph.graph_id,
        graph_hash=adapted.graph.content_hash(),
        required_fields=TASKFLOW_MANDATORY_FIELDS,
        resolutions=tuple(
            SemanticResolution(
                field_path=field,
                kind=ResolutionKind.SNAPSHOT,
                value={"reviewed": True, "field": field},
                source="reviewer-reviewed-snapshot",
            )
            for field in TASKFLOW_MANDATORY_FIELDS
        ),
    )
    ledger_path = tmp_path / "resolution.json"
    ledger_path.write_text(ledger.model_dump_json(), encoding="utf-8")
    monkeypatch.setenv("TIANNARA_TASKFLOW_RESOLUTION_RECORD", str(ledger_path))
    monkeypatch.delenv("TIANNARA_TASKFLOW_EVIDENCE_ENVELOPE", raising=False)
    monkeypatch.delenv("TIANNARA_TASKFLOW_TRUSTED_EVIDENCE_KEY", raising=False)

    report = run_trial.build_report()

    assert report["status"] == "BLOCKED"
    assert report["phase"] == "trusted_evidence_verification"
    assert report["semantic_resolution_record"]["graph_hash"] == report["requirement_graph_sha256"]
    assert report["trusted_evidence_verified"] is False
    assert any("No trusted resolution envelope" in item for item in report["blockers"])

def test_payload_preflight_still_blocks_before_live_compiler_consumption(monkeypatch, tmp_path):
    import json
    from provider_free import run_trial
    from tiannara.domain.models.semantic_resolution import (
        SemanticResolution,
        SemanticResolutionRecord,
        ResolutionKind,
        TASKFLOW_MANDATORY_FIELDS,
    )
    from tiannara.domain.models.taskflow_semantic_contract import REQUIRED_VALUE_KEYS

    original = run_trial.adapt_taskflow_snapshot

    def structurally_complete_fixture(*args, **kwargs):
        adapted = original(*args, **kwargs)
        ledger = SemanticResolutionRecord(
            graph_id=adapted.graph.graph_id,
            graph_hash=adapted.graph.content_hash(),
            required_fields=TASKFLOW_MANDATORY_FIELDS,
            resolutions=tuple(
                SemanticResolution(
                    field_path=field,
                    kind=ResolutionKind.SNAPSHOT,
                    value={key: {"decision": "reviewed-fixture"} for key in REQUIRED_VALUE_KEYS[field]},
                    source="test-fixture-only",
                )
                for field in TASKFLOW_MANDATORY_FIELDS
            ),
        )
        return replace(adapted, semantic_resolutions=ledger)

    monkeypatch.setattr(run_trial, "adapt_taskflow_snapshot", structurally_complete_fixture)
    # Unit-test-only bypass to exercise the post-authentication integration boundary.
    # This does not create or verify production trusted evidence.
    monkeypatch.setattr(run_trial, "verify_trusted_resolution_envelope", lambda **kwargs: (True, ()))
    record_path = tmp_path / "resolution.json"
    envelope_path = tmp_path / "envelope.json"
    # The adapter fixture supplies the same deterministic graph binding used by the runner.
    adapted = structurally_complete_fixture(
        (run_trial.TRIAL / "PROBLEM.md").read_text(encoding="utf-8"),
        json.loads((run_trial.ROOT / "golden-projects" / "taskflow" / "ACCEPTANCE.json").read_text(encoding="utf-8")),
        problem_source="snapshot:experiments/taskflow-native/PROBLEM.md",
        acceptance_source="snapshot:golden-projects/taskflow/ACCEPTANCE.json",
    )
    record_path.write_text(adapted.semantic_resolutions.model_dump_json(), encoding="utf-8")
    envelope_path.write_text(json.dumps({"signer_id": "test-fixture-only"}), encoding="utf-8")
    monkeypatch.setenv("TIANNARA_TASKFLOW_RESOLUTION_RECORD", str(record_path))
    monkeypatch.setenv("TIANNARA_TASKFLOW_EVIDENCE_ENVELOPE", str(envelope_path))
    monkeypatch.setenv("TIANNARA_TASKFLOW_TRUSTED_EVIDENCE_KEY", "test-fixture-only-key")

    report = run_trial.build_report()

    assert report["status"] == "BLOCKED"
    assert report["phase"] == "compiler_integration"
    assert report["semantic_payload_validated"] is True
    assert report["trusted_payload_consumed_by_project_compiler"] is False
    assert report["semantic_consumer_bindings_verified"] is False
    assert report["backend_selection_attempted"] is False
    assert report["generation_started"] is False
    assert report["application_generated"] is False
    assert report["certified"] is False

