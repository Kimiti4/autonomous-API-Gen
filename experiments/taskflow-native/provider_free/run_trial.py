"""Fail-closed preflight for the blind TaskFlow native generation trial."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from provider_free.native_adapter import adapt_taskflow_snapshot
from provider_free.semantic_source_audit import build_source_audit
from provider_free.trusted_evidence import canonical_json, verify_trusted_resolution_envelope
from tiannara.domain.models.semantic_resolution import (
    UnresolvedSemanticsError,
    SemanticResolutionRecord,
    require_taskflow_semantics,
)

ROOT = Path(__file__).resolve().parents[3]
TRIAL = ROOT / "experiments" / "taskflow-native"


def _base_report(adapted, record: SemanticResolutionRecord, source_audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "tiannara.taskflow.native-trial-preflight.v1",
        "trial_id": "TASKFLOW-ESAP-NATIVE-001",
        "problem_sha256": adapted.problem_sha256,
        "acceptance_sha256": adapted.acceptance_sha256,
        "requirement_graph_id": adapted.graph.graph_id,
        "requirement_graph_sha256": adapted.graph.content_hash(),
        "semantic_resolution_record": record.model_dump(mode="json"),
        "semantic_source_audit": source_audit,
        "generation_started": False,
        "system_model_constructed": False,
        "typed_isr_constructed": False,
        "backend_selected": False,
        "application_generated": False,
        "runtime_verified": False,
        "certified": False,
    }


def build_report() -> dict:
    problem_path = TRIAL / "PROBLEM.md"
    acceptance_path = ROOT / "golden-projects" / "taskflow" / "ACCEPTANCE.json"
    problem_bytes = problem_path.read_bytes()
    acceptance_file_bytes = acceptance_path.read_bytes()
    problem = problem_bytes.decode("utf-8")
    acceptance = json.loads(acceptance_file_bytes.decode("utf-8"))
    source_audit = build_source_audit()
    adapted = adapt_taskflow_snapshot(
        problem,
        acceptance,
        problem_source="snapshot:experiments/taskflow-native/PROBLEM.md",
        acceptance_source="snapshot:golden-projects/taskflow/ACCEPTANCE.json",
    )
    record_path = os.environ.get("TIANNARA_TASKFLOW_RESOLUTION_RECORD")
    record = adapted.semantic_resolutions
    record_load_error = None
    if record_path:
        try:
            record = SemanticResolutionRecord.model_validate_json(
                Path(record_path).read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as exc:
            record_load_error = f"Unable to load semantic resolution record: {exc}"
    report = _base_report(adapted, record, source_audit)
    try:
        if record_load_error:
            raise ValueError(record_load_error)
        require_taskflow_semantics(adapted.graph, record)
    except (UnresolvedSemanticsError, ValueError) as exc:
        report.update({
            "status": "BLOCKED",
            "phase": "semantic_preflight",
            "unresolved_mandatory_semantics": list(exc.fields) if isinstance(exc, UnresolvedSemanticsError) else list(record.unresolved_fields()),
            "blockers": [
                str(exc),
                "Supply a complete graph-bound record through TIANNARA_TASKFLOW_RESOLUTION_RECORD only after trusted review.",
                "Source strings and approval references alone are not trusted evidence.",
            ],
        })
        return report

    envelope_path_value = os.environ.get("TIANNARA_TASKFLOW_EVIDENCE_ENVELOPE")
    envelope = None
    envelope_errors = []
    if envelope_path_value:
        try:
            envelope = json.loads(Path(envelope_path_value).read_text(encoding="utf-8"))
            if not isinstance(envelope, dict):
                envelope_errors.append("Trusted resolution envelope must be a JSON object.")
                envelope = None
        except (OSError, json.JSONDecodeError) as exc:
            envelope_errors.append(f"Unable to load trusted resolution envelope: {exc}")
    key_text = os.environ.get("TIANNARA_TASKFLOW_TRUSTED_EVIDENCE_KEY")
    trusted_key = key_text.encode("utf-8") if key_text else None
    verified, evidence_blockers = verify_trusted_resolution_envelope(
        record=record,
        graph=adapted.graph,
        problem_bytes=problem_bytes,
        acceptance_bytes=canonical_json(acceptance),
        envelope=envelope,
        trusted_key=trusted_key,
    )
    if envelope_errors:
        verified = False
        evidence_blockers = tuple(evidence_blockers) + tuple(envelope_errors)

    if not verified:
        report.update({
            "status": "BLOCKED",
            "phase": "trusted_evidence_verification",
            "unresolved_mandatory_semantics": [],
            "trusted_evidence_verified": False,
            "blockers": list(evidence_blockers),
        })
        return report

    report.update({
        "status": "BLOCKED",
        "phase": "compiler_integration",
        "unresolved_mandatory_semantics": [],
        "trusted_evidence_verified": True,
        "trusted_evidence_signer": envelope.get("signer_id") if envelope else None,
        "blockers": [
            "Trusted resolution envelope verified for the current graph, snapshots, and exact resolution ledger.",
            "Generation remains blocked: the verified evidence path is not yet wired to the live ProjectCompiler trial orchestrator.",
            "Application generation, runtime verification, and certification have not occurred.",
        ],
    })
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
