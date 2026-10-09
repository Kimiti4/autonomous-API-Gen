"""Read-only baseline-vs-repaired benchmark against the JamiiLink repository.

The target checkout is treated as untrusted source: this script reads tracked
source text only and never imports or executes target application code.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

from app.engine.repository_code_scan import scan_repository

SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
EXCLUDED_PARTS = {
    ".git", "node_modules", "dist", "build", "coverage", ".next",
    "vendor", "playwright-report", "test-results",
}
REGISTRATION_PAGE = "iyf-s10-week-09-Kimiti4/src/pages/RegisterPage.jsx"
REGISTRATION_JOURNEY = (
    "iyf-s10-week-09-Kimiti4/e2e/journeys/"
    "jn-01.register-feed-discover-profile-alerts.spec.js"
)
EXPECTED_BASELINE_RULES = {
    REGISTRATION_PAGE: {"unassociated-jsx-label"},
    REGISTRATION_JOURNEY: {
        "conditional-e2e-interaction",
        "permissive-registration-outcome",
    },
}
REPAIRED_RULES = {
    REGISTRATION_PAGE: {"unassociated-jsx-label"},
    REGISTRATION_JOURNEY: {
        "conditional-e2e-interaction",
        "permissive-registration-outcome",
    },
}

MINIMAL_REPAIR_GUIDANCE = {
    "unassociated-jsx-label": {
        "change": "Add a stable unique id to the input and a matching htmlFor to its label.",
        "verification": "Use Playwright getByLabel and run the accessibility suite.",
    },
    "conditional-e2e-interaction": {
        "change": "Make required form filling and submission unconditional; let missing controls fail the test.",
        "verification": "Run the registration journey and assert the registration request was sent.",
    },
    "permissive-registration-outcome": {
        "change": "Assert navigation to /login and validate the captured registration payload; do not accept /register.",
        "verification": "Assert the URL and payload fields after submission in the registration E2E journey.",
    },
}


def tracked_source_files(root: Path) -> list[tuple[str, str]]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    paths = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = raw.decode("utf-8", errors="replace").replace("\\", "/")
        parts = set(Path(relative).parts)
        if parts & EXCLUDED_PARTS or Path(relative).suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        file_path = root / relative
        if not file_path.is_file():
            continue
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        paths.append((relative, source))
    return sorted(paths, key=lambda item: item[0])


def summarize(root: Path) -> dict:
    files = tracked_source_files(root)
    if not files:
        raise RuntimeError(f"no tracked source files found under {root}")
    scan = scan_repository(files, root=str(root))
    findings = [
        {
            "id": finding.finding_id,
            "path": finding.path,
            "line": finding.line,
            "rule": finding.rule,
            "category": finding.category,
            "severity": finding.severity,
            "message": finding.message,
            "evidence": list(finding.evidence),
            "digest": finding.digest,
        }
        for finding in scan.findings
    ]
    return {
        "repository": str(root),
        "source_files_scanned": scan.files_scanned,
        "scan_digest": scan.digest,
        "findings_count": len(findings),
        "rule_counts": dict(sorted(Counter(f["rule"] for f in findings).items())),
        "findings": findings,
    }


def findings_for(scan: dict, path: str) -> set[str]:
    return {f["rule"] for f in scan["findings"] if f["path"] == path}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    baseline = summarize(args.baseline.resolve())
    candidate = summarize(args.candidate.resolve())
    checks = []
    for path, expected_rules in EXPECTED_BASELINE_RULES.items():
        observed = findings_for(baseline, path)
        for rule in sorted(expected_rules):
            checks.append({
                "id": f"baseline-detects:{path}:{rule}",
                "status": "PASS" if rule in observed else "FAIL",
                "observed_rules": sorted(observed),
            })
    for path, forbidden_rules in REPAIRED_RULES.items():
        observed = findings_for(candidate, path)
        for rule in sorted(forbidden_rules):
            checks.append({
                "id": f"candidate-clears:{path}:{rule}",
                "status": "FAIL" if rule in observed else "PASS",
                "observed_rules": sorted(observed),
            })

    baseline_rules = {
        finding["rule"]
        for finding in baseline["findings"]
        if finding["path"] in EXPECTED_BASELINE_RULES
    }
    repair_proposals = [
        {
            "rule": rule,
            "minimal_change": MINIMAL_REPAIR_GUIDANCE[rule]["change"],
            "verification": MINIMAL_REPAIR_GUIDANCE[rule]["verification"],
            "patch_applied": False,
            "human_review_required": True,
        }
        for rule in sorted(baseline_rules)
        if rule in MINIMAL_REPAIR_GUIDANCE
    ]
    proposal_rules = {proposal["rule"] for proposal in repair_proposals}
    checks.append({
        "id": "minimal-repair-proposals",
        "status": "PASS" if set(MINIMAL_REPAIR_GUIDANCE).issubset(proposal_rules) else "FAIL",
        "observed_rules": sorted(proposal_rules),
    })

    report = {
        "schema": "esap.existing-codebase-benchmark.v1",
        "scope": {
            "mode": "read-only",
            "inventory": "git-tracked source files with supported source extensions",
            "excluded_directory_names": sorted(EXCLUDED_PARTS),
            "runtime_execution_of_target_source": False,
            "full_repository_audit_claimed": False,
            "repair_applied_by_esap": False,
        },
        "benchmark": "jamiilink-registration-label-and-e2e-integrity",
        "baseline": baseline,
        "candidate": candidate,
        "repair_proposals": repair_proposals,
        "checks": checks,
        "verdict": "PASS" if checks and all(c["status"] == "PASS" for c in checks) else "FAIL",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": report["verdict"],
        "baseline_source_files": baseline["source_files_scanned"],
        "candidate_source_files": candidate["source_files_scanned"],
        "baseline_findings": baseline["findings_count"],
        "candidate_findings": candidate["findings_count"],
        "checks": checks,
        "report": str(args.report),
    }, indent=2))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
