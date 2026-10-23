"""The source-bound authorization certification lane: contract tests.

These tests are the lane's own acceptance criteria. They run the lane once
(the expensive part: each generated application installs and runs its own
adversarial suite) and then verify the negative cases against the evidence it
produced: stale candidate evidence, a missing runtime report, a tampered
ledger, a mismatched manifest, and the Rust negative control.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from certification.authorization.candidate import (
    DECLARED_OPERATION_TESTS,
    REQUIRED_ADVERSARIAL_TESTS,
)
from certification.authorization.campaign import (
    VERDICT_CERTIFIED,
    VERDICT_NOT_CERTIFIED,
    VERDICT_UNSUPPORTED_FAIL_CLOSED,
    run_authorization_campaign,
)
from certification.authorization.corpus import CorpusError, validate_workload
from certification.authorization.verifier import verify_authorization_evidence
from certification.authorization.workloads import (
    AUTHORIZATION_CORPUS,
    AUTHORIZATION_CORPUS_HASH,
    PAYROLL_WORKLOAD,
)
from certification.corpus.corpus import default_corpus

EVIDENCE_FILES = (
    "manifest.json", "source.md", "requirement-graph.json", "isr.json",
    "plan.json", "bundle.json", "runtime-report.json", "mutation.json",
    "negative-control.json", "authorization-ledger.jsonl",
)


@pytest.fixture(scope="module")
def campaign_run(tmp_path_factory) -> tuple[Path, object]:
    evidence_dir = tmp_path_factory.mktemp("authorization-evidence")
    result = run_authorization_campaign(str(evidence_dir))
    return evidence_dir, result


def _copy_evidence(evidence_dir: Path, target: Path, workloads=None) -> Path:
    target.mkdir(parents=True, exist_ok=True)
    for name in ("coverage.json", "authorization-ledger.jsonl"):
        source = evidence_dir / name
        if source.is_file():
            shutil.copy2(source, target / name)
    workloads_dir = evidence_dir / "workloads"
    for workload_dir in (workloads or [p for p in workloads_dir.iterdir() if p.is_dir()]):
        destination = target / "workloads" / workload_dir.name
        destination.mkdir(parents=True, exist_ok=True)
        for name in EVIDENCE_FILES:
            source = workload_dir / name
            if source.is_file():
                shutil.copy2(source, destination / name)
    return target


def test_campaign_certifies_only_when_every_gate_passes(campaign_run) -> None:
    _, result = campaign_run
    assert result.verdict == VERDICT_CERTIFIED, result.problems
    assert not result.problems
    for workload in result.workloads:
        assert workload.python.verdict == VERDICT_CERTIFIED, workload.problems
        for gate in workload.gates:
            assert gate.passed, f"{workload.workload_id}: {gate.gate}: {gate.detail}"


def test_unsupported_backend_is_never_reported_as_a_pass(campaign_run) -> None:
    _, result = campaign_run
    for workload in result.workloads:
        assert workload.rust.verdict == VERDICT_UNSUPPORTED_FAIL_CLOSED
        assert workload.rust.verdict != VERDICT_CERTIFIED
        assert "authorization_policies" in workload.rust.detail


def test_coverage_reports_every_workload_and_backend(campaign_run) -> None:
    evidence_dir, result = campaign_run
    coverage = json.loads((evidence_dir / "coverage.json").read_text(encoding="utf-8"))
    rows = coverage["rows"]
    assert len(rows) == len(result.workloads) * 2
    assert {(row["workload_id"], row["backend"]) for row in rows} == {
        (workload.workload_id, backend)
        for workload in result.workloads
        for backend in ("python-fastapi", "rust-axum")
    }
    assert coverage["summary"] == {
        "certified": len(result.workloads),
        "unsupported_fail_closed": len(result.workloads),
        "not_certified": 0,
    }
    for row in rows:
        assert row["verdict"] in {
            VERDICT_CERTIFIED, VERDICT_UNSUPPORTED_FAIL_CLOSED, VERDICT_NOT_CERTIFIED
        }


def test_each_workload_covers_a_distinct_policy_pattern(campaign_run) -> None:
    _, result = campaign_run
    policy_ids = {workload.python.policy_ids for workload in result.workloads}
    assert len(policy_ids) == len(result.workloads)
    resources = {
        binding["resource"]
        for workload in result.workloads
        for binding in workload.python.bound_operations
    }
    assert len(resources) >= 3
    operations = {
        binding["operation"]
        for workload in result.workloads
        for binding in workload.python.bound_operations
    }
    assert len(operations) >= 10


def test_generated_application_executed_the_adversarial_suite(campaign_run) -> None:
    evidence_dir, result = campaign_run
    for workload in result.workloads:
        report = json.loads(
            (evidence_dir / "workloads" / workload.workload_id / "runtime-report.json")
            .read_text(encoding="utf-8")
        )
        assert report["passed"] is True, workload.workload_id
        assert report["failed"] == 0
        for name in REQUIRED_ADVERSARIAL_TESTS:
            assert name in report["passed_tests"], f"{workload.workload_id}: {name}"
        if workload.python.declared_routes:
            for name in DECLARED_OPERATION_TESTS:
                assert name in report["passed_tests"], f"{workload.workload_id}: {name}"
        assert not report["missing_required"]


def test_declared_operation_workload_is_candidate_bound(campaign_run) -> None:
    """The declared route metadata comes from the plan and is emitted verbatim."""
    from compiler.core.declared_api import declared_routes
    from compiler.core.plan import CompilationPlan

    evidence_dir, result = campaign_run
    declared = [w for w in result.workloads if w.python.declared_routes]
    assert len(declared) == 1
    workload = declared[0]
    workload_dir = evidence_dir / "workloads" / workload.workload_id
    manifest = json.loads((workload_dir / "manifest.json").read_text(encoding="utf-8"))
    plan = CompilationPlan.model_validate(
        json.loads((workload_dir / "plan.json").read_text(encoding="utf-8"))
    )
    expected = [route.as_dict() for route in declared_routes(plan)]
    assert len(expected) == 4
    assert manifest["declared_routes"] == expected

    bundle = json.loads((workload_dir / "bundle.json").read_text(encoding="utf-8"))
    module = bundle["app/api/declared.py"]
    for route in expected:
        assert f"{route['path']!r}," in module
        assert f"methods=[{route['method']!r}]" in module
        assert f"OPERATION_POLICIES[{route['operation_id']!r}]" in module
        assert f"resource={route['resource']!r}" in module

    report = json.loads(
        (workload_dir / "runtime-report.json").read_text(encoding="utf-8")
    )
    assert report["bundle_hash"] == manifest["artifact_bundle_hash"]


def test_declared_route_tampering_is_refused(campaign_run, tmp_path: Path) -> None:
    evidence_dir, result = campaign_run
    declared = next(w for w in result.workloads if w.python.declared_routes)
    tampered = _copy_evidence(evidence_dir, tmp_path / "declared-route-tampered")
    manifest_path = tampered / "workloads" / declared.workload_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["declared_routes"][0]["path"] = "/tampered"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    verification = verify_authorization_evidence(str(tampered))
    assert verification.ok is False
    assert any(
        "declared routes do not match" in problem for problem in verification.problems
    )


def test_bundle_that_drops_a_declared_guard_is_refused(campaign_run, tmp_path: Path) -> None:
    evidence_dir, result = campaign_run
    declared = next(w for w in result.workloads if w.python.declared_routes)
    tampered = _copy_evidence(evidence_dir, tmp_path / "declared-guard-tampered")
    bundle_path = tampered / "workloads" / declared.workload_id / "bundle.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    operation_id = declared.python.declared_routes[0]["operation_id"]
    guard = f"OPERATION_POLICIES[{operation_id!r}]"
    bundle["app/api/declared.py"] = bundle["app/api/declared.py"].replace(guard, "None")
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    verification = verify_authorization_evidence(str(tampered))
    assert verification.ok is False
    assert any(
        "does not emit the manifest's declared routes" in problem
        for problem in verification.problems
    )


def test_runtime_report_is_bound_to_the_exact_generated_candidate(campaign_run) -> None:
    """The executed artifact must be the candidate's bundle, not a lookalike."""
    evidence_dir, result = campaign_run
    for workload in result.workloads:
        workload_dir = evidence_dir / "workloads" / workload.workload_id
        manifest = json.loads((workload_dir / "manifest.json").read_text(encoding="utf-8"))
        report = json.loads((workload_dir / "runtime-report.json").read_text(encoding="utf-8"))
        assert report["bundle_hash"] == manifest["artifact_bundle_hash"], workload.workload_id


