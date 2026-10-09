"""Three-state generalization and blind-input integrity gate.

Certifies that a *second*, distinct natural-language specification was
independently interpreted and executed through the same isolated pipeline
as the first trial. The gate never reports a binary pass/fail: it emits
exactly one verdict with honest semantics:

  * ``PASS``    -- every check passed: both trials ran to completion, the
    generation boundary held for both, the second specification is
    demonstrably distinct in input *and* interpreted output, its oracle
    never entered a generation workspace, and its acceptance flow executed
    live HTTP calls against the generated service;
  * ``BLOCKED`` -- a precondition is missing (evidence absent because a
    trial never ran, or configuration is incomplete). Not a certification;
  * ``FAIL``    -- evidence exists but integrity is violated: fabrication
    markers in the runner, isolation denials, oracle material inside a
    workspace, contract pin drift, identical output across specifications,
    or acceptance criteria declared but not executed.

Exit codes: 0 PASS, 1 FAIL, 2 BLOCKED. CI must fail on anything but PASS.
"""
from __future__ import annotations

import ast
import hashlib
import json
import time
from pathlib import Path

TRIAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = TRIAL_DIR.parents[1]
TRIAL1 = TRIAL_DIR
TRIAL2 = REPO_ROOT / "experiments" / "spec2-expensel"
REPORT = TRIAL_DIR / "out" / "evidence" / "generalization_integrity.json"

RUNNER_FILES = ("run_trial.py", "generationlib.py", "isolated_generation.py")
FABRICATION_ASSIGN_NAMES = frozenset(
    {"ELICITATION", "EXTRACTION", "SEED_TRANSCRIPT", "RECORDED_TRANSCRIPT"}
)
FABRICATION_SOURCE_MARKERS = (
    "seed_transcript",
    "RecordedModelProvider",
    "ScriptedModelProvider",
    "ReplayModelProvider",
    "CannedModelProvider",
)
HELD_OUT_NAME_MARKERS = ("acceptance.json", "trial_hooks.py")
MIN_ACCEPTANCE_IDS = 10


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _evidence_dir(trial_dir: Path) -> Path:
    contract = _load_json(trial_dir / "TRIAL_CONTRACT.json") or {}
    return trial_dir / contract.get("evidence_dir", "out/evidence")


def _check(check_id: str, status: str, detail: list[str]) -> dict:
    return {"id": check_id, "status": status, "detail": detail}


def _acceptance_ids(trial_dir: Path) -> list[str] | None:
    contract = _load_json(trial_dir / "TRIAL_CONTRACT.json")
    if contract is None:
        return None
    spec = contract.get("inputs", {}).get("acceptance", {})
    acceptance = _load_json((trial_dir / spec.get("path", "")).resolve())
    if acceptance is None:
        return None
    entries = acceptance.get("acceptance_criteria", [])
    ids = [entry.get("id", "") for entry in entries]
    return ids if ids and all(ids) else None


def check_runner_independence(harness_dir: Path) -> dict:
    reasons: list[str] = []
    missing: list[str] = []
    for name in RUNNER_FILES:
        path = harness_dir / name
        if not path.is_file():
            missing.append(name)
            continue
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            reasons.append(f"{name} cannot be inspected: {exc}")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
            for target in targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id in FABRICATION_ASSIGN_NAMES
                ):
                    reasons.append(
                        f"{name} embeds a fixture payload assigned to {target.id}"
                    )
        for marker in FABRICATION_SOURCE_MARKERS:
            if marker in source:
                reasons.append(f"{name} references recorded-response provider {marker!r}")
    if reasons:
        return _check("runner-independent-interpretation", "FAIL", reasons)
    if missing:
        return _check(
            "runner-independent-interpretation",
            "BLOCKED",
            [f"runner file missing: {name}" for name in missing],
        )
    return _check("runner-independent-interpretation", "PASS", [])


def check_distinct_specification(trial1: Path, trial2: Path) -> dict:
    statements = []
    for trial_dir in (trial1, trial2):
        path = trial_dir / "PROBLEM.md"
        if not path.is_file():
            return _check(
                "distinct-specification",
                "BLOCKED",
                [f"{trial_dir.name}/PROBLEM.md missing"],
            )
        statements.append(_sha256(path))
    if statements[0] == statements[1]:
        return _check(
            "distinct-specification",
            "FAIL",
            ["both trials pin byte-identical problem statements"],
        )

    isr_hashes = []
    for trial_dir in (trial1, trial2):
        graph = _load_json(_evidence_dir(trial_dir) / "isr_graph.json")
        if graph is None or not graph.get("isr_hash"):
            return _check(
                "distinct-specification",
                "BLOCKED",
                [f"{trial_dir.name} has not produced interpreted graph evidence"],
            )
        isr_hashes.append(graph["isr_hash"])
    if isr_hashes[0] == isr_hashes[1]:
        return _check(
            "distinct-specification",
            "FAIL",
            [
                "distinct statements produced identical ISR hashes "
                f"({isr_hashes[0]}); output was not derived from each statement"
            ],
        )
    return _check(
        "distinct-specification",
        "PASS",
        [f"distinct statements and ISR graphs ({isr_hashes[0]} vs {isr_hashes[1]})"],
    )


