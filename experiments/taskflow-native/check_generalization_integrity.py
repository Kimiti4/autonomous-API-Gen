"""Fail-closed generalization and blind-input integrity gate.

The native TaskFlow trial is not evidence of autonomous specification
interpretation while task-specific elicitation/extraction payloads are embedded
in the runner. This gate records the limitation rather than silently certifying
the capability. It also requires a second, distinct specification and an
enforced source boundary before generalization can be certified.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

TRIAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = TRIAL_DIR.parents[1]
RUNNER = TRIAL_DIR / "run_trial.py"
CONTRACT = TRIAL_DIR / "TRIAL_CONTRACT.json"
REPORT = TRIAL_DIR / "out" / "evidence" / "generalization_integrity.json"


def check_runner_ast(path: Path) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        return False, [f"runner cannot be inspected: {exc}"]

    assigned = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id in {"ELICITATION", "EXTRACTION"}:
                    assigned.add(target.id)
    if "ELICITATION" in assigned:
        reasons.append("runner embeds a task-specific ELICITATION payload")
    if "EXTRACTION" in assigned:
        reasons.append("runner embeds a task-specific EXTRACTION/requirement graph")

    source = path.read_text(encoding="utf-8")
    if "OllamaModelProvider" not in source or "RecordingModelProvider" not in source:
        reasons.append(
            "runner does not use a live structured provider and record its actual output"
        )
    if "_record(build_elicitation_request" in source or "_record(build_extraction_request" in source:
        reasons.append("runner still seeds task-specific elicitation/extraction answers")
    return not reasons, reasons


def main() -> int:
    reasons: list[str] = []
    checks: list[dict] = []

    runner_ok, runner_reasons = check_runner_ast(RUNNER)
    checks.append({
        "id": "independent-interpretation",
        "status": "PASS" if runner_ok else "BLOCKED",
        "detail": runner_reasons,
    })
    reasons.extend(runner_reasons)

    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        inputs = contract.get("inputs", {})
        problem_inputs = [
            spec.get("path", "")
            for name, spec in inputs.items()
            if name == "problem"
        ]
        distinct_specs = contract.get("generalization_specs", [])
        has_second_spec = bool(distinct_specs) and len(set(problem_inputs + distinct_specs)) >= 2
    except (OSError, ValueError) as exc:
        contract = {}
        has_second_spec = False
        reasons.append(f"contract could not be inspected: {exc}")

    second_run_path = TRIAL_DIR / "out" / "evidence" / "generalization_runs.json"
    second_run_ok = False
    second_run_detail = []
    if not has_second_spec:
        second_run_detail.append(
            "contract does not define a second distinct specification for a generalization trial"
        )
    else:
        try:
            run_evidence = json.loads(second_run_path.read_text(encoding="utf-8"))
            second_run_ok = any(
                item.get("spec_path") in distinct_specs and item.get("completed") is True
                for item in run_evidence.get("runs", [])
            )
        except (OSError, ValueError):
            second_run_ok = False
        if not second_run_ok:
            second_run_detail.append(
                "no successful second-spec generation and verification evidence exists"
            )
    checks.append({
        "id": "distinct-specification",
        "status": "PASS" if has_second_spec and second_run_ok else "BLOCKED",
        "detail": second_run_detail,
    })
    if not has_second_spec or not second_run_ok:
        reasons.extend(second_run_detail)

    forbidden = contract.get("forbidden", [])
    present_forbidden = []
    for entry in forbidden:
        candidate = (REPO_ROOT / entry).resolve()
        if candidate.exists():
            present_forbidden.append(entry)
    boundary_ok = not present_forbidden and (REPO_ROOT / ".git").exists() is False
    boundary_detail = []
    if present_forbidden:
        boundary_detail.append(
            "forbidden golden inputs remain in the checked-out workspace: "
            + ", ".join(present_forbidden)
        )
    if (REPO_ROOT / ".git").exists():
        boundary_detail.append(
            "repository metadata is present in the trial workspace; static input pins "
            "do not enforce a read boundary"
        )
    checks.append({
        "id": "enforced-blind-input-boundary",
        "status": "PASS" if boundary_ok else "BLOCKED",
        "detail": boundary_detail,
    })
    if not boundary_ok:
        reasons.extend(boundary_detail)

    verdict = "PASS" if not reasons else "BLOCKED"
    payload = {
        "schema": "tiannara.generalization-integrity.v1",
        "verdict": verdict,
        "certification_scope": (
            "independent specification interpretation and blind-input isolation"
        ),
        "checks": checks,
        "limitations": reasons,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"generalization-integrity: {verdict}")
    for check in checks:
        print(f"  [{check['status']}] {check['id']}")
        for detail in check["detail"]:
            print(f"    - {detail}")
    # This is a certification gate, so BLOCKED must fail CI rather than look green.
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
