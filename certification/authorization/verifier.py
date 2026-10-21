"""Independent verification of the authorization certification evidence.

The verifier reads only what is on disk. It recomputes every binding from the
persisted artifacts and refuses to certify when anything is missing, stale, or
tampered. It never trusts the manifest's own claims.
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


def verify_authorization_evidence(evidence_dir: str) -> VerificationResult:
    """Recompute and check every binding the candidate claims."""
    root = Path(evidence_dir)
    problems: list[str] = []
    checks: dict[str, bool] = {}

    def record(name: str, ok: bool, message: str) -> bool:
        checks[name] = ok
        if not ok:
            problems.append(message)
        return ok

    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        record("manifest_present", False, f"missing {MANIFEST_NAME}")
        return VerificationResult(ok=False, problems=tuple(problems), checks=checks)
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
    if not plan_path.is_file():
        record("plan_present", False, f"missing {PLAN_NAME}")
    else:
        record("plan_present", True, "")
        from compiler.core.plan import CompilationPlan

        plan = CompilationPlan.model_validate(_read_json(plan_path))
        digest = sha256_json(plan.model_dump(mode="json"))
        record(
            "plan_hash",
            digest == candidate.plan_hash,
            f"plan hash mismatch: evidence={digest} manifest={candidate.plan_hash}",
        )

    bundle_path = root / BUNDLE_NAME
    if not bundle_path.is_file():
        record("bundle_present", False, f"missing {BUNDLE_NAME}")
    else:
        record("bundle_present", True, "")
        from compiler.core.repository import build_repository

        files = _read_json(bundle_path)
        digest = build_repository({str(k): str(v) for k, v in files.items()}).content_hash
        record(
            "artifact_bundle_hash",
            digest == candidate.artifact_bundle_hash,
            f"artifact bundle hash mismatch: evidence={digest} manifest={candidate.artifact_bundle_hash}",
        )

    report_path = root / RUNTIME_REPORT_NAME
    if not report_path.is_file():
        record("runtime_report_present", False, f"missing {RUNTIME_REPORT_NAME}")
    else:
        record("runtime_report_present", True, "")
        report = _read_json(report_path)
        digest = sha256_json({
            key: value for key, value in report.items() if key != "report_hash"
        })
        record(
            "runtime_report_hash",
            digest == candidate.runtime_report_hash == report.get("report_hash"),
            f"runtime report hash mismatch: evidence={digest} manifest={candidate.runtime_report_hash}",
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
        changed = mutation.get("changed_hashes") or {}
        record(
            "mutation_changed_hashes",
            bool(changed) and all(changed.values()),
            f"a policy mutation did not change every candidate binding hash: {changed}",
        )
        record(
            "mutation_invalidates_prior_evidence",
            bool(mutation.get("stale_evidence_problems")),
            "the prior candidate evidence still verified against the mutated candidate",
        )
        record(
            "mutation_reexecuted",
            bool(mutation.get("mutated_runtime_passed")),
            "the mutated candidate was not independently re-executed",
        )

    control_path = root / NEGATIVE_CONTROL_NAME
    if not control_path.is_file():
        record("negative_control_present", False, f"missing {NEGATIVE_CONTROL_NAME}")
    else:
        record("negative_control_present", True, "")
        control = _read_json(control_path)
        record(
            "rust_negative_control",
            bool(control.get("rejected")) and "authorization_policies" in str(control.get("reason", "")),
            f"the Rust negative control did not refuse the obligation: {control.get('reason')}",
        )

    ledger_path = root / LEDGER_NAME
    if not ledger_path.is_file():
        record("ledger_present", False, f"missing {LEDGER_NAME}")
        record("ledger_chain", False, "the evidence ledger is missing")
    else:
        record("ledger_present", True, "")
        record(
            "ledger_chain",
            EvidenceLedger.verify(str(ledger_path)),
            "the evidence ledger chain does not verify",
        )
        last: Mapping[str, Any] | None = None
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                last = json.loads(line)
        record(
            "ledger_binds_candidate",
            bool(last) and last.get("trial", {}).get("manifest_hash") == candidate.manifest_hash,
            "the ledger does not bind this candidate manifest",
        )

    return VerificationResult(
        ok=not problems,
        problems=tuple(problems),
        checks=checks,
    )
