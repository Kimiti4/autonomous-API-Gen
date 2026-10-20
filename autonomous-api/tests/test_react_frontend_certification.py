from app.engine.frontend_certification import (
    FrontendExecutionEvidence,
    certify_frontend_compiler,
    frontend_artifact_hash,
)
from app.engine.frontend_ir import FrontendProjectIR, FrontendScreen
from app.engine.react_typescript_compiler import ReactTypeScriptCompiler


def _ir():
    return FrontendProjectIR(
        "1", "ev-app",
        (FrontendScreen(
            "wallet", "/wallet", "Wallet", "WalletView", "wallet-read",
            ("send", "refresh"), ("screen-reader", "keyboard-navigation")
        ),),
        "api-v1", ("responsive",), ("API_BASE_URL",),
    )


def test_react_target_does_not_certify_source_without_execution_evidence():
    ir = _ir()
    result = ReactTypeScriptCompiler().compile(ir)
    certification = certify_frontend_compiler(ir, result)
    assert not certification.certified
    assert any("missing real build" in finding for finding in certification.findings)


def test_react_target_certifies_only_with_matching_build_unit_and_e2e_evidence():
    ir = _ir()
    result = ReactTypeScriptCompiler().compile(ir)
    evidence = FrontendExecutionEvidence(
        artifact_sha256=frontend_artifact_hash(result),
        build_passed=True,
        unit_tests_passed=True,
        e2e_passed=True,
        build_log_sha256="a" * 64,
        unit_test_log_sha256="b" * 64,
        e2e_log_sha256="c" * 64,
        workflow_run_id="test-run",
        source_commit="test-commit",
    )
    certification = certify_frontend_compiler(ir, result, evidence)
    assert certification.certified, certification.findings


def test_execution_evidence_for_different_artifacts_is_rejected():
    ir = _ir()
    result = ReactTypeScriptCompiler().compile(ir)
    evidence = FrontendExecutionEvidence(
        artifact_sha256="0" * 64,
        build_passed=True,
        unit_tests_passed=True,
        e2e_passed=True,
        build_log_sha256="a" * 64,
        unit_test_log_sha256="b" * 64,
        e2e_log_sha256="c" * 64,
        workflow_run_id="test-run",
        source_commit="test-commit",
    )
    certification = certify_frontend_compiler(ir, result, evidence)
    assert not certification.certified
    assert any("not bound to this exact" in finding for finding in certification.findings)
