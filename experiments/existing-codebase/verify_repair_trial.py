"""Validate generated repair evidence and repaired semantics in the disposable trial workspace."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from app.engine.repository_code_scan import scan_repository

TARGETS = [
    "iyf-s10-week-09-Kimiti4/src/pages/RegisterPage.jsx",
    "iyf-s10-week-09-Kimiti4/e2e/journeys/jn-01.register-feed-discover-profile-alerts.spec.js",
]
EXPECTED_RULES = {
    "unassociated-jsx-label",
    "conditional-e2e-interaction",
    "permissive-registration-outcome",
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--patch", required=True, type=Path)
    parser.add_argument("--repair-report", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    patch_path = args.patch.resolve()
    repair_report_path = args.repair_report.resolve()

    def blocked(reason: str) -> int:
        print(json.dumps({"verdict": "BLOCKED", "reason": reason, "patch_applied": False}))
        return 2

    files: list[tuple[str, str]] = []
    for relative in TARGETS:
        path = workspace / relative
        if not path.is_file():
            return blocked(f"missing target {relative}")
        files.append((relative, path.read_text(encoding="utf-8", errors="replace")))

    if not patch_path.is_file() or patch_path.stat().st_size == 0:
        return blocked("generated patch is missing or empty")
    if not repair_report_path.is_file():
        return blocked("repair-generation report is missing")

    try:
        generation = json.loads(repair_report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return blocked(f"repair-generation report is unreadable: {exc}")

    patch = patch_path.read_text(encoding="utf-8", errors="replace")
    page = dict(files)[TARGETS[0]]
    journey = dict(files)[TARGETS[1]]
    changes = generation.get("changes")
    change_by_path = {
        item.get("path"): item for item in changes if isinstance(item, dict)
    } if isinstance(changes, list) else {}
    checks: list[dict[str, str]] = []

    def check(check_id: str, passed: bool) -> None:
        checks.append({"id": check_id, "status": "PASS" if passed else "FAIL"})

    check("generation-report-schema", generation.get("schema") == "esap.existing-codebase-repair-trial.v1")
    check("generation-mode-is-disposable-only", generation.get("mode") == "disposable-workspace-only")
    check("upstream-repository-not-modified", generation.get("upstream_repository_modified") is False)
    check("human-review-required-before-external-write", generation.get("human_review_required_before_external_write") is True)
    check("no-general-reasoning-claim", generation.get("independent_general_reasoning_claimed") is False)
    check("patch-claims-disposable-application", generation.get("patch_applied_to_disposable_workspace") is True)
    check("patch-includes-registration-page", f"--- a/{TARGETS[0]}" in patch and f"+++ b/{TARGETS[0]}" in patch)
    check("patch-includes-registration-journey", f"--- a/{TARGETS[1]}" in patch and f"+++ b/{TARGETS[1]}" in patch)
    check("repair-report-has-exact-target-set", set(change_by_path) == set(TARGETS))

    hash_checks = True
    for relative, content in files:
        item = change_by_path.get(relative, {})
        before_hash = item.get("before_sha256", "")
        after_hash = item.get("after_sha256", "")
        if not re.fullmatch(r"[0-9a-f]{64}", before_hash) or not re.fullmatch(r"[0-9a-f]{64}", after_hash):
            hash_checks = False
        if not after_hash or sha256_text(content) != after_hash:
            hash_checks = False
        if before_hash == after_hash:
            hash_checks = False
    check("repair-report-hashes-match-workspace", hash_checks)

    # Independent semantic assertions prevent a clean heuristic scan from being the only gate.
    label_pairs = re.findall(r'<label\s+htmlFor="([^"]+)"[^>]*>', page)
    input_ids = set(re.findall(r'<input\b[^>]*\bid="([^"]+)"', page))
    check("labels-reference-existing-input-ids", len(label_pairs) >= 5 and all(value in input_ids for value in label_pairs))
    check("required-journey-interactions-not-conditionally-skipped", not re.search(r"if\s*\(\s*await\s+\w+\.isVisible\s*\(\s*\)\s*\)", journey))
    check("journey-asserts-specific-login-destination", bool(re.search(r"toHaveURL\(\s*/.*login", journey)))
    check("journey-captures-and-checks-registration-payload", "registrationPayload" in journey and "postDataJSON()" in journey and "toMatchObject" in journey)
    check("patch-artifact-nonempty", patch_path.stat().st_size > 0)

    scan = scan_repository(files, root=str(workspace))
    findings = [
        {"path": f.path, "line": f.line, "rule": f.rule, "evidence": list(f.evidence)}
        for f in scan.findings if f.rule in EXPECTED_RULES
    ]
    present = {finding["rule"] for finding in findings}
    checks.extend(
        {"id": f"generated-trial-clears:{rule}", "status": "PASS" if rule not in present else "FAIL"}
        for rule in sorted(EXPECTED_RULES)
    )
    result = {
        "schema": "esap.existing-codebase-repair-verification.v2",
        "workspace": str(workspace),
        "runtime_execution_of_source_by_scanner": False,
        "upstream_repository_modified": False,
        "repair_generation_report": str(repair_report_path),
        "patch_path": str(patch_path),
        "patch_bytes": patch_path.stat().st_size,
        "target_findings_remaining": findings,
        "checks": checks,
        "passed_checks": sum(item["status"] == "PASS" for item in checks),
        "total_checks": len(checks),
        "verdict": "PASS" if all(item["status"] == "PASS" for item in checks) and not findings else "FAIL",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": result["verdict"], "passed_checks": result["passed_checks"], "total_checks": result["total_checks"], "checks": checks, "target_findings_remaining": findings}, indent=2))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