def _trial_execution(trial_dir: Path) -> list[str]:
    reasons: list[str] = []
    evidence = _evidence_dir(trial_dir)
    run_results = _load_json(evidence / "run_results.json")
    if run_results is None:
        return [f"{trial_dir.name}: run_results.json missing (trial never ran)"]
    if run_results.get("completed") is not True:
        reasons.append(f"{trial_dir.name}: trial did not complete")

    factory = _load_json(evidence / "factory_summary.json")
    if factory is None:
        reasons.append(f"{trial_dir.name}: factory_summary.json missing")
    elif factory.get("ok") is not True:
        reasons.append(f"{trial_dir.name}: factory stage not ok")

    ids = _acceptance_ids(trial_dir)
    if ids is None:
        reasons.append(f"{trial_dir.name}: acceptance oracle unreadable")
    elif len(ids) < MIN_ACCEPTANCE_IDS:
        reasons.append(
            f"{trial_dir.name}: acceptance oracle declares {len(ids)} criteria "
            f"(minimum {MIN_ACCEPTANCE_IDS})"
        )
    e2e = _load_json(evidence / "e2e_results.json")
    if e2e is None:
        reasons.append(f"{trial_dir.name}: e2e_results.json missing")
    else:
        acs = e2e.get("acs") or {}
        if e2e.get("reachable") is not True:
            reasons.append(f"{trial_dir.name}: generated service not reachable")
        if ids:
            missing = sorted(set(ids) - set(acs))
            if missing:
                reasons.append(
                    f"{trial_dir.name}: acceptance criteria without execution "
                    "evidence: " + ", ".join(missing)
                )
        for ac_id in sorted(acs):
            entry = acs[ac_id] or {}
            if entry.get("passed") is not True:
                reasons.append(f"{trial_dir.name}: {ac_id} did not pass")
            if not isinstance(entry.get("http_status"), int):
                reasons.append(
                    f"{trial_dir.name}: {ac_id} has no executed HTTP status"
                )
    return reasons


def check_trial_execution(trial1: Path, trial2: Path) -> dict:
    reasons = _trial_execution(trial1) + _trial_execution(trial2)
    never_ran = any("never ran" in reason for reason in reasons)
    if not reasons:
        return _check("trial-execution", "PASS", [])
    if never_ran and all(
        "never ran" in reason or "missing" in reason for reason in reasons
    ):
        return _check("trial-execution", "BLOCKED", reasons)
    return _check("trial-execution", "FAIL", reasons)


def _boundary_reasons(trial_dir: Path) -> list[str]:
    reasons: list[str] = []
    isolation = _load_json(_evidence_dir(trial_dir) / "isolation.json")
    if isolation is None:
        return [f"{trial_dir.name}: isolation.json missing (trial never ran)"]
    if isolation.get("violations"):
        reasons.append(
            f"{trial_dir.name}: workspace violations "
            + ", ".join(isolation["violations"])
        )
    denied_count = isolation.get("denied_count")
    if denied_count != 0:
        reasons.append(
            f"{trial_dir.name}: boundary denials recorded: {denied_count!r}"
        )
    spawn_exit = (isolation.get("spawn") or {}).get("exit_code")
    if spawn_exit not in (0, 1):
        reasons.append(
            f"{trial_dir.name}: generation child exited abnormally: {spawn_exit!r}"
        )
    manifest = isolation.get("workspace") or {}
    for rel in manifest.get("files", {}):
        parts = rel.lower().split("/")
        name = parts[-1]
        if (
            ".git" in parts
            or "golden-projects" in parts
            or name.startswith("oracle")
        ):
            reasons.append(
                f"{trial_dir.name}: forbidden workspace entry {rel}"
            )
    return reasons


def check_generation_boundary(trial1: Path, trial2: Path) -> dict:
    reasons = _boundary_reasons(trial1) + _boundary_reasons(trial2)
    if not reasons:
        return _check("generation-boundary", "PASS", [])
    if all("missing" in reason for reason in reasons):
        return _check("generation-boundary", "BLOCKED", reasons)
    return _check("generation-boundary", "FAIL", reasons)


def _held_out_reasons(trial_dir: Path) -> list[str]:
    reasons: list[str] = []
    contract = _load_json(trial_dir / "TRIAL_CONTRACT.json")
    if contract is None:
        return [f"{trial_dir.name}: TRIAL_CONTRACT.json missing"]
    for name, spec in contract.get("inputs", {}).items():
        path = (trial_dir / spec.get("path", "")).resolve()
        if not path.is_file():
            reasons.append(f"{trial_dir.name}: pinned input {name} missing")
        elif _sha256(path) != spec.get("sha256"):
            reasons.append(
                f"{trial_dir.name}: contract pin drift for {spec.get('path')}"
            )
    manifest = (
        _load_json(_evidence_dir(trial_dir) / "isolation.json") or {}
    ).get("workspace") or {}
    if not manifest.get("files"):
        reasons.append(f"{trial_dir.name}: workspace manifest missing")
    for rel in manifest.get("files", {}):
        lowered = rel.lower()
        if any(lowered.endswith(marker) for marker in HELD_OUT_NAME_MARKERS):
            reasons.append(
                f"{trial_dir.name}: held-out oracle material inside workspace: {rel}"
            )
    return reasons


