"""Fail-closed contract tests for the W01-W22 remediation register.

The register is the plan's source of truth, so these tests prove two things:
the real register is well-formed, and the validator rejects every class of
overclaim. A validator that cannot reject a broken register would itself be a
fail-open defect.
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
import sys

import pytest

from certification.remediation.register import (
    DEFECTS,
    SCHEMA_ID,
    SCHEMA_VERSION,
    WORK_PACKAGES,
    CertificationTier,
    Defect,
    DefectStatus,
    Evidence,
    EvidenceKind,
    Status,
    WorkPackage,
    main,
    register_payload,
    validate_register,
)

EXPECTED_IDS = [f"W{index:02d}" for index in range(1, 23)]


def _replace_package(register_id: str, **changes) -> tuple[WorkPackage, ...]:
    return tuple(
        dataclasses.replace(package, **changes) if package.id == register_id else package
        for package in WORK_PACKAGES
    )


def _problems(packages=WORK_PACKAGES, defects=DEFECTS, repo_root=None) -> list[str]:
    if repo_root is None:
        return validate_register(packages, defects)
    return validate_register(packages, defects, repo_root=repo_root)


def test_register_validates_clean() -> None:
    assert _problems() == []


def test_schema_identity_is_explicit() -> None:
    payload = register_payload()
    assert payload["schema_id"] == SCHEMA_ID == "esap.remediation.register"
    assert payload["schema_version"] == SCHEMA_VERSION == "1.0.0"


def test_exactly_w01_through_w22_in_order() -> None:
    assert [package.id for package in WORK_PACKAGES] == EXPECTED_IDS
    assert _problems(_replace_package("W22", id="W23")) == [
        f"work package ids must be exactly W01..W22 in order; got {EXPECTED_IDS[:-1] + ['W23']}"
    ]


def test_missing_work_package_is_rejected() -> None:
    problems = _problems(tuple(package for package in WORK_PACKAGES if package.id != "W11"))
    assert any("must be exactly W01..W22" in problem for problem in problems)


def test_duplicate_work_package_is_rejected() -> None:
    duplicated = WORK_PACKAGES + (WORK_PACKAGES[0],)
    problems = _problems(duplicated)
    assert any("duplicate work package id: W01" in problem for problem in problems)


def test_every_package_has_requirement_gate_and_evidence() -> None:
    for package in WORK_PACKAGES:
        assert package.requirement.strip()
        assert package.closure_gate.strip()
        assert package.evidence
        assert package.claimed_tiers


def test_every_evidence_reference_resolves() -> None:
    assert _problems() == []


def test_code_evidence_must_exist() -> None:
    packages = _replace_package(
        "W07",
        evidence=(
            Evidence(EvidenceKind.CODE, "compiler/backends/does_not_exist.py"),
        ),
    )
    problems = _problems(packages)
    assert any("code evidence does not exist" in problem for problem in problems)


def test_test_evidence_must_be_canonical() -> None:
    packages = _replace_package(
        "W21",
            evidence=(Evidence(EvidenceKind.TEST, "autonomous-api/test_production.py"),),
    )
    problems = _problems(packages)
    assert any("outside the canonical suite" in problem for problem in problems)


def test_workflow_evidence_must_be_a_workflow() -> None:
    packages = _replace_package(
        "W18",
        evidence=(Evidence(EvidenceKind.WORKFLOW, "release/run-campaign-a.sh"),),
    )
    problems = _problems(packages)
    assert any("outside .github/workflows" in problem for problem in problems)


def test_unknown_pr_reference_is_rejected() -> None:
    packages = _replace_package(
        "W13",
        evidence=(Evidence(EvidenceKind.PR, "PR#9999"),),
    )
    problems = _problems(packages)
    assert any("unknown PR reference: PR#9999" in problem for problem in problems)


def test_malformed_artifact_reference_is_rejected() -> None:
    packages = _replace_package(
        "W16",
        evidence=(Evidence(EvidenceKind.EVIDENCE, "some/local/file.json"),),
    )
    problems = _problems(packages)
    assert any("workflow artifact" in problem for problem in problems)


def test_dependency_cycle_is_rejected() -> None:
    packages = _replace_package(
        "W02",
        dependencies=("W01", "W03"),
    )
    problems = _problems(packages)
    assert any("dependency cycle" in problem for problem in problems)


def test_unknown_dependency_is_rejected() -> None:
    packages = _replace_package(
        "W22",
        dependencies=("W99",),
    )
    problems = _problems(packages)
    assert any("depends on unknown package: W99" in problem for problem in problems)


def test_self_dependency_is_rejected() -> None:
    packages = _replace_package(
        "W05",
        dependencies=("W04", "W05"),
    )
    problems = _problems(packages)
    assert any("W05: depends on itself" in problem for problem in problems)


def test_verified_requires_test_and_workflow_or_artifact_evidence() -> None:
    verified_no_test = _replace_package(
        "W08",
        status=Status.VERIFIED,
        verified_tiers=(CertificationTier.BUILD,),
        evidence=(
            Evidence(EvidenceKind.CODE, "compiler/backends/production/postgres_backend.py"),
            Evidence(
                EvidenceKind.WORKFLOW,
                ".github/workflows/root-canonical-suite.yml",
            ),
        ),
    )
    assert any("VERIFIED without canonical test evidence" in problem for problem in _problems(verified_no_test))

    verified_no_workflow = _replace_package(
        "W08",
        status=Status.VERIFIED,
        verified_tiers=(CertificationTier.BUILD,),
        evidence=(
            Evidence(EvidenceKind.CODE, "compiler/backends/production/postgres_backend.py"),
            Evidence(
                EvidenceKind.TEST,
                "tests/test_no_passing_stubs.py",
            ),
        ),
    )
    assert any(
        "VERIFIED without workflow or artifact evidence" in problem
        for problem in _problems(verified_no_workflow)
    )


def test_verified_tiers_require_verified_status() -> None:
    packages = _replace_package(
        "W08",
        verified_tiers=(CertificationTier.BUILD,),
    )
    problems = _problems(packages)
    assert any("verified tiers require VERIFIED status" in problem for problem in problems)


def test_verified_tier_must_be_claimed() -> None:
    packages = _replace_package(
        "W04",
        status=Status.VERIFIED,
        claimed_tiers=(CertificationTier.STRUCTURAL,),
        verified_tiers=(CertificationTier.BEHAVIORAL,),
        evidence=(
            Evidence(EvidenceKind.CODE, "vertical_slice/candidate_generation_d23.py"),
            Evidence(
                EvidenceKind.TEST,
                "tests/vs1/test_candidate_generation_d23.py",
            ),
            Evidence(
                EvidenceKind.WORKFLOW,
                ".github/workflows/root-canonical-suite.yml",
            ),
        ),
    )
    problems = _problems(packages)
    assert any("verified tier behavioral is not claimed" in problem for problem in problems)


def test_in_progress_requires_limitations() -> None:
    packages = _replace_package("W09", limitations=())
    problems = _problems(packages)
    assert any("W09: IN_PROGRESS requires explicit limitations" in problem for problem in problems)


def test_implemented_unverified_requires_canonical_test() -> None:
    packages = _replace_package("W16", evidence=(
        Evidence(EvidenceKind.CODE, "certification/campaign/runner.py"),
    ))
    problems = _problems(packages)
    assert any("IMPLEMENTED_UNVERIFIED requires canonical test evidence" in problem for problem in problems)


def test_verified_defect_requires_regression_test() -> None:
    defects = tuple(
        dataclasses.replace(defect, regression_test=None)
        if defect.id == "D01"
        else defect
        for defect in DEFECTS
    )
    problems = _problems(WORK_PACKAGES, defects)
    assert any("D01: VERIFIED defect requires a canonical regression test" in problem for problem in problems)


def test_defect_regression_test_must_be_canonical() -> None:
    defects = tuple(
        dataclasses.replace(defect, regression_test="autonomous-api/test_system.py")
        if defect.id == "D01"
        else defect
        for defect in DEFECTS
    )
    problems = _problems(WORK_PACKAGES, defects)
    assert any("outside the canonical suite" in problem for problem in problems)


def test_defect_location_must_exist() -> None:
    defects = tuple(
        dataclasses.replace(defect, location="nowhere/missing.py")
        if defect.id == "D04"
        else defect
        for defect in DEFECTS
    )
    problems = _problems(WORK_PACKAGES, defects)
    assert any("defect location does not exist" in problem for problem in problems)


def test_defect_severity_is_bounded() -> None:
    defects = tuple(
        dataclasses.replace(defect, severity="catastrophic")
        if defect.id == "D04"
        else defect
        for defect in DEFECTS
    )
    problems = _problems(WORK_PACKAGES, defects)
    assert any("invalid severity" in problem for problem in problems)


def test_duplicate_defect_is_rejected() -> None:
    problems = _problems(WORK_PACKAGES, DEFECTS + (DEFECTS[0],))
    assert any("duplicate defect id: D01" in problem for problem in problems)


def test_known_defect_baseline_is_honest() -> None:
    by_id = {defect.id: defect for defect in DEFECTS}
    assert by_id["D01"].status is DefectStatus.VERIFIED
    assert by_id["D02"].status is DefectStatus.VERIFIED
    assert by_id["D03"].status is DefectStatus.VERIFIED
    assert by_id["D04"].status is DefectStatus.VERIFIED
    for defect_id in ("D05", "D06", "D07", "D08"):
        assert by_id[defect_id].status is DefectStatus.OPEN


def test_certification_claim_is_gated_by_open_simulation_defects() -> None:
    by_id = {package.id: package for package in WORK_PACKAGES}
    defects = {defect.id: defect for defect in DEFECTS}
    open_defects = {
        defect_id
        for defect_id, defect in defects.items()
        if defect.status is DefectStatus.OPEN
    }
    if open_defects & {"D05", "D06", "D07", "D08"}:
        assert by_id["W16"].status is not Status.VERIFIED


def test_no_work_package_is_verified_yet() -> None:
    assert all(package.status is not Status.VERIFIED for package in WORK_PACKAGES)
    assert all(not package.verified_tiers for package in WORK_PACKAGES)


def test_payload_serialises_to_json() -> None:
    payload = register_payload()
    encoded = json.dumps(payload)
    assert json.loads(encoded) == payload
    assert len(payload["work_packages"]) == 22


def test_cli_check_returns_zero_for_valid_register(capsys) -> None:
    assert main(["--check"]) == 0
    assert "REGISTER-OK: 22 work packages, 8 defects" in capsys.readouterr().out


def test_cli_reports_problems_for_broken_register(monkeypatch, capsys) -> None:
    import certification.remediation.register as register_module

    broken = _replace_package(
        "W20",
        evidence=(Evidence(EvidenceKind.CODE, "certification/core/missing_metrics.py"),),
    )
    monkeypatch.setattr(register_module, "WORK_PACKAGES", broken)
    assert main(["--check"]) == 1
    assert "REGISTER-INVALID" in capsys.readouterr().err


def test_cli_json_contains_schema_and_defects(capsys) -> None:
    assert main(["--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_id"] == SCHEMA_ID
    assert {defect["id"] for defect in payload["defects"]} == {
        defect.id for defect in DEFECTS
    }


def test_module_entrypoint_runs_check() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "certification.remediation.register", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "REGISTER-OK" in completed.stdout
