"""The source-bound authorization certification lane.

The lane proves one thing: that a reviewed source requirement, bound through
an approval to a typed ISR policy, reaches a generated application whose own
runtime enforces it, and that the whole chain is candidate-bound.

Gates, in order:

``source_binding``
    The reviewed requirement declares a typed policy, the approval binds it,
    the canonical mapper projects it, and the plan carries exactly the declared
    operations.
``candidate_binding``
    Source digest, requirement graph hash, ISR content hash, plan hash,
    generated bundle hash, and runtime report hash agree.
``runtime_enforcement``
    The generated application is installed and runs its own adversarial suite.
    Static assertions do not count.
``mutation_sensitivity``
    A policy mutation changes the source, ISR, plan, bundle, and runtime report
    hashes; reusing the previous candidate's evidence fails.
``rust_negative_control``
    The same candidate is refused by the Rust backend with a precise
    unsupported-semantics reason. No Rust pass is inferred.
``independent_verification``
    An independent verifier replays the bindings from the persisted artifacts.

The verdict is ``CERTIFIED`` only when every gate passes and the independent
verifier reports no problems.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from certification.authorization.candidate import (
    REQUIRED_ADVERSARIAL_TESTS,
    AuthorizationCandidate,
    build_candidate,
    candidate_from_manifest,
    canonical_json,
    sha256_json,
    sha256_text,
    stale_evidence_problems,
)
from certification.authorization.corpus import (
    CORPUS_VERSION,
    AuthorizationWorkload,
    validate_workload,
)
from certification.authorization.runtime import RuntimeReport, run_generated_suite
from certification.authorization.verifier import verify_authorization_evidence
from certification.authorization.workloads import (
    AUTHORIZATION_CORPUS,
    AUTHORIZATION_CORPUS_HASH,
    CORPUS_ID,
    CORPUS_METADATA,
)
from certification.evidence.ledger import EvidenceLedger

VERDICT_CERTIFIED = "CERTIFIED"
VERDICT_NOT_CERTIFIED = "NOT_CERTIFIED"

GATE_NAMES = (
    "source_binding",
    "candidate_binding",
    "runtime_enforcement",
    "mutation_sensitivity",
    "rust_negative_control",
    "independent_verification",
)

TRIAL_SCHEMA_ID = "tiannara.authorization.trial"
TRIAL_SCHEMA_VERSION = "1.0.0"

LEDGER_NAME = "authorization-ledger.jsonl"


@dataclass(frozen=True)
class GateResult:
    gate: str
    passed: bool
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {"gate": self.gate, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class AuthorizationCampaignResult:
    verdict: str
    candidate_id: str
    manifest_hash: str
    gates: tuple[GateResult, ...]
    problems: tuple[str, ...]
    evidence_dir: str

    @property
    def certified(self) -> bool:
        return self.verdict == VERDICT_CERTIFIED

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "candidate_id": self.candidate_id,
            "manifest_hash": self.manifest_hash,
            "gates": [gate.as_dict() for gate in self.gates],
            "problems": list(self.problems),
            "evidence_dir": self.evidence_dir,
        }


@dataclass(frozen=True)
class CandidateArtifacts:
    workload: AuthorizationWorkload
    draft: Any
    projection: Any
    plan: Any
    repo: Any


def build_candidate_artifacts(workload: AuthorizationWorkload) -> CandidateArtifacts:
    """Project a corpus workload through the controlled source-bound seam."""
    from compiler.core.lowering import isr_to_plan
    from compiler.backends.python_fastapi import PythonFastAPIBackend
    from reqgraph.adapters.tor_isr import project_tor_to_isr
    from reqgraph.ingestion.tor_extractor import extract_tor_text

    draft = extract_tor_text(workload.source_text, workload.source_name)
    approvals, _ = workload.resolve_requirements(draft)
    projection = project_tor_to_isr(
        draft,
        approvals,
        system_id=workload.system_id,
        revision_id=workload.revision_id,
        created_at=workload.created_at,
    )
    plan = isr_to_plan(projection.revision)
    repo = PythonFastAPIBackend().compile(plan)
    return CandidateArtifacts(
        workload=workload,
        draft=draft,
        projection=projection,
        plan=plan,
        repo=repo,
    )


def _replace_role(payload: Any, old_role: str, new_role: str) -> Any:
    if isinstance(payload, str):
        return payload.replace(old_role, new_role)
    if isinstance(payload, Mapping):
        return {key: _replace_role(value, old_role, new_role) for key, value in payload.items()}
    if isinstance(payload, (list, tuple)):
        return [_replace_role(value, old_role, new_role) for value in payload]
    return payload


def mutate_workload(
    workload: AuthorizationWorkload,
    *,
    old_role: str,
    new_role: str,
) -> AuthorizationWorkload:
    """Return a workload whose policy role was renamed in the source and approval."""
    mutated = dataclasses.replace(
        workload,
        source_text=workload.source_text.replace(old_role, new_role),
        approval_needles=tuple(
            (needle, _replace_role(payload, old_role, new_role))
            for needle, payload in workload.approval_needles
        ),
        policy_node=_replace_role(workload.policy_node, old_role, new_role),
        policy_edge=_replace_role(workload.policy_edge, old_role, new_role),
        bound_operations=tuple(
            dataclasses.replace(
                binding,
                roles=tuple(role.replace(old_role, new_role) for role in binding.roles),
            )
            for binding in workload.bound_operations
        ),
    )
    validate_workload(mutated)
    return mutated


def _source_binding_problems(
    workload: AuthorizationWorkload,
    artifacts: CandidateArtifacts,
) -> list[str]:
    problems: list[str] = []
    graph = artifacts.projection.revision.graph
    node = graph.nodes.get(workload.policy_node_id)
    if node is None:
        problems.append(f"the declared policy node {workload.policy_node_id!r} is not in the ISR")
        return problems
    behavior = node.properties.get("behavior")
    if not isinstance(behavior, Mapping) or not behavior.get("rules"):
        problems.append("the projected policy carries no typed rules")
        return problems
    edge = graph.edges.get(workload.policy_edge.get("id", ""))
    if edge is None or edge.type.value != "secured_by":
        problems.append("the projected ISR does not bind the policy with a secured_by edge")

    declared = {
        (binding.operation, binding.resource, binding.effect, tuple(binding.roles))
        for binding in workload.bound_operations
    }
    observed: set[tuple[str, str, str, tuple[str, ...]]] = set()
    for service in artifacts.plan.services:
        for policy in service.security_policies:
            if policy.behavior is None:
                continue
            for rule in policy.behavior.rules:
                for action in rule.actions:
                    observed.add((action, rule.resource, rule.effect, tuple(rule.roles)))
    if declared != observed:
        problems.append(
            "the plan's authorization obligations do not match the declared source bindings: "
            f"declared={sorted(declared)} observed={sorted(observed)}"
        )
    return problems


def _candidate_binding_problems(
    candidate: AuthorizationCandidate,
    artifacts: CandidateArtifacts,
    runtime_report: RuntimeReport,
) -> list[str]:
    from reqgraph.adapters.tor_isr import requirement_graph_hash

    return stale_evidence_problems(
        candidate,
        source_sha256=artifacts.projection.source_sha256,
        requirement_graph_hash=requirement_graph_hash(artifacts.projection.requirement_graph),
        isr_content_hash=artifacts.projection.revision.content_hash,
        plan_hash=sha256_json(artifacts.plan.model_dump(mode="json")),
        artifact_bundle_hash=artifacts.repo.content_hash,
        runtime_report_hash=runtime_report.report_hash,
    )


def _rust_negative_control(plan: Any) -> tuple[bool, str]:
    """Submit the same candidate to Rust; it must refuse the obligation."""
    from compiler.backends.rust_axum import RustAxumBackend
    from compiler.core.capabilities import UnsupportedSemanticsError

    try:
        RustAxumBackend().compile(plan)
    except UnsupportedSemanticsError as exc:
        message = str(exc)
        if "authorization_policies" in message:
            return True, message
        return False, f"rust refused the candidate without citing authorization_policies: {message}"
    return False, "rust accepted a candidate carrying an authorization obligation"


def _write_evidence(
    evidence_dir: Path,
    artifacts: CandidateArtifacts,
    candidate: AuthorizationCandidate,
    runtime_report: RuntimeReport,
    mutation: Mapping[str, Any],
    negative_control: Mapping[str, Any],
) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "source.md").write_text(artifacts.workload.source_text, encoding="utf-8")
    (evidence_dir / "requirement-graph.json").write_text(
        canonical_json(artifacts.projection.requirement_graph.model_dump(mode="json")),
        encoding="utf-8",
    )
    (evidence_dir / "isr.json").write_text(
        canonical_json(artifacts.projection.revision.model_dump(mode="json")),
        encoding="utf-8",
    )
    (evidence_dir / "plan.json").write_text(
        canonical_json(artifacts.plan.model_dump(mode="json")),
        encoding="utf-8",
    )
    (evidence_dir / "bundle.json").write_text(
        canonical_json(dict(sorted(artifacts.repo.files.items()))),
        encoding="utf-8",
    )
    (evidence_dir / "runtime-report.json").write_text(
        canonical_json(runtime_report.as_dict()),
        encoding="utf-8",
    )
    (evidence_dir / "manifest.json").write_text(
        canonical_json(candidate.manifest()),
        encoding="utf-8",
    )
    (evidence_dir / "mutation.json").write_text(canonical_json(mutation), encoding="utf-8")
    (evidence_dir / "negative-control.json").write_text(
        canonical_json(negative_control), encoding="utf-8"
    )


def run_authorization_campaign(
    evidence_dir: str,
    workload: AuthorizationWorkload = AUTHORIZATION_CORPUS[0],
    *,
    install: bool = True,
    keep_evidence: bool = True,
) -> AuthorizationCampaignResult:
    """Run the authorization certification lane for one workload."""
    evidence_path = Path(evidence_dir)
    gates: list[GateResult] = []
    problems: list[str] = []

    if evidence_path.exists():
        shutil.rmtree(evidence_path)
    evidence_path.mkdir(parents=True, exist_ok=True)
    workdir = evidence_path / "work"

    artifacts = build_candidate_artifacts(workload)
    source_problems = _source_binding_problems(workload, artifacts)
    gates.append(GateResult(
        gate="source_binding",
        passed=not source_problems,
        detail="the source declaration, approval, ISR, and plan agree"
        if not source_problems else "; ".join(source_problems),
    ))
    problems.extend(source_problems)

    runtime_report = run_generated_suite(
        artifacts.repo.files,
        workdir / "candidate",
        REQUIRED_ADVERSARIAL_TESTS,
        install=install,
    )
    candidate = build_candidate(
        candidate_id=f"authorization-candidate:{workload.workload_id}",
        corpus_id=CORPUS_ID,
        corpus_version=CORPUS_VERSION,
        corpus_hash=AUTHORIZATION_CORPUS_HASH,
        workload_id=workload.workload_id,
        projection=artifacts.projection,
        plan=artifacts.plan,
        repo=artifacts.repo,
        runtime_report_hash=runtime_report.report_hash,
    )
    binding_problems = _candidate_binding_problems(candidate, artifacts, runtime_report)
    gates.append(GateResult(
        gate="candidate_binding",
        passed=not binding_problems,
        detail="every candidate binding hash agrees"
        if not binding_problems else "; ".join(binding_problems),
    ))
    problems.extend(binding_problems)

    runtime_problems: list[str] = []
    if not runtime_report.passed:
        runtime_problems.append(
            "the generated application did not pass its own adversarial suite: "
            f"missing={list(runtime_report.missing_required)} failed={list(runtime_report.failed_tests)}"
        )
    gates.append(GateResult(
        gate="runtime_enforcement",
        passed=not runtime_problems,
        detail=f"{runtime_report.total} generated tests passed"
        if not runtime_problems else "; ".join(runtime_problems),
    ))
    problems.extend(runtime_problems)

    mutation_problems: list[str] = []
    mutation_detail: dict[str, Any] = {}
    try:
        mutated_workload = mutate_workload(workload, old_role="payroll_approver", new_role="payroll_admin")
        mutated_artifacts = build_candidate_artifacts(mutated_workload)
        mutated_report = run_generated_suite(
            mutated_artifacts.repo.files,
            workdir / "mutated",
            REQUIRED_ADVERSARIAL_TESTS,
            install=install,
        )
        changed = {
            "source_sha256": mutated_artifacts.projection.source_sha256 != candidate.source_sha256,
            "isr_content_hash": mutated_artifacts.projection.revision.content_hash != candidate.isr_content_hash,
            "plan_hash": sha256_json(mutated_artifacts.plan.model_dump(mode="json")) != candidate.plan_hash,
            "artifact_bundle_hash": mutated_artifacts.repo.content_hash != candidate.artifact_bundle_hash,
            "runtime_report_hash": mutated_report.report_hash != candidate.runtime_report_hash,
        }
        stale = stale_evidence_problems(
            candidate,
            source_sha256=mutated_artifacts.projection.source_sha256,
            requirement_graph_hash=candidate.requirement_graph_hash,
            isr_content_hash=mutated_artifacts.projection.revision.content_hash,
            plan_hash=sha256_json(mutated_artifacts.plan.model_dump(mode="json")),
            artifact_bundle_hash=mutated_artifacts.repo.content_hash,
            runtime_report_hash=mutated_report.report_hash,
        )
        mutation_detail = {
            "mutated_role": {"from": "payroll_approver", "to": "payroll_admin"},
            "changed_hashes": changed,
            "mutated_runtime_passed": mutated_report.passed,
            "stale_evidence_problems": stale,
        }
        if not all(changed.values()):
            mutation_problems.append(
                "a policy mutation did not change every candidate binding hash: "
                f"{ {k: v for k, v in changed.items() if not v} }"
            )
        if not mutated_report.passed:
            mutation_problems.append("the mutated candidate did not pass its own adversarial suite")
        if not stale:
            mutation_problems.append("the prior candidate's evidence still verified against the mutated candidate")
    except Exception as exc:  # noqa: BLE001 - the gate records the failure reason
        mutation_problems.append(f"the mutation case failed to execute: {exc}")
        mutation_detail = {"error": str(exc)}
    gates.append(GateResult(
        gate="mutation_sensitivity",
        passed=not mutation_problems,
        detail="a policy mutation invalidates the previous candidate evidence"
        if not mutation_problems else "; ".join(mutation_problems),
    ))
    problems.extend(mutation_problems)

    rust_passed, rust_detail = _rust_negative_control(artifacts.plan)
    gates.append(GateResult(
        gate="rust_negative_control",
        passed=rust_passed,
        detail=rust_detail,
    ))
    if not rust_passed:
        problems.append(f"rust negative control: {rust_detail}")

    negative_control = {
        "backend": "rust-axum",
        "backend_version": "1.4.0",
        "rejected": rust_passed,
        "reason": rust_detail,
    }
    _write_evidence(
        evidence_path,
        artifacts,
        candidate,
        runtime_report,
        mutation_detail,
        negative_control,
    )

    verdict = VERDICT_CERTIFIED if not problems else VERDICT_NOT_CERTIFIED
    ledger = EvidenceLedger(str(evidence_path / LEDGER_NAME))
    record_hash = ledger.append({
        "schema_id": TRIAL_SCHEMA_ID,
        "schema_version": TRIAL_SCHEMA_VERSION,
        "candidate_id": candidate.candidate_id,
        "manifest_hash": candidate.manifest_hash,
        "verdict": verdict,
        "gates": [gate.as_dict() for gate in gates],
        "source_sha256": candidate.source_sha256,
        "requirement_graph_hash": candidate.requirement_graph_hash,
        "isr_content_hash": candidate.isr_content_hash,
        "plan_hash": candidate.plan_hash,
        "artifact_bundle_hash": candidate.artifact_bundle_hash,
        "runtime_report_hash": candidate.runtime_report_hash,
        "corpus_hash": candidate.corpus_hash,
    })

    verification = verify_authorization_evidence(str(evidence_path))
    gates.append(GateResult(
        gate="independent_verification",
        passed=verification.ok,
        detail="independent verification replayed every binding"
        if verification.ok else "; ".join(verification.problems),
    ))
    problems.extend(verification.problems)
    if problems:
        verdict = VERDICT_NOT_CERTIFIED

    if not keep_evidence:
        shutil.rmtree(workdir, ignore_errors=True)

    return AuthorizationCampaignResult(
        verdict=verdict,
        candidate_id=candidate.candidate_id,
        manifest_hash=candidate.manifest_hash,
        gates=tuple(gates),
        problems=tuple(problems),
        evidence_dir=str(evidence_path),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the authorization certification lane")
    parser.add_argument(
        "--evidence-dir",
        default="release/evidence/authorization",
        help="directory that receives the candidate evidence and the ledger",
    )
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="skip dependency installation (the environment must already provide them)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = run_authorization_campaign(
        args.evidence_dir,
        install=not args.no_install,
    )
    print(json.dumps(result.as_dict(), indent=2))
    for gate in result.gates:
        status = "PASS" if gate.passed else "FAIL"
        print(f"{status} {gate.gate}: {gate.detail}")
    print(f"VERDICT: {result.verdict}")
    return 0 if result.certified else 1


if __name__ == "__main__":
    raise SystemExit(main())
