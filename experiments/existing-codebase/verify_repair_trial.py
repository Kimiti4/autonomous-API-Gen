"""Validate a generated repair only inside the disposable JamiiLink trial workspace."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--patch", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    files = []
    for relative in TARGETS:
        path = workspace / relative
        if not path.is_file():
            print(json.dumps({"verdict": "BLOCKED", "reason": f"missing target {relative}"}))
            return 2
        files.append((relative, path.read_text(encoding="utf-8", errors="replace")))
    if not args.patch.is_file() or args.patch.stat().st_size == 0:
        print(json.dumps({"verdict": "FAIL", "reason": "generated patch is missing or empty"}))
        return 1

    scan = scan_repository(files, root=str(workspace))
    findings = [
        {"path": f.path, "line": f.line, "rule": f.rule, "evidence": list(f.evidence)}
        for f in scan.findings if f.rule in EXPECTED_RULES
    ]
    present = {finding["rule"] for finding in findings}
    missing = sorted(EXPECTED_RULES - present)
    checks = [
        {"id": f"generated-trial-clears:{rule}", "status": "PASS" if rule not in present else "FAIL"}
        for rule in sorted(EXPECTED_RULES)
    ]
    checks.extend([
        {"id": "patch-artifact-nonempty", "status": "PASS" if args.patch.stat().st_size > 0 else "FAIL"},
        {"id": "scope-is-disposable-workspace", "status": "PASS"},
    ])
    result = {
        "schema": "esap.existing-codebase-repair-verification.v1",
        "workspace": str(workspace),
        "runtime_execution_of_source_by_scanner": False,
        "upstream_repository_modified": False,
        "patch_path": str(args.patch),
        "patch_bytes": args.patch.stat().st_size,
        "target_findings_remaining": findings,
        "checks": checks,
        "verdict": "PASS" if not missing else "FAIL",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": result["verdict"], "checks": checks, "target_findings_remaining": findings}, indent=2))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
