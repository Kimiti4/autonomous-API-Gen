"""Bounded live TaskFlow attempt consuming only immutable snapshot inputs.

This runner deliberately uses ESAP's existing LanguageModelProvider, typed ISR,
capability derivation, compiler registry, and selector contracts. It does not
import the retired PR #73 runner or its contract schema.

Exit codes: 0 = full path completed (not automatically certified), 2 = BLOCKED,
1 = FAIL. A blocked/failed attempt is written to the evidence directory.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
TRIAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TRIAL_DIR))

from snapshot_consumer import SnapshotConsumptionError, load_snapshot_inputs  # noqa: E402


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _base_record(verdict: str, reason: str, started: str) -> dict[str, Any]:
    return {
        "schema": "tiannara.taskflow-live-attempt.v1",
        "trial_id": "TASKFLOW-ESAP-NATIVE-001",
        "verdict": verdict,
        "reason": reason,
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "generation_mode": "live-only",
        "certified": False,
        "evidence": [],
    }


def run(evidence_dir: Path, timeout_seconds: int) -> int:
    started = datetime.now(timezone.utc).isoformat()
    evidence_dir = evidence_dir.resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    report_path = evidence_dir / "live-attempt.json"

    try:
        snapshot = load_snapshot_inputs(evidence_dir)
    except (SnapshotConsumptionError, OSError) as exc:
        _write_json(report_path, _base_record("FAIL", f"snapshot_invalid:{type(exc).__name__}", started))
        return 1

    inputs = snapshot["inputs"]
    problem_key = "experiments/taskflow-native/PROBLEM.md"
    acceptance_key = "golden-projects/taskflow/ACCEPTANCE.json"
    if problem_key not in inputs or acceptance_key not in inputs:
        _write_json(report_path, _base_record("FAIL", "snapshot_missing_canonical_input", started))
        return 1

    base_url = os.environ.get("TIANNARA_LLM_BASE_URL", "").strip()
    model_id = os.environ.get("TIANNARA_LLM_MODEL", "").strip()
    if not base_url or not model_id:
        report = _base_record(
            "BLOCKED",
            "live_provider_not_configured: set TIANNARA_LLM_BASE_URL and TIANNARA_LLM_MODEL; replay is prohibited",
            started,
        )
        report["snapshot_contract_sha256"] = snapshot["contract_sha256"]
        report["snapshot_input_sha256"] = {
            name: __import__("hashlib").sha256(path.read_bytes()).hexdigest()
            for name, path in inputs.items()
        }
        _write_json(report_path, report)
        return 2

    from tiannara.application.compiler.composition import build_compiler_registry
    from tiannara.application.compiler.derivation import derive_compilation_requirements
    from tiannara.application.compiler.selector import plan_compilation
    from tiannara.application.intent.compiler import IntentCompiler
    from tiannara.application.intent.config import IntentCompilerConfig
    from tiannara.domain.models.backend_declaration import BackendSelectionError
    from tiannara.infrastructure.llm.openai_compatible_provider import OpenAICompatibleProvider

    problem = inputs[problem_key].read_text(encoding="utf-8")
    acceptance = json.loads(inputs[acceptance_key].read_text(encoding="utf-8"))
    statement = (
        problem
        + "\n\nAcceptance contract (authoritative; implement required scope only):\n"
        + json.dumps(acceptance, sort_keys=True, indent=2)
    )
    provider = OpenAICompatibleProvider(
        base_url=base_url,
        model_id=model_id,
        api_key=os.environ.get("TIANNARA_LLM_API_KEY") or None,
        timeout_seconds=timeout_seconds,
    )
    report = _base_record("FAIL", "attempt_started", started)
    report["snapshot_contract_sha256"] = snapshot["contract_sha256"]
    report["snapshot_input_sha256"] = {
        name: __import__("hashlib").sha256(path.read_bytes()).hexdigest()
        for name, path in inputs.items()
    }
    report["provider"] = {"model_id": model_id, "base_url": base_url, "timeout_seconds": timeout_seconds}
    try:
        compiled = IntentCompiler(
            provider,
            config=IntentCompilerConfig(model_id=model_id, max_repair_iterations=2),
        ).compile_full(statement, "TASKFLOW-ESAP-NATIVE-001")
        if not compiled.call_records or any(getattr(r.status, "value", r.status) != "live" for r in compiled.call_records):
            raise RuntimeError("live_provenance_gate_failed")
        isr_path = evidence_dir / "generated_isr.json"
        _write_json(isr_path, compiled.isr.model_dump(mode="json"))
        graph_path = evidence_dir / "requirement_graph.json"
        _write_json(graph_path, compiled.requirement_graph.model_dump(mode="json"))
        calls_path = evidence_dir / "model_calls.json"
        _write_json(calls_path, [record.model_dump(mode="json") for record in compiled.call_records])
        report["evidence"].extend([isr_path.name, graph_path.name, calls_path.name])
        report["isr_sha256"] = compiled.isr.content_hash()
        report["model_call_count"] = len(compiled.call_records)
        report["all_model_calls_live"] = True

        model = compiled.isr.system_model()
        if model is None:
            raise RuntimeError("typed_isr_missing")
        requirements = derive_compilation_requirements(model)
        report["derived_requirements"] = [
            {
                "artifact_kind": requirement.artifact_kind.value,
                "required_capabilities": [cap.value for cap in requirement.required_capabilities],
                "subject_ref": requirement.subject_ref,
            }
            for requirement in requirements
        ]
        registry = build_compiler_registry()
        try:
            plan = plan_compilation(registry, requirements)
        except Exception as exc:
            report["verdict"] = "BLOCKED"
            report["reason"] = f"compiler_capability_gap:{type(exc).__name__}"
            report["compiler_error"] = str(exc)
            report["finished_at"] = datetime.now(timezone.utc).isoformat()
            report["certified"] = False
            _write_json(report_path, report)
            return 2
        report["plan_id"] = plan.plan_id
        report["selected_backends"] = [item.backend_id for item in plan.planned]
        report["verdict"] = "BLOCKED"
        report["reason"] = "compiler_execution_and_runtime_gates_not_yet_connected_to_this_trial_runner"
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["certified"] = False
        _write_json(report_path, report)
        return 2
    except Exception as exc:
        report["verdict"] = "FAIL"
        report["reason"] = f"live_attempt_failed:{type(exc).__name__}"
        report["diagnostic"] = str(exc)[:1000]
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        _write_json(report_path, report)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", default=str(TRIAL_DIR / "out" / "evidence"))
    parser.add_argument("--timeout-seconds", type=int, default=90)
    args = parser.parse_args()
    if not 1 <= args.timeout_seconds <= 180:
        parser.error("--timeout-seconds must be between 1 and 180")
    return run(Path(args.evidence_dir), args.timeout_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
