"""The source-bound authorization certification lane.

The lane proves one thing per workload: that a reviewed source requirement,
bound through an approval to a typed ISR policy, reaches a generated
application whose own runtime enforces it, and that the whole chain is
candidate-bound.

Gates, per workload:

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
    Every policy mutation the corpus declares changes the source, ISR, plan,
    bundle, and runtime report hashes; reusing the previous candidate's
    evidence fails.
``rust_negative_control``
    The same candidate is refused by the Rust backend with a precise
    unsupported-semantics reason. No Rust pass is inferred.
``independent_verification``
    An independent verifier replays the bindings from the persisted artifacts.

Outcomes are never collapsed into a generic pass. Every workload reports one
verdict per backend:

``CERTIFIED``
    The backend enforced the policy and the candidate's evidence verified.
``UNSUPPORTED_FAIL_CLOSED``
    The backend refused the authorization obligation with a precise reason.
``NOT_CERTIFIED``
    Anything else: a failed gate, a missing binding, or an unverifiable
    candidate.
"""
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from certification.authorization.candidate import (
    REQUIRED_ADVERSARIAL_TESTS,
    AuthorizationCandidate,
    build_candidate,
    canonical_json,
    sha256_json,
    stale_evidence_problems,
)
from certification.authorization.corpus import AuthorizationWorkload
from certification.authorization.runtime import RuntimeReport, run_generated_suite
from certification.authorization.verifier import verify_authorization_evidence
from certification.authorization.workloads import (
    AUTHORIZATION_CORPUS,
    AUTHORIZATION_CORPUS_HASH,
    CORPUS_ID,
    CORPUS_METADATA,
    CORPUS_VERSION,
)
from certification.evidence.ledger import EvidenceLedger

VERDICT_CERTIFIED = "CERTIFIED"
VERDICT_UNSUPPORTED_FAIL_CLOSED = "UNSUPPORTED_FAIL_CLOSED"
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
TRIAL_SCHEMA_VERSION = "1.1.0"

LEDGER_NAME = "authorization-ledger.jsonl"
COVERAGE_NAME = "coverage.json"
WORKLOADS_DIRNAME = "workloads"

PYTHON_BACKEND = "python-fastapi"
RUST_BACKEND = "rust-axum"


@dataclass(frozen=True)
class GateResult:
    gate: str
    passed: bool
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {"gate": self.gate, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class BackendOutcome:
    """The verdict for one (workload, backend) pair."""

    workload_id: str
    backend: str
    backend_version: str
    verdict: str
    detail: str
    policy_ids: tuple[str, ...] = ()
    bound_operations: tuple[dict[str, Any], ...] = ()
    runtime_report_hash: str = ""
    manifest_hash: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "workload_id": self.workload_id,
            "backend": self.backend,
            "backend_version": self.backend_version,
            "verdict": self.verdict,
            "detail": self.detail,
            "policy_ids": list(self.policy_ids),
            "bound_operations": [dict(binding) for binding in self.bound_operations],
            "runtime_report_hash": self.runtime_report_hash,
            "manifest_hash": self.manifest_hash,
        }


@dataclass(frozen=True)
class WorkloadOutcome:
    """Every outcome for one workload."""

    workload_id: str
    python: BackendOutcome
    rust: BackendOutcome
    gates: tuple[GateResult, ...]
    mutations: tuple[dict[str, Any], ...]
    problems: tuple[str, ...]
    candidate: AuthorizationCandidate | None = None

    @property
    def certified(self) -> bool:
        return self.python.verdict == VERDICT_CERTIFIED

    def as_dict(self) -> dict[str, Any]:
        return {
            "workload_id": self.workload_id,
            "python": self.python.as_dict(),
            "rust": self.rust.as_dict(),
            "gates": [gate.as_dict() for gate in self.gates],
            "mutations": [dict(mutation) for mutation in self.mutations],
            "problems": list(self.problems),
        }


@dataclass(frozen=True)
class AuthorizationCampaignResult:
    verdict: str
    corpus_hash: str
    workloads: tuple[WorkloadOutcome, ...]
    problems: tuple[str, ...]
    evidence_dir: str

    @property
    def certified(self) -> bool:
        return self.verdict == VERDICT_CERTIFIED

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "corpus_hash": self.corpus_hash,
            "workloads": [workload.as_dict() for workload in self.workloads],
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


