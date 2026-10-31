"""Independent verification of the authorization certification evidence.

The verifier reads only what is on disk. It recomputes every binding from the
persisted artifacts and refuses to certify when anything is missing, stale,
tampered, or mismatched. It never trusts the manifest's own claims.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from certification.authorization.candidate import (
    candidate_from_manifest,
    canonical_json,
    sha256_json,
    sha256_text,
)
from certification.evidence.ledger import EvidenceLedger

MANIFEST_NAME = "manifest.json"
SOURCE_NAME = "source.md"
REQUIREMENT_GRAPH_NAME = "requirement-graph.json"
ISR_NAME = "isr.json"
PLAN_NAME = "plan.json"
BUNDLE_NAME = "bundle.json"
RUNTIME_REPORT_NAME = "runtime-report.json"
MUTATION_NAME = "mutation.json"
NEGATIVE_CONTROL_NAME = "negative-control.json"
LEDGER_NAME = "authorization-ledger.jsonl"
COVERAGE_NAME = "coverage.json"
WORKLOADS_DIRNAME = "workloads"


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    problems: tuple[str, ...]
    checks: dict[str, bool]

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "problems": list(self.problems),
            "checks": dict(self.checks),
        }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _verify_workload(root: Path, workload_id: str) -> tuple[list[str], dict[str, bool]]:
    """Verify one workload's evidence directory."""
    problems: list[str] = []
    checks: dict[str, bool] = {}

    def record(name: str, ok: bool, message: str) -> bool:
        checks[name] = ok
        if not ok:
            problems.append(f"{workload_id}: {message}")
        return ok

    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        record("manifest_present", False, f"missing {MANIFEST_NAME}")
        return problems, checks
    record("manifest_present", True, "")

    manifest = _read_json(manifest_path)
    candidate = candidate_from_manifest(manifest)

    source_path = root / SOURCE_NAME
    if not source_path.is_file():
        record("source_present", False, f"missing {SOURCE_NAME}")
    else:
        record("source_present", True, "")
        digest = sha256_text(source_path.read_text(encoding="utf-8"))
        record(
            "source_digest",
            digest == candidate.source_sha256,
            f"source digest mismatch: evidence={digest} manifest={candidate.source_sha256}",
        )

    graph_path = root / REQUIREMENT_GRAPH_NAME
    if not graph_path.is_file():
        record("requirement_graph_present", False, f"missing {REQUIREMENT_GRAPH_NAME}")
    else:
        record("requirement_graph_present", True, "")
        from reqgraph.adapters.tor_isr import requirement_graph_hash
        from reqgraph.core.graph import RequirementGraph

        graph = RequirementGraph.model_validate(_read_json(graph_path))
        digest = requirement_graph_hash(graph)
        record(
            "requirement_graph_hash",
            digest == candidate.requirement_graph_hash,
            f"requirement graph hash mismatch: evidence={digest} manifest={candidate.requirement_graph_hash}",
        )

    isr_path = root / ISR_NAME
    if not isr_path.is_file():
        record("isr_present", False, f"missing {ISR_NAME}")
    else:
        record("isr_present", True, "")
        from isr.core.revision import ISRRevision

        revision = ISRRevision.model_validate(_read_json(isr_path))
        record(
            "isr_content_hash",
            revision.content_hash == candidate.isr_content_hash,
            f"ISR content hash mismatch: evidence={revision.content_hash} "
            f"manifest={candidate.isr_content_hash}",
        )

    plan_path = root / PLAN_NAME
    plan_payload: Any = None
    if not plan_path.is_file():
        record("plan_present", False, f"missing {PLAN_NAME}")
    else:
        record("plan_present", True, "")
        from compiler.core.plan import CompilationPlan

        plan_payload = CompilationPlan.model_validate(_read_json(plan_path))
        digest = sha256_json(plan_payload.model_dump(mode="json"))
        record(
            "plan_hash",
            digest == candidate.plan_hash,
            f"plan hash mismatch: evidence={digest} manifest={candidate.plan_hash}",
        )

    bundle_path = root / BUNDLE_NAME
    bundle_files: dict[str, str] = {}
    if not bundle_path.is_file():
        record("bundle_present", False, f"missing {BUNDLE_NAME}")
    else:
        record("bundle_present", True, "")
        from compiler.core.repository import build_repository

        bundle_files = {str(k): str(v) for k, v in _read_json(bundle_path).items()}
        digest = build_repository(bundle_files).content_hash
        record(
            "artifact_bundle_hash",
            digest == candidate.artifact_bundle_hash,
            f"artifact bundle hash mismatch: evidence={digest} manifest={candidate.artifact_bundle_hash}",
        )

    # The manifest's declared policy and operation bindings must match the plan
    # and the emitted application, not merely the plan's own hash.
    if plan_payload is not None:
        from certification.authorization.candidate import (
            bound_operations_of,
            declared_routes_of,
        )

        observed = bound_operations_of(plan_payload)
        record(
            "policy_bindings_match_plan",
            [dict(binding) for binding in observed] == [dict(binding) for binding in candidate.bound_operations],
            "the manifest's authorization bindings do not match the compiled plan",
        )
        record(
            "policy_ids_match_plan",
            sorted(p.policy_id for p in plan_payload.security) == sorted(candidate.policy_ids),
            "the manifest's policy ids do not match the compiled plan",
        )
        observed_routes = declared_routes_of(plan_payload)
        record(
            "declared_routes_match_plan",
            [dict(route) for route in observed_routes]
            == [dict(route) for route in candidate.declared_routes],
            "the manifest's declared routes do not match the compiled plan",
        )
    if bundle_files:
        emitted = bundle_files.get("app/core/policies.py", "")
        record(
            "emitted_enforcement_matches_manifest",
            all(policy_id in emitted for policy_id in candidate.policy_ids),
            "the generated application does not carry the manifest's policies",
        )
        if candidate.declared_routes:
            declared_module = bundle_files.get("app/api/declared.py")
            record(
                "declared_module_present",
                bool(declared_module),
                "the generated application does not emit the declared API module",
            )
            if declared_module:
                missing = [
                    route for route in candidate.declared_routes
                    if f"{route['path']!r}," not in declared_module
                    or f"methods=[{route['method']!r}]" not in declared_module
                    or f"OPERATION_POLICIES[{route['operation_id']!r}]" not in declared_module
                    or f"resource={route['resource']!r}" not in declared_module
                ]
                record(
                    "emitted_declared_routes_match_manifest",
                    not missing,
                    "the generated application does not emit the manifest's declared "
                    f"routes: {[route['operation_id'] for route in missing]}",
                )

    report_path = root / RUNTIME_REPORT_NAME
    if not report_path.is_file():
        record("runtime_report_present", False, f"missing {RUNTIME_REPORT_NAME}")
    else:
        record("runtime_report_present", True, "")
        report = _read_json(report_path)
        digest = sha256_json({
            key: value
            for key, value in report.items()
            if key not in ("report_hash", "stdout_sha256")
        })
        record(
            "runtime_report_hash",
            digest == candidate.runtime_report_hash == report.get("report_hash"),
            f"runtime report hash mismatch: evidence={digest} manifest={candidate.runtime_report_hash}",
        )
        record(
            "runtime_report_bound_to_candidate",
            report.get("bundle_hash") == candidate.artifact_bundle_hash,
            "the runtime report was not produced by the candidate's generated bundle: "
            f"report={report.get('bundle_hash')} manifest={candidate.artifact_bundle_hash}",
        )
        record(
            "runtime_report_passed",
            bool(report.get("passed")) and not report.get("failed_tests"),
            f"the generated application did not pass its own suite: {report.get('failed_tests')}",
        )
        missing = [name for name in candidate.required_adversarial_tests
                   if name not in set(report.get("passed_tests") or ())]
        record(
            "runtime_adversarial_coverage",
            not missing,
            f"the generated application did not execute the required adversarial tests: {missing}",
        )

    mutation_path = root / MUTATION_NAME
    if not mutation_path.is_file():
        record("mutation_present", False, f"missing {MUTATION_NAME}")
    else:
        record("mutation_present", True, "")
        mutation = _read_json(mutation_path)
        cases = mutation.get("cases") or []
        record(
            "mutation_cases_present",
            bool(cases),
            "the workload declares no executed policy mutation",
        )
        record(
            "mutation_changed_hashes",
            all(all((case.get("changed_hashes") or {}).values()) for case in cases),
            "a policy mutation did not change every candidate binding hash",
        )
        record(
            "mutation_invalidates_prior_evidence",
            all(case.get("stale_evidence_problems") for case in cases),
            "the prior candidate evidence still verified against a mutated candidate",
        )
        record(
            "mutation_reexecuted",
            all(case.get("mutated_runtime_passed") for case in cases),
            "a mutated candidate was not independently re-executed",
        )

    control_path = root / NEGATIVE_CONTROL_NAME
    if not control_path.is_file():
        record("negative_control_present", False, f"missing {NEGATIVE_CONTROL_NAME}")
    else:
        record("negative_control_present", True, "")
        control = _read_json(control_path)
        record(
            "rust_negative_control",
            bool(control.get("rejected"))
            and control.get("verdict") == "UNSUPPORTED_FAIL_CLOSED"
            and "authorization_policies" in str(control.get("reason", "")),
            f"the Rust negative control did not refuse the obligation: {control.get('reason')}",
        )

    return problems, checks


