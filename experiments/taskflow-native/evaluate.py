"""TASKFLOW-ESAP-NATIVE-001 evaluator -- the release gate.

Reads the trial contract, the permitted inputs, and the evidence written by
``run_trial.py``, then re-derives every claim independently:

  * rehashes the contract's SHA-256 pins over PROBLEM.md / ACCEPTANCE.json;
  * rescans PROBLEM.md against the technology denylist;
  * re-verifies the materialized manifest by hashing the files on disk;
  * cross-checks the graph-compile ISR hash against the factory's;
  * requires every required backend bundle to be static-OK, evaluated, and
    passing -- an unevaluated or missing stage is NOT a pass;
  * requires every acceptance criterion to carry a real HTTP result
    (status code + response excerpt); fabricated/simulated evidence that
    lacks those fields, or whose hashes do not match the files, fails.

Exit codes (the contract's gate semantics):
  0 = PASS, 1 = FAILED, 2 = BLOCKED (the trial never produced an output
  directory, so there is nothing to evaluate).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

TRIAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = TRIAL_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

EVIDENCE_SCHEMA = "taskflow.trial.evidence.v1"

REQUIRED_ARTIFACT_SUFFIXES = (
    "/main.py",
    "/tests/test_api.py",
    "/frontend/app.js",
    "/frontend/tests/app.test.mjs",
    "/migrations/apply.py",
    "/infra/topology.json",
    "/deploy/plan.py",
    "/docs/validate_docs.py",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scan_text_tokens(text: str) -> list[str]:
    from tiannara.domain.models.system_model import TECHNOLOGY_TOKENS

    hits = []
    for token in TECHNOLOGY_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", text, re.IGNORECASE):
            hits.append(token)
    return hits


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(trial_dir: Path) -> tuple[int, list[dict]]:
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> bool:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
        return ok

    contract_path = trial_dir / "TRIAL_CONTRACT.json"
    if not contract_path.is_file():
        check("contract-present", False, "TRIAL_CONTRACT.json missing")
        return 2, checks
    try:
        contract = _load_json(contract_path)
    except ValueError as exc:
        check("contract-present", False, f"unparseable contract: {exc}")
        return 2, checks

    out_dir = trial_dir / contract.get("output_dir", "out")
    if not out_dir.exists():
        check("trial-output-present", False, f"{out_dir.name}/ absent -- trial never ran")
        return 2, checks

    evidence_dir = trial_dir / contract.get("evidence_dir", "out/evidence")
    expected_schema = contract.get("evidence_schema", EVIDENCE_SCHEMA)

    problem_path = (trial_dir / contract["inputs"]["problem"]["path"]).resolve()
    acceptance_path = (trial_dir / contract["inputs"]["acceptance"]["path"]).resolve()

    pin_results = []
    for name, spec in contract.get("inputs", {}).items():
        path = (trial_dir / spec["path"]).resolve()
        if not path.is_file():
            pin_results.append(f"{name}: missing")
            continue
        actual = sha256_file(path)
        if actual != spec["sha256"]:
            pin_results.append(f"{name}: {actual} != {spec['sha256']}")
    check(
        "contract-pins",
        not pin_results,
        "; ".join(pin_results),
    )

    if problem_path.is_file():
        hits = scan_text_tokens(problem_path.read_text(encoding="utf-8"))
        check("problem-technology-free", not hits, f"tokens: {hits}" if hits else "")
    else:
        check("problem-technology-free", False, "PROBLEM.md missing")

    acceptance_ok = False
    acceptance_ids: list[str] = []
    if acceptance_path.is_file():
        try:
            acceptance = _load_json(acceptance_path)
            entries = acceptance.get("acceptance_criteria", [])
            acceptance_ids = [entry.get("id", "") for entry in entries]
            acceptance_ok = (
                len(entries) >= 10
                and all(
                    entry.get("id") and entry.get("statement")
                    and entry.get("evidence_key")
                    for entry in entries
                )
                and len(set(acceptance_ids)) == len(acceptance_ids)
                and all(re.fullmatch(r"AC-\d{2}", ac_id) for ac_id in acceptance_ids)
            )
        except ValueError as exc:
            checks.append(
                {"name": "acceptance-structure", "ok": False, "detail": str(exc)}
            )
        else:
            check("acceptance-structure", acceptance_ok, "")
    else:
        check("acceptance-structure", False, "ACCEPTANCE.json missing")

    def load_evidence(filename: str):
        path = evidence_dir / filename
        if not path.is_file():
            check(f"evidence:{filename}", False, "missing")
            return None
        try:
            payload = _load_json(path)
        except ValueError as exc:
            check(f"evidence:{filename}", False, f"unparseable: {exc}")
            return None
        if payload.get("evidence_schema") != expected_schema:
            check(
                f"evidence:{filename}",
                False,
                f"schema {payload.get('evidence_schema')!r} != {expected_schema!r}",
            )
            return None
        check(f"evidence:{filename}", True, "")
        return payload

    run_meta = load_evidence("run_meta.json")
    isr_graph = load_evidence("isr_graph.json")
    factory_summary = load_evidence("factory_summary.json")
    e2e_results = load_evidence("e2e_results.json")
    manifest = load_evidence("manifest.json")
    run_results = load_evidence("run_results.json")

    if run_meta is not None:
        hash_mismatches = [
            name
            for name, spec in contract.get("inputs", {}).items()
            if run_meta.get("permitted_input_hashes", {}).get(name)
            != spec["sha256"]
        ]
        check(
            "run-meta-input-hashes",
            not hash_mismatches,
            f"mismatched: {hash_mismatches}" if hash_mismatches else "",
        )
        check(
            "run-meta-contract-hash",
            run_meta.get("contract_sha256") == sha256_file(contract_path),
            "contract changed after the run",
        )

    if isr_graph is not None and factory_summary is not None:
        graph_hash = isr_graph.get("isr_hash", "")
        factory_hash = factory_summary.get("isr_hash", "")
        check(
            "isr-hash-consistency",
            bool(graph_hash) and graph_hash == factory_hash,
            f"graph={graph_hash[:16]} factory={factory_hash[:16]}",
        )
        check(
            "graph-system-name",
            bool(isr_graph.get("system_name")),
            "system_name missing from graph evidence",
        )

    if factory_summary is not None:
        required = set(contract.get("required_backends", []))
        seen = {bundle.get("backend_id") for bundle in factory_summary.get("bundles", [])}
        missing_backends = sorted(required - seen)
        check(
            "factory-required-backends",
            not missing_backends and bool(required),
            f"missing: {missing_backends}" if missing_backends else "",
        )
        failing = [
            bundle.get("backend_id")
            for bundle in factory_summary.get("bundles", [])
            if not (
                bundle.get("static_ok")
                and bundle.get("ok")
                and (bundle.get("test") or {}).get("evaluated")
                and (bundle.get("test") or {}).get("passed")
            )
        ]
        check(
            "factory-bundles-pass",
            bool(factory_summary.get("ok")) and not failing,
            f"failing: {failing}" if failing else "",
        )
        check(
            "factory-repair-bounded",
            int(factory_summary.get("repair_attempts_total", 0))
            <= int(contract.get("max_repair_attempts", 3))
            * max(len(factory_summary.get("bundles", [])), 1),
            "",
        )

    if e2e_results is not None:
        check("e2e-service-reachable", bool(e2e_results.get("reachable")), "")
        acs = e2e_results.get("acs", {}) or {}
        problems = []
        for ac_id in acceptance_ids:
            record = acs.get(ac_id)
            if record is None:
                problems.append(f"{ac_id}: no evidence")
                continue
            if not record.get("passed"):
                problems.append(f"{ac_id}: not passed")
            if not isinstance(record.get("http_status"), int):
                problems.append(f"{ac_id}: http_status missing")
            excerpt = record.get("response_excerpt")
            if not isinstance(excerpt, str) or not excerpt.strip():
                problems.append(f"{ac_id}: response_excerpt missing")
        extra = sorted(set(acs) - set(acceptance_ids))
        if extra:
            problems.append(f"unexpected acs: {extra}")
        check(
            "acceptance-evidence",
            not problems and bool(acceptance_ids),
            "; ".join(problems),
        )
        smoke = e2e_results.get("node_smoke", {}) or {}
        check(
            "frontend-smoke",
            smoke.get("exit") == 0 and bool(smoke.get("ok")),
            f"exit={smoke.get('exit')} ok={smoke.get('ok')}",
        )

    if manifest is not None:
        files = manifest.get("files", {}) or {}
        check("manifest-nonempty", bool(files), "no files recorded")
        mismatches = []
        for rel, recorded in files.items():
            path = out_dir / manifest.get("root", "repo") / rel
            if not path.is_file():
                mismatches.append(f"{rel}: missing on disk")
                continue
            actual = sha256_file(path)
            if actual != recorded:
                mismatches.append(f"{rel}: hash mismatch")
        check(
            "manifest-hashes-match-disk",
            not mismatches and bool(files),
            "; ".join(mismatches[:5]),
        )
        missing_artifacts = [
            suffix
            for suffix in REQUIRED_ARTIFACT_SUFFIXES
            if not any(rel.endswith(suffix) for rel in files)
        ]
        has_migration_sql = any(
            "/migrations/" in rel and rel.endswith(".sql") for rel in files
        )
        if not has_migration_sql:
            missing_artifacts.append("migrations/*.sql")
        check(
            "structural-artifacts",
            not missing_artifacts,
            f"missing: {missing_artifacts}" if missing_artifacts else "",
        )

    if run_results is not None:
        check("run-completed", bool(run_results.get("completed")), "")

    blocked_names = {"trial-output-present", "contract-present"}
    if any(c["name"] in blocked_names for c in checks):
        return 2, checks
    verdict = 0 if all(c["ok"] for c in checks) else 1
    return verdict, checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate TASKFLOW-ESAP-NATIVE-001")
    parser.add_argument("--trial-dir", default=None)
    args = parser.parse_args(argv)
    trial_dir = Path(args.trial_dir) if args.trial_dir else TRIAL_DIR
    verdict, checks = evaluate(trial_dir)
    evidence_dir = trial_dir / "out" / "evidence"
    if evidence_dir.exists():
        try:
            (evidence_dir / "evaluation.json").write_text(
                json.dumps(
                    {
                        "evidence_schema": EVIDENCE_SCHEMA,
                        "verdict": {0: "PASS", 1: "FAILED", 2: "BLOCKED"}[verdict],
                        "checks": checks,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass
    label = {0: "PASS", 1: "FAILED", 2: "BLOCKED"}[verdict]
    failed = [c["name"] for c in checks if not c["ok"]]
    print(f"evaluation: {label}")
    for check_result in checks:
        mark = "ok" if check_result["ok"] else "FAIL"
        detail = f" -- {check_result['detail']}" if check_result["detail"] else ""
        print(f"  [{mark}] {check_result['name']}{detail}")
    if failed:
        print(f"failed checks: {', '.join(failed)}")
    return verdict


if __name__ == "__main__":
    raise SystemExit(main())