def _rust_outcome(workload: AuthorizationWorkload, plan: Any) -> BackendOutcome:
    """Submit the same candidate to Rust; it must refuse the obligation."""
    from compiler.backends.rust_axum import RustAxumBackend
    from compiler.core.capabilities import UnsupportedSemanticsError

    try:
        RustAxumBackend().compile(plan)
    except UnsupportedSemanticsError as exc:
        message = str(exc)
        if "authorization_policies" in message:
            return BackendOutcome(
                workload_id=workload.workload_id,
                backend=RUST_BACKEND,
                backend_version="1.4.0",
                verdict=VERDICT_UNSUPPORTED_FAIL_CLOSED,
                detail=message,
            )
        return BackendOutcome(
            workload_id=workload.workload_id,
            backend=RUST_BACKEND,
            backend_version="1.4.0",
            verdict=VERDICT_NOT_CERTIFIED,
            detail=f"rust refused the candidate without citing authorization_policies: {message}",
        )
    return BackendOutcome(
        workload_id=workload.workload_id,
        backend=RUST_BACKEND,
        backend_version="1.4.0",
        verdict=VERDICT_NOT_CERTIFIED,
        detail="rust accepted a candidate carrying an authorization obligation",
    )


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


def _run_workload(
    workload: AuthorizationWorkload,
    evidence_root: Path,
    workdir: Path,
    *,
    install: bool,
    install_state: dict[str, bool],
) -> WorkloadOutcome:
    """Run every gate for one workload and write its evidence."""
    gates: list[GateResult] = []
    problems: list[str] = []
    evidence_dir = evidence_root / WORKLOADS_DIRNAME / workload.workload_id

    artifacts = build_candidate_artifacts(workload)
    source_problems = _source_binding_problems(workload, artifacts)
    gates.append(GateResult(
        gate="source_binding",
        passed=not source_problems,
        detail="the source declaration, approval, ISR, and plan agree"
        if not source_problems else "; ".join(source_problems),
    ))
    problems.extend(source_problems)

    should_install = install and not install_state.get("installed", False)
    runtime_report = run_generated_suite(
        artifacts.repo.files,
        workdir / workload.workload_id / "candidate",
        REQUIRED_ADVERSARIAL_TESTS,
        install=should_install,
    )
    if should_install:
        install_state["installed"] = True

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

    mutation_records: list[dict[str, Any]] = []
    mutation_problems: list[str] = []
    for case in workload.mutations:
        record, case_problems = _run_mutation(
            case,
            workload,
            candidate,
            workdir / workload.workload_id / f"mutation-{case.kind}",
            install=install,
            install_state=install_state,
        )
        mutation_records.append(record)
        mutation_problems.extend(case_problems)
    if workload.mutations:
        gates.append(GateResult(
            gate="mutation_sensitivity",
            passed=not mutation_problems,
            detail="every policy mutation invalidates the previous candidate evidence"
            if not mutation_problems else "; ".join(mutation_problems),
        ))
        problems.extend(mutation_problems)

    rust = _rust_outcome(workload, artifacts.plan)
    gates.append(GateResult(
        gate="rust_negative_control",
        passed=rust.verdict == VERDICT_UNSUPPORTED_FAIL_CLOSED,
        detail=rust.detail,
    ))
    if rust.verdict != VERDICT_UNSUPPORTED_FAIL_CLOSED:
        problems.append(f"rust negative control: {rust.detail}")

    negative_control = {
        "backend": RUST_BACKEND,
        "backend_version": rust.backend_version,
        "rejected": rust.verdict == VERDICT_UNSUPPORTED_FAIL_CLOSED,
        "verdict": rust.verdict,
        "reason": rust.detail,
    }
    mutation_record = {
        "cases": mutation_records,
        "changed_hashes": all(
            all(case["changed_hashes"].values()) for case in mutation_records
        ) if mutation_records else False,
        "stale_evidence_problems": [
            problem
            for case in mutation_records
            for problem in case["stale_evidence_problems"]
        ],
        "mutated_runtime_passed": all(
            case["mutated_runtime_passed"] for case in mutation_records
        ) if mutation_records else False,
    }
    _write_evidence(
        evidence_dir,
        artifacts,
        candidate,
        runtime_report,
        mutation_record,
        negative_control,
    )

    python_verdict = VERDICT_CERTIFIED if not problems else VERDICT_NOT_CERTIFIED
    python_outcome = BackendOutcome(
        workload_id=workload.workload_id,
        backend=PYTHON_BACKEND,
        backend_version="1.4.0",
        verdict=python_verdict,
        detail="; ".join(problems) if problems else "every gate passed",
        policy_ids=candidate.policy_ids,
        bound_operations=candidate.bound_operations,
        runtime_report_hash=runtime_report.report_hash,
        manifest_hash=candidate.manifest_hash,
    )
    return WorkloadOutcome(
        workload_id=workload.workload_id,
        python=python_outcome,
        rust=rust,
        gates=tuple(gates),
        mutations=tuple(mutation_records),
        problems=tuple(problems),
        candidate=candidate,
    )


