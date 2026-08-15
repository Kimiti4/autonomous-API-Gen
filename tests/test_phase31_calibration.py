"""Phase-31 -- BackendCalibrationHarness (calibration slice).

Exercises the real Go + FastAPI backends through the harness over the default
corpus, end-to-end, hermetically (no Go toolchain expected in CI -> runtime is
degrade-tier, but static verification is deterministic). Asserts:
  * both backends are selected per ISR (select-all);
  * per-backend output dirs are namespaced (no Dockerfile collision);
  * both pass static verification;
  * evidence is appended to the ledger (one tamper-evident record per backend);
  * the report exposes the gate semantics and success rate.
"""
from __future__ import annotations

import shutil

from tiannara.application.compiler.go_hexagonal_backend import GoHexagonalBackend
from tiannara.application.harness.calibration.corpus import DEFAULT_CORPUS
from tiannara.application.harness.calibration.harness import (
    GATE_SEMANTICS,
    BackendCalibrationHarness,
    build_calibration_registry,
    verification_report_error,
)
from tiannara.application.harness.calibration.report import CalibrationReport
from tiannara.domain.models.evidence import Verdict
from tiannara.infrastructure.ledger.jsonl_evidence_ledger import JsonlEvidenceLedger


def _hermetic_which(*_args, **_kwargs):
    return None  # simulate no Go (and no git) on PATH


def test_harness_compiles_each_isr_to_each_backend(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", _hermetic_which)
    ledger = JsonlEvidenceLedger(tmp_path / "evidence.jsonl")
    harness = BackendCalibrationHarness(build_calibration_registry(), ledger)
    report = harness.calibrate(out_root=tmp_path / "out")

    assert isinstance(report, CalibrationReport)
    assert report.corpus_size == len(DEFAULT_CORPUS)
    assert set(report.backends_tested) == {"fastapi_hexagonal", "go_hexagonal"}
    # One outcome per (corpus model x backend).
    assert report.total == len(DEFAULT_CORPUS) * len(report.backends_tested)
    assert report.passed == report.total  # static verification passes for both
    assert report.success_rate == 1.0


def test_harness_namespaces_bundles_per_backend(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", _hermetic_which)
    ledger = JsonlEvidenceLedger(tmp_path / "evidence.jsonl")
    harness = BackendCalibrationHarness(build_calibration_registry(), ledger)
    report = harness.calibrate(out_root=tmp_path / "out")

    roots = {o.backend_id: o.bundle_path for o in report.outcomes}
    assert roots["fastapi_hexagonal"] is not None
    assert roots["go_hexagonal"] is not None
    # Each backend writes into its own dir -> root-level Dockerfile collision avoided.
    assert roots["fastapi_hexagonal"] != roots["go_hexagonal"]
    assert report.outcomes[0].bundle_path.is_dir()


def test_harness_records_tamper_evident_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", _hermetic_which)
    ledger_path = tmp_path / "evidence.jsonl"
    ledger = JsonlEvidenceLedger(ledger_path)
    harness = BackendCalibrationHarness(build_calibration_registry(), ledger)
    report = harness.calibrate(out_root=tmp_path / "out")

    # One CertificationEvidence per backend outcome, hash-chained.
    assert len(ledger.all()) == report.total
    assert ledger.verify_chain() is True
    for outcome in report.outcomes:
        assert outcome.evidence.genome_id.startswith("pre-evolution:")
        assert outcome.evidence.isr_hash == outcome.isr_hash
        assert outcome.evidence.backend_name == outcome.backend_id
        assert outcome.evidence.verdict is Verdict.PASS


def test_harness_runtime_degrades_when_toolchain_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", _hermetric_which if False else _hermetic_which)
    ledger = JsonlEvidenceLedger(tmp_path / "evidence.jsonl")
    harness = BackendCalibrationHarness(build_calibration_registry(), ledger)
    report = harness.calibrate(out_root=tmp_path / "out")

    for outcome in report.outcomes:
        # No Go toolchain -> Go runtime skipped, not faked.
        if outcome.backend_id == "go_hexagonal":
            assert outcome.runtime_status == "skipped:toolchain_absent"
            assert outcome.test_run is None
            # Static pass still holds despite skipped runtime.
            assert outcome.ok is True
        else:
            # FastAPI now declares a runtime_image+test_command (R2.4.0a), so it
            # degrades to the same honest skip as Go -- never a fake "ran".
            assert outcome.runtime_status == "skipped:toolchain_absent"
    assert report.runtime_coverage == 0.0
    assert "toolchain" in report.gate_semantics


def test_go_and_fastapi_are_distinct_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", _hermetic_which)
    ledger = JsonlEvidenceLedger(tmp_path / "evidence.jsonl")
    harness = BackendCalibrationHarness(build_calibration_registry(), ledger)
    report = harness.calibrate(out_root=tmp_path / "out")

    by_backend = {}
    for o in report.outcomes:
        by_backend[o.backend_id] = o
    go_artifacts = set(by_backend["go_hexagonal"].evidence.model_extra or {})
    # Distinct file schemas (Go: module-rooted; FastAPI: slug-rooted).
    go_files = by_backend["go_hexagonal"].bundle_path
    assert (go_files / "go.mod").exists()
    fastapi_files = by_backend["fastapi_hexagonal"].bundle_path
    assert (fastapi_files / "order_management" / "main.py").exists()


def test_verification_report_error_helper():
    from tiannara.application.compiler.verification import BundleVerificationReport

    assert verification_report_error(None) is None
    assert verification_report_error(BundleVerificationReport(ok=True)) is None
    bad = BundleVerificationReport(ok=False, missing_files=["Dockerfile"])
    assert verification_report_error(bad) == "missing: ['Dockerfile']"
    bad2 = BundleVerificationReport(ok=False, syntax_errors=["go.mod: broken"])
    assert verification_report_error(bad2) == "syntax: ['go.mod: broken']"
    bare = BundleVerificationReport(ok=False)
    assert verification_report_error(bare) == "verification failed"


def test_calibrate_cli_subcommand(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", _hermetic_which)
    from tiannara.interfaces.cli.main import main

    rc = main(
        [
            "calibrate",
            "--out",
            str(tmp_path / "cli-out"),
            "--ledger",
            str(tmp_path / "cli-evidence.jsonl"),
        ]
    )
    assert rc == 0
    assert (tmp_path / "cli-out" / "go_hexagonal" / "go.mod").exists()
    ledger = JsonlEvidenceLedger(tmp_path / "cli-evidence.jsonl")
    assert len(ledger.all()) == _expected_records()
    assert ledger.verify_chain() is True


def _expected_records() -> int:
    # 2 calibrated backends (FastAPI + Go) per corpus model.
    return len(DEFAULT_CORPUS) * 2