def check_pins_and_oracle_held_out(trial1: Path, trial2: Path) -> dict:
    reasons = _held_out_reasons(trial1) + _held_out_reasons(trial2)
    if not reasons:
        return _check("contract-pins-and-oracle-held-out", "PASS", [])
    hard_markers = ("pin drift", "oracle material", "forbidden workspace")
    hard = [
        reason for reason in reasons
        if any(marker in reason for marker in hard_markers)
    ]
    if hard:
        return _check("contract-pins-and-oracle-held-out", "FAIL", reasons)
    return _check("contract-pins-and-oracle-held-out", "BLOCKED", reasons)


def check_forbidden_inputs_absent(repo_root: Path, trial_dirs: list[Path]) -> dict:
    """Check forbidden paths against each trial's *generation workspace* manifest.

    The repository checkout is allowed to contain golden/oracle material for
    the independent evaluator. Looking for forbidden paths at repo_root would
    conflate evaluator visibility with generator visibility and can produce a
    false PASS when the workspace was never inspected. This check therefore
    fails closed when isolation evidence is missing.
    """
    del repo_root  # The checkout root is intentionally not the isolation boundary.
    reasons: list[str] = []
    checked = False
    blocked: list[str] = []
    for trial_dir in trial_dirs:
        contract = _load_json(trial_dir / "TRIAL_CONTRACT.json")
        if contract is None:
            blocked.append(f"{trial_dir.name}: TRIAL_CONTRACT.json missing")
            continue
        isolation = _load_json(_evidence_dir(trial_dir) / "isolation.json")
        workspace = (isolation or {}).get("workspace") or {}
        files = workspace.get("files")
        if not isinstance(files, dict):
            blocked.append(
                f"{trial_dir.name}: isolation workspace file manifest missing"
            )
            continue
        checked = True
        normalized_files = [str(name).replace("\\", "/").lstrip("./") for name in files]
        for entry in contract.get("forbidden", []):
            forbidden = str(entry).replace("\\\\", "/").lstrip("./")
            if not forbidden:
                blocked.append(f"{trial_dir.name}: empty forbidden path in contract")
                continue
            prefix = forbidden.rstrip("/")
            matches = [
                name for name in normalized_files
                if name == prefix or name.startswith(prefix + "/")
            ]
            if matches:
                reasons.append(
                    f"{trial_dir.name}: forbidden input present in generation "
                    f"workspace: {entry} (matched {matches[0]})"
                )
    if reasons:
        return _check("forbidden-inputs-absent", "FAIL", reasons)
    if blocked or not checked:
        return _check(
            "forbidden-inputs-absent",
            "BLOCKED",
            blocked or ["no trial workspace manifest could be inspected"],
        )
    return _check("forbidden-inputs-absent", "PASS", [
        "all contract-forbidden paths absent from both generation workspace manifests"
    ])


def evaluate_gate(trial1: Path, trial2: Path, repo_root: Path) -> tuple[str, list[dict]]:
    checks = [
        check_runner_independence(trial1),
        check_distinct_specification(trial1, trial2),
        check_trial_execution(trial1, trial2),
        check_generation_boundary(trial1, trial2),
        check_pins_and_oracle_held_out(trial1, trial2),
        check_forbidden_inputs_absent(repo_root, [trial1, trial2]),
    ]
    statuses = {check["status"] for check in checks}
    if "FAIL" in statuses:
        verdict = "FAIL"
    elif "BLOCKED" in statuses:
        verdict = "BLOCKED"
    else:
        verdict = "PASS"
    return verdict, checks


def main() -> int:
    verdict, checks = evaluate_gate(TRIAL1, TRIAL2, REPO_ROOT)
    limitations = [
        detail
        for check in checks
        if check["status"] != "PASS"
        for detail in check["detail"]
    ]
    payload = {
        "schema": "tiannara.generalization-integrity.v2",
        "verdict": verdict,
        "certification_scope": (
            "independent interpretation and execution of a second distinct "
            "specification under an enforced blind-input boundary"
        ),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "trials": [TRIAL1.name, TRIAL2.name],
        "checks": checks,
        "limitations": limitations,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"generalization-integrity: {verdict}")
    for check in checks:
        print(f"  [{check['status']}] {check['id']}")
        for detail in check["detail"]:
            print(f"    - {detail}")
    return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[verdict]


if __name__ == "__main__":
    raise SystemExit(main())