def _run_mutation(
    case: Any,
    workload: AuthorizationWorkload,
    candidate: AuthorizationCandidate,
    workdir: Path,
    *,
    install: bool,
    install_state: dict[str, bool],
) -> tuple[dict[str, Any], list[str]]:
    """Run one policy mutation and prove the previous evidence is stale."""
    problems: list[str] = []
    record: dict[str, Any] = {
        "kind": case.kind,
        "description": case.description,
        "changed_hashes": {},
        "stale_evidence_problems": [],
        "mutated_runtime_passed": False,
    }
    try:
        mutated_workload = case.apply(workload)
        mutated_artifacts = build_candidate_artifacts(mutated_workload)
        mutated_report = run_generated_suite(
            mutated_artifacts.repo.files,
            workdir,
            REQUIRED_ADVERSARIAL_TESTS,
            install=install and not install_state.get("installed", False),
        )
        install_state["installed"] = True
        mutated_plan_hash = sha256_json(mutated_artifacts.plan.model_dump(mode="json"))
        changed = {
            "source_sha256": mutated_artifacts.projection.source_sha256 != candidate.source_sha256,
            "isr_content_hash": mutated_artifacts.projection.revision.content_hash != candidate.isr_content_hash,
            "plan_hash": mutated_plan_hash != candidate.plan_hash,
            "artifact_bundle_hash": mutated_artifacts.repo.content_hash != candidate.artifact_bundle_hash,
            "runtime_report_hash": mutated_report.report_hash != candidate.runtime_report_hash,
        }
        stale = stale_evidence_problems(
            candidate,
            source_sha256=mutated_artifacts.projection.source_sha256,
            requirement_graph_hash=candidate.requirement_graph_hash,
            isr_content_hash=mutated_artifacts.projection.revision.content_hash,
            plan_hash=mutated_plan_hash,
            artifact_bundle_hash=mutated_artifacts.repo.content_hash,
            runtime_report_hash=mutated_report.report_hash,
        )
        record["changed_hashes"] = changed
        record["stale_evidence_problems"] = stale
        record["mutated_runtime_passed"] = mutated_report.passed
        record["mutated"] = {
            "source_sha256": mutated_artifacts.projection.source_sha256,
            "isr_content_hash": mutated_artifacts.projection.revision.content_hash,
            "plan_hash": mutated_plan_hash,
            "artifact_bundle_hash": mutated_artifacts.repo.content_hash,
            "runtime_report_hash": mutated_report.report_hash,
        }
        if not all(changed.values()):
            problems.append(
                f"mutation {case.kind!r} did not change every candidate binding hash: "
                f"{ {key: value for key, value in changed.items() if not value} }"
            )
        if not mutated_report.passed:
            problems.append(f"mutation {case.kind!r} did not pass its own adversarial suite")
        if not stale:
            problems.append(
                f"mutation {case.kind!r} left the previous candidate's evidence valid"
            )
    except Exception as exc:  # noqa: BLE001 - the gate records the failure reason
        problems.append(f"mutation {case.kind!r} failed to execute: {exc}")
        record["error"] = str(exc)
    return record, problems