def verify_authorization_evidence(evidence_dir: str) -> VerificationResult:
    """Recompute and check every binding the candidates claim."""
    root = Path(evidence_dir)
    problems: list[str] = []
    checks: dict[str, bool] = {}

    workloads_root = root / WORKLOADS_DIRNAME
    if not workloads_root.is_dir():
        checks["workloads_present"] = False
        problems.append(f"missing {WORKLOADS_DIRNAME}/")
        return VerificationResult(ok=False, problems=tuple(problems), checks=checks)
    checks["workloads_present"] = True

    workload_dirs = sorted(path for path in workloads_root.iterdir() if path.is_dir())
    if not workload_dirs:
        checks["workloads_non_empty"] = False
        problems.append("no workload evidence was produced")
        return VerificationResult(ok=False, problems=tuple(problems), checks=checks)
    checks["workloads_non_empty"] = True

    for workload_dir in workload_dirs:
        workload_problems, workload_checks = _verify_workload(workload_dir, workload_dir.name)
        problems.extend(workload_problems)
        for name, value in workload_checks.items():
            checks[f"{workload_dir.name}.{name}"] = value

    coverage_path = root / COVERAGE_NAME
    if not coverage_path.is_file():
        checks["coverage_present"] = False
        problems.append(f"missing {COVERAGE_NAME}")
    else:
        checks["coverage_present"] = True
        coverage = _read_json(coverage_path)
        rows = coverage.get("rows") or []
        recorded = {(row["workload_id"], row["backend"]) for row in rows}
        expected = {
            (workload_dir.name, backend)
            for workload_dir in workload_dirs
            for backend in ("python-fastapi", "rust-axum")
        }
        checks["coverage_matches_workloads"] = recorded == expected
        if recorded != expected:
            problems.append(
                "the coverage report does not cover exactly the produced workloads: "
                f"recorded={sorted(recorded)} expected={sorted(expected)}"
            )
        certified = [row for row in rows if row["verdict"] == "CERTIFIED"]
        fail_closed = [row for row in rows if row["verdict"] == "UNSUPPORTED_FAIL_CLOSED"]
        checks["coverage_has_certified_rows"] = bool(certified)
        checks["coverage_has_fail_closed_rows"] = bool(fail_closed)
        if not certified:
            problems.append("the coverage report certifies no backend")
        if not fail_closed:
            problems.append("the coverage report records no fail-closed backend")

    ledger_path = root / LEDGER_NAME
    if not ledger_path.is_file():
        checks["ledger_present"] = False
        checks["ledger_chain"] = False
        problems.append("the evidence ledger is missing")
    else:
        checks["ledger_present"] = True
        checks["ledger_chain"] = EvidenceLedger.verify(str(ledger_path))
        if not checks["ledger_chain"]:
            problems.append("the evidence ledger chain does not verify")
        records = [
            json.loads(line)
            for line in ledger_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        bound = {record.get("trial", {}).get("workload_id") for record in records}
        expected_ids = {workload_dir.name for workload_dir in workload_dirs}
        checks["ledger_binds_every_workload"] = expected_ids.issubset(bound)
        if not expected_ids.issubset(bound):
            problems.append(
                f"the ledger does not bind every workload: expected={sorted(expected_ids)} "
                f"bound={sorted(bound)}"
            )
        for record in records:
            trial = record.get("trial", {})
            workload_id = trial.get("workload_id")
            manifest_path = workloads_root / str(workload_id) / MANIFEST_NAME
            if not manifest_path.is_file():
                continue
            manifest = _read_json(manifest_path)
            candidate = candidate_from_manifest(manifest)
            checks[f"ledger_binds_{workload_id}"] = (
                trial.get("manifest_hash") == candidate.manifest_hash
            )
            if trial.get("manifest_hash") != candidate.manifest_hash:
                problems.append(
                    f"{workload_id}: the ledger does not bind this candidate manifest"
                )

    return VerificationResult(
        ok=not problems,
        problems=tuple(problems),
        checks=checks,
    )
