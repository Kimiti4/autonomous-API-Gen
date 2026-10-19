from app.engine.frontend_certification import (\n    FrontendExecutionEvidence,\n    certify_frontend_compiler,\n    frontend_artifact_hash,\n)
from app.engine.frontend_ir import FrontendProjectIR, FrontendScreen
from app.engine.react_typescript_compiler import ReactTypeScriptCompiler


def test_react_target_preserves_frontend_semantics():
    ir = FrontendProjectIR(
        "1", "ev-app",
        (FrontendScreen(
            "wallet", "/wallet", "Wallet", "WalletView", "wallet-read",
            ("send", "refresh"), ("screen-reader", "keyboard-navigation")
        ),),
        "api-v1", ("responsive",), ("API_BASE_URL",),
    )
    result = ReactTypeScriptCompiler().compile(ir)
    certification = certify_frontend_compiler(ir, result)
    assert not certification.certified
    assert any("missing real build" in finding for finding in certification.findings)\n\n    evidence = FrontendExecutionEvidence(\n        artifact_sha256=frontend_artifact_hash(result),\n        build_passed=True,\n        unit_tests_passed=True,\n        e2e_passed=True,\n        build_log_sha256="a" * 64,\n        unit_test_log_sha256="b" * 64,\n        e2e_log_sha256="c" * 64,\n        workflow_run_id="test-run",\n        source_commit="test-commit",\n    )\n    certified = certify_frontend_compiler(ir, result, evidence)\n    assert certified.certified, certified.findings