def _coverage_document(
    outcomes: Sequence[WorkloadOutcome],
    corpus_hash: str,
) -> dict[str, Any]:
    """The per-workload, per-backend coverage report."""
    rows: list[dict[str, Any]] = []
    for outcome in outcomes:
        for backend in (outcome.python, outcome.rust):
            rows.append(backend.as_dict())
    certified = [row for row in rows if row["verdict"] == VERDICT_CERTIFIED]
    fail_closed = [row for row in rows if row["verdict"] == VERDICT_UNSUPPORTED_FAIL_CLOSED]
    return {
        "schema_id": "tiannara.authorization.coverage",
        "schema_version": "1.0.0",
        "corpus_id": CORPUS_ID,
        "corpus_version": CORPUS_VERSION,
        "corpus_hash": corpus_hash,
        "workload_count": len(outcomes),
        "rows": rows,
        "summary": {
            "certified": len(certified),
            "unsupported_fail_closed": len(fail_closed),
            "not_certified": len(rows) - len(certified) - len(fail_closed),
        },
    }


def run_authorization_campaign(
    evidence_dir: str,
    workloads: Sequence[AuthorizationWorkload] = AUTHORIZATION_CORPUS,
    *,
    install: bool = True,
    keep_workdir: bool = False,
) -> AuthorizationCampaignResult:
    """Run the authorization certification lane for a set of workloads."""
    evidence_path = Path(evidence_dir)
    if evidence_path.exists():
        shutil.rmtree(evidence_path)
    evidence_path.mkdir(parents=True, exist_ok=True)
    workdir = evidence_path / "work"
    install_state: dict[str, bool] = {}

    outcomes: list[WorkloadOutcome] = []
    for workload in workloads:
        outcomes.append(_run_workload(
            workload,
            evidence_path,
            workdir,
            install=install,
            install_state=install_state,
        ))

    coverage = _coverage_document(outcomes, AUTHORIZATION_CORPUS_HASH)
    (evidence_path / COVERAGE_NAME).write_text(canonical_json(coverage), encoding="utf-8")

    ledger = EvidenceLedger(str(evidence_path / LEDGER_NAME))
    for outcome in outcomes:
        candidate = outcome.candidate
        ledger.append({
            "schema_id": TRIAL_SCHEMA_ID,
            "schema_version": TRIAL_SCHEMA_VERSION,
            "candidate_id": outcome.python.manifest_hash,
            "workload_id": outcome.workload_id,
            "manifest_hash": outcome.python.manifest_hash,
            "verdict": outcome.python.verdict,
            "python": outcome.python.as_dict(),
            "rust": outcome.rust.as_dict(),
            "gates": [gate.as_dict() for gate in outcome.gates],
            "source_sha256": candidate.source_sha256 if candidate else "",
            "isr_content_hash": candidate.isr_content_hash if candidate else "",
            "plan_hash": candidate.plan_hash if candidate else "",
            "artifact_bundle_hash": candidate.artifact_bundle_hash if candidate else "",
            "runtime_report_hash": candidate.runtime_report_hash if candidate else "",
            "corpus_hash": AUTHORIZATION_CORPUS_HASH,
        })

    verification = verify_authorization_evidence(str(evidence_path))
    problems = [problem for outcome in outcomes for problem in outcome.problems]
    problems.extend(verification.problems)
    verdict = VERDICT_CERTIFIED if not problems else VERDICT_NOT_CERTIFIED

    if not keep_workdir:
        shutil.rmtree(workdir, ignore_errors=True)

    return AuthorizationCampaignResult(
        verdict=verdict,
        corpus_hash=AUTHORIZATION_CORPUS_HASH,
        workloads=tuple(outcomes),
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
    for workload in result.workloads:
        print(
            f"{workload.workload_id}: python={workload.python.verdict} "
            f"rust={workload.rust.verdict}"
        )
        for gate in workload.gates:
            status = "PASS" if gate.passed else "FAIL"
            print(f"  {status} {gate.gate}: {gate.detail}")
    print(f"VERDICT: {result.verdict}")
    return 0 if result.certified else 1


if __name__ == "__main__":
    raise SystemExit(main())