def test_runtime_report_from_another_candidate_is_refused(campaign_run, tmp_path: Path) -> None:
    evidence_dir, _ = campaign_run
    swapped = _copy_evidence(evidence_dir, tmp_path / "swapped")
    payroll = swapped / "workloads" / "payroll-authorization"
    orders_report = json.loads(
        (swapped / "workloads" / "orders-authorization" / "runtime-report.json")
        .read_text(encoding="utf-8")
    )
    (payroll / "runtime-report.json").write_text(json.dumps(orders_report), encoding="utf-8")

    verification = verify_authorization_evidence(str(swapped))
    assert verification.ok is False
    assert any("runtime report hash mismatch" in problem for problem in verification.problems)


def test_every_mutation_kind_invalidated_the_previous_evidence(campaign_run) -> None:
    evidence_dir, result = campaign_run
    kinds = set()
    for workload in result.workloads:
        record = json.loads(
            (evidence_dir / "workloads" / workload.workload_id / "mutation.json")
            .read_text(encoding="utf-8")
        )
        assert record["cases"], workload.workload_id
        for case in record["cases"]:
            kinds.add(case["kind"])
            assert all(case["changed_hashes"].values()), f"{workload.workload_id}: {case['kind']}"
            assert case["stale_evidence_problems"], f"{workload.workload_id}: {case['kind']}"
            assert case["mutated_runtime_passed"] is True
    assert kinds == {"role", "action", "resource", "policy", "attribute"}


