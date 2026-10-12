"""Fail-closed preflight for the blind TaskFlow native generation trial."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from provider_free.native_adapter import adapt_taskflow_snapshot
from provider_free.semantic_source_audit import build_source_audit
from tiannara.domain.models.semantic_resolution import (
    UnresolvedSemanticsError,
    require_taskflow_semantics,
)

ROOT = Path(__file__).resolve().parents[3]
TRIAL = ROOT / "experiments" / "taskflow-native"


def build_report() -> dict:
    problem = (TRIAL / "PROBLEM.md").read_text(encoding="utf-8")
    acceptance_path = ROOT / "golden-projects" / "taskflow" / "ACCEPTANCE.json"
    acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
    source_audit = build_source_audit()
    adapted = adapt_taskflow_snapshot(
        problem,
        acceptance,
        problem_source="snapshot:experiments/taskflow-native/PROBLEM.md",
        acceptance_source="snapshot:golden-projects/taskflow/ACCEPTANCE.json",
    )
    try:
        require_taskflow_semantics(adapted.graph, adapted.semantic_resolutions)
    except UnresolvedSemanticsError as exc:
        return {
            "schema": "tiannara.taskflow.native-trial-preflight.v1",
            "trial_id": "TASKFLOW-ESAP-NATIVE-001",
            "status": "BLOCKED",
            "phase": "semantic_preflight",
            "problem_sha256": adapted.problem_sha256,
            "acceptance_sha256": adapted.acceptance_sha256,
            "requirement_graph_id": adapted.graph.graph_id,
            "requirement_graph_sha256": adapted.graph.content_hash(),
            "semantic_resolution_record": adapted.semantic_resolutions.model_dump(mode="json"),
        "semantic_source_audit": source_audit,
            "semantic_source_audit": source_audit,
            "unresolved_mandatory_semantics": list(exc.fields),
            "generation_started": False,
            "system_model_constructed": False,
            "typed_isr_constructed": False,
            "backend_selected": False,
            "application_generated": False,
            "runtime_verified": False,
            "certified": False,
            "blockers": [
                str(exc),
                "No trusted native semantic resolver or verified human-decision record is configured.",
                "Source strings and approval references alone are not trusted evidence.",
            ],
        }
    return {
        "schema": "tiannara.taskflow.native-trial-preflight.v1",
        "trial_id": "TASKFLOW-ESAP-NATIVE-001",
        "status": "BLOCKED",
        "phase": "trusted_evidence_verification",
        "problem_sha256": adapted.problem_sha256,
        "acceptance_sha256": adapted.acceptance_sha256,
        "requirement_graph_id": adapted.graph.graph_id,
        "requirement_graph_sha256": adapted.graph.content_hash(),
        "semantic_resolution_record": adapted.semantic_resolutions.model_dump(mode="json"),
        "unresolved_mandatory_semantics": [],
        "generation_started": False,
        "system_model_constructed": False,
        "typed_isr_constructed": False,
        "backend_selected": False,
        "application_generated": False,
        "runtime_verified": False,
        "certified": False,
        "blockers": [
            "Semantic ledger is structurally complete, but trusted evidence verification is not implemented.",
            "Generation is blocked until trusted resolution evidence can be verified.",
        ],
    }


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
