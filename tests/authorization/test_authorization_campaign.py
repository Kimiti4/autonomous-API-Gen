"""The source-bound authorization certification lane: contract tests.

These tests are the lane's own acceptance criteria. They run the lane once
(the expensive part: the generated application installs and runs its own
adversarial suite) and then verify the negative cases against the evidence it
produced: stale candidate evidence, a tampered ledger, a missing runtime
report, and the Rust negative control.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from certification.authorization.candidate import REQUIRED_ADVERSARIAL_TESTS
from certification.authorization.campaign import (
    VERDICT_CERTIFIED,
    VERDICT_NOT_CERTIFIED,
    run_authorization_campaign,
)
from certification.authorization.corpus import CorpusError, validate_workload
from certification.authorization.verifier import verify_authorization_evidence
from certification.authorization.workloads import (
    AUTHORIZATION_CORPUS,
    AUTHORIZATION_CORPUS_HASH,
    PAYROLL_AUTHORIZATION_WORKLOAD,
)
from certification.corpus.corpus import default_corpus


@pytest.fixture(scope="module")
def campaign_run(tmp_path_factory) -> tuple[Path, object]:
    evidence_dir = tmp_path_factory.mktemp("authorization-evidence")
    result = run_authorization_campaign(str(evidence_dir))
    return evidence_dir, result


def test_campaign_certifies_only_when_every_gate_passes(campaign_run) -> None:
    _, result = campaign_run
    assert result.verdict == VERDICT_CERTIFIED, result.problems
    assert not result.problems
    passed = {gate.gate for gate in result.gates if gate.passed}
    assert passed == {
        "source_binding",
        "candidate_binding",
        "runtime_enforcement",
        "mutation_sensitivity",
        "rust_negative_control",
        "independent_verification",
    }


def test_generated_application_executed_the_adversarial_suite(campaign_run) -> None:
    evidence_dir, _ = campaign_run
    report = json.loads((evidence_dir / "runtime-report.json").read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert report["failed"] == 0
    for name in REQUIRED_ADVERSARIAL_TESTS:
        assert name in report["passed_tests"]
    assert not report["missing_required"]


def test_candidate_manifest_binds_source_to_runtime_report(campaign_run) -> None:
    evidence_dir, result = campaign_run
    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_sha256"]
    assert manifest["requirement_graph_hash"]
    assert manifest["isr_content_hash"]
    assert manifest["plan_hash"]
    assert manifest["artifact_bundle_hash"]
    assert manifest["runtime_report_hash"]
    assert manifest["policy_ids"] == ["security:payroll-approver"]
    assert manifest["manifest_hash" if "manifest_hash" in manifest else "candidate_id"]
    assert result.manifest_hash


def test_mutation_invalidated_the_previous_candidate_evidence(campaign_run) -> None:
    evidence_dir, _ = campaign_run
    mutation = json.loads((evidence_dir / "mutation.json").read_text(encoding="utf-8"))
    assert all(mutation["changed_hashes"].values())
    assert mutation["mutated_runtime_passed"] is True
    assert mutation["stale_evidence_problems"]


def test_rust_negative_control_refused_the_authorization_obligation(campaign_run) -> None:
    evidence_dir, _ = campaign_run
    control = json.loads((evidence_dir / "negative-control.json").read_text(encoding="utf-8"))
    assert control["backend"] == "rust-axum"
    assert control["rejected"] is True
    assert "authorization_policies" in control["reason"]


def test_stale_candidate_evidence_is_refused(campaign_run, tmp_path: Path) -> None:
    evidence_dir, _ = campaign_run
    stale = tmp_path / "stale"
    stale.mkdir()
    for name in (
        "manifest.json", "source.md", "requirement-graph.json", "isr.json",
        "plan.json", "bundle.json", "runtime-report.json", "mutation.json",
        "negative-control.json", "authorization-ledger.jsonl",
    ):
        (stale / name).write_text((evidence_dir / name).read_text(encoding="utf-8"), encoding="utf-8")
    manifest = json.loads((stale / "manifest.json").read_text(encoding="utf-8"))
    manifest["plan_hash"] = "0" * 64
    (stale / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    verification = verify_authorization_evidence(str(stale))
    assert verification.ok is False
    assert any("plan hash mismatch" in problem for problem in verification.problems)
    assert any("ledger does not bind" in problem for problem in verification.problems)


def test_missing_runtime_report_blocks_certification(campaign_run, tmp_path: Path) -> None:
    evidence_dir, _ = campaign_run
    broken = tmp_path / "missing-report"
    broken.mkdir()
    for name in (
        "manifest.json", "source.md", "requirement-graph.json", "isr.json",
        "plan.json", "bundle.json", "mutation.json", "negative-control.json",
        "authorization-ledger.jsonl",
    ):
        (broken / name).write_text((evidence_dir / name).read_text(encoding="utf-8"), encoding="utf-8")

    verification = verify_authorization_evidence(str(broken))
    assert verification.ok is False
    assert any("runtime-report.json" in problem for problem in verification.problems)


def test_tampered_ledger_blocks_certification(campaign_run, tmp_path: Path) -> None:
    evidence_dir, _ = campaign_run
    tampered = tmp_path / "tampered"
    tampered.mkdir()
    for name in (
        "manifest.json", "source.md", "requirement-graph.json", "isr.json",
        "plan.json", "bundle.json", "runtime-report.json", "mutation.json",
        "negative-control.json",
    ):
        (tampered / name).write_text((evidence_dir / name).read_text(encoding="utf-8"), encoding="utf-8")
    ledger = (evidence_dir / "authorization-ledger.jsonl").read_text(encoding="utf-8")
    tampered_ledger = ledger.replace('"verdict": "CERTIFIED"', '"verdict": "NOT_CERTIFIED"', 1)
    (tampered / "authorization-ledger.jsonl").write_text(tampered_ledger, encoding="utf-8")

    verification = verify_authorization_evidence(str(tampered))
    assert verification.ok is False
    assert any("ledger chain" in problem for problem in verification.problems)


def test_policy_the_source_does_not_authorise_is_refused() -> None:
    workload = PAYROLL_AUTHORIZATION_WORKLOAD
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
        PAYROLL_AUTHORIZATION_WORKLOAD.__class__(
            **{
                **{field: getattr(PAYROLL_AUTHORIZATION_WORKLOAD, field)
                   for field in PAYROLL_AUTHORIZATION_WORKLOAD.__dataclass_fields__},
                "source_text": PAYROLL_AUTHORIZATION_WORKLOAD.source_text + "\n- An extra line.\n",
            }
        ),
    ))
    assert changed != AUTHORIZATION_CORPUS_HASH


def test_general_campaign_a_scope_is_unchanged() -> None:
    """The authorization lane does not alter the 39 x 2 Campaign A matrix."""
    campaign_workloads = default_corpus()
    assert len(campaign_workloads) == 39
    authorization_ids = {workload.workload_id for workload in AUTHORIZATION_CORPUS}
    assert not authorization_ids & {workload.intent for workload in campaign_workloads}