def test_stale_candidate_evidence_is_refused(campaign_run, tmp_path: Path) -> None:
    evidence_dir, _ = campaign_run
    stale = _copy_evidence(evidence_dir, tmp_path / "stale")
    manifest_path = stale / "workloads" / "payroll-authorization" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["plan_hash"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    verification = verify_authorization_evidence(str(stale))
    assert verification.ok is False
    assert any("plan hash mismatch" in problem for problem in verification.problems)
    assert any("does not bind this candidate manifest" in problem for problem in verification.problems)


def test_mismatched_manifest_is_refused(campaign_run, tmp_path: Path) -> None:
    """A manifest that claims policies the plan does not carry must be refused."""
    evidence_dir, _ = campaign_run
    mismatched = _copy_evidence(evidence_dir, tmp_path / "mismatched")
    manifest_path = mismatched / "workloads" / "payroll-authorization" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["policy_ids"] = ["security:not-in-the-plan"]
    manifest["bound_operations"] = [{
        "policy_id": "security:not-in-the-plan",
        "service_id": "service:payroll",
        "operation": "employee.read",
        "resource": "Employee",
        "effect": "allow",
        "roles": ["payroll_approver"],
        "rule_id": "invented",
    }]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    verification = verify_authorization_evidence(str(mismatched))
    assert verification.ok is False
    assert any("policy ids do not match" in problem for problem in verification.problems)
    assert any("bindings do not match" in problem for problem in verification.problems)


def test_missing_runtime_report_blocks_certification(campaign_run, tmp_path: Path) -> None:
    evidence_dir, _ = campaign_run
    broken = _copy_evidence(evidence_dir, tmp_path / "missing-report")
    (broken / "workloads" / "payroll-authorization" / "runtime-report.json").unlink()

    verification = verify_authorization_evidence(str(broken))
    assert verification.ok is False
    assert any("runtime-report.json" in problem for problem in verification.problems)


def test_tampered_ledger_blocks_certification(campaign_run, tmp_path: Path) -> None:
    evidence_dir, _ = campaign_run
    tampered = _copy_evidence(evidence_dir, tmp_path / "tampered")
    ledger = tampered / "authorization-ledger.jsonl"
    content = ledger.read_text(encoding="utf-8")
    ledger.write_text(content.replace('"verdict": "CERTIFIED"', '"verdict": "NOT_CERTIFIED"', 1), encoding="utf-8")

    verification = verify_authorization_evidence(str(tampered))
    assert verification.ok is False
    assert any("ledger chain" in problem for problem in verification.problems)


def test_policy_the_source_does_not_authorise_is_refused() -> None:
    workload = PAYROLL_WORKLOAD
    tampered = workload.__class__(
        **{
            **{field: getattr(workload, field) for field in workload.__dataclass_fields__},
            "source_text": workload.source_text.replace("payroll_approver", "payroll_admin"),
        }
    )
    with pytest.raises(CorpusError):
        validate_workload(tampered)


def test_authorization_corpus_is_versioned_and_hashed() -> None:
    from certification.authorization.corpus import corpus_hash

    assert AUTHORIZATION_CORPUS_HASH == corpus_hash(AUTHORIZATION_CORPUS)
    assert len(AUTHORIZATION_CORPUS_HASH) == 64
    changed = corpus_hash((
        PAYROLL_WORKLOAD.__class__(
            **{
                **{field: getattr(PAYROLL_WORKLOAD, field)
                   for field in PAYROLL_WORKLOAD.__dataclass_fields__},
                "source_text": PAYROLL_WORKLOAD.source_text + "\n- An extra line.\n",
            }
        ),
    ))
    assert changed != AUTHORIZATION_CORPUS_HASH


def test_corpus_carries_exactly_one_declared_operation_workload() -> None:
    declared = [w for w in AUTHORIZATION_CORPUS if w.declared_operations]
    assert len(declared) == 1
    workload = declared[0]
    assert workload.workload_id == "payroll-declared-api-authorization"
    assert len(workload.declared_operations) == 4
    assert {operation.method for operation in workload.declared_operations} == {
        "GET", "POST", "DELETE",
    }


def test_general_campaign_a_scope_is_unchanged() -> None:
    """The authorization lane does not alter the 39 x 2 Campaign A matrix."""
    campaign_workloads = default_corpus()
    assert len(campaign_workloads) == 39
    authorization_ids = {workload.workload_id for workload in AUTHORIZATION_CORPUS}
    assert not authorization_ids & {workload.intent for workload in campaign_workloads}
