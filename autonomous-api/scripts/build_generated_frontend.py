"""Generate and certify a reproducible React frontend fixture.

CI invokes this script in three phases: generate, record evidence after the
real npm build/unit/E2E commands pass, then certify the exact emitted artifact
set against the hashed execution logs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.engine.frontend_certification import (
    FrontendExecutionEvidence,
    certify_frontend_compiler,
    frontend_artifact_hash,
)
from app.engine.frontend_ir import (
    FrontendActionBinding,
    FrontendProjectIR,
    FrontendScreen,
)
from app.engine.react_typescript_compiler import ReactTypeScriptCompiler


def fixture_ir() -> FrontendProjectIR:
    return FrontendProjectIR(
        schema_version="1",
        application_id="world-concern-payroll-ui",
        screens=(
            FrontendScreen(
                screen_id="payroll-dashboard",
                route="/payroll",
                title="Payroll Dashboard",
                data_contract="PayrollRunList",
                authorization_policy="payroll.read",
                actions=("Refresh payroll runs", "View payslips"),
                accessibility_requirements=("keyboard-navigation", "screen-reader"),
                action_bindings=(
                    FrontendActionBinding(
                        action_id="Refresh payroll runs",
                        api_operation_id="payroll.list_runs",
                        method="GET",
                        path="/api/payroll-runs",
                        request_fields=(),
                        authorization_policy="payroll.read",
                    ),
                ),
            ),
        ),
        api_contract_version="api-v1",
        platform_requirements=("responsive-layout", "semantic-html"),
        configuration_keys=("API_BASE_URL",),
    )


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_compiled_files(output: Path, compilation) -> None:
    for artifact in compilation.artifacts:
        relative = Path(artifact.path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe generated path: {artifact.path}")
        path = output / relative
        if not path.is_file():
            raise ValueError(f"generated artifact is missing: {artifact.path}")
        if path.read_text(encoding="utf-8") != artifact.content:
            raise ValueError(f"generated artifact changed after compilation: {artifact.path}")


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    ir = fixture_ir()
    compilation = ReactTypeScriptCompiler().compile(ir)
    if compilation.diagnostics:
        raise RuntimeError("frontend compilation failed: " + "; ".join(compilation.diagnostics))
    for artifact in compilation.artifacts:
        target = output / artifact.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(artifact.content, encoding="utf-8")
    manifest = {
        "schema_version": ir.schema_version,
        "application_id": ir.application_id,
        "artifact_sha256": frontend_artifact_hash(compilation),
        "files": [
            {"path": artifact.path, "sha256": hashlib.sha256(artifact.content.encode("utf-8")).hexdigest()}
            for artifact in sorted(compilation.artifacts, key=lambda item: item.path)
        ],
    }
    (output / "source-artifact-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def record_evidence(output: Path, build_log: Path, unit_log: Path, e2e_log: Path) -> None:
    compilation = ReactTypeScriptCompiler().compile(fixture_ir())
    _verify_compiled_files(output, compilation)
    logs = (build_log, unit_log, e2e_log)
    for log in logs:
        if not log.is_file() or not log.read_bytes():
            raise ValueError(f"execution log is missing or empty: {log}")
    evidence = FrontendExecutionEvidence(
        artifact_sha256=frontend_artifact_hash(compilation),
        build_passed=True,
        unit_tests_passed=True,
        e2e_passed=True,
        build_log_sha256=_hash_file(build_log),
        unit_test_log_sha256=_hash_file(unit_log),
        e2e_log_sha256=_hash_file(e2e_log),
        workflow_run_id=os.environ.get("GITHUB_RUN_ID", "local-run"),
        source_commit=os.environ.get("GITHUB_SHA", "local-source"),
    )
    (output / "frontend-execution-evidence.json").write_text(
        json.dumps(evidence.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def certify(output: Path) -> None:
    compilation = ReactTypeScriptCompiler().compile(fixture_ir())
    _verify_compiled_files(output, compilation)
    evidence_path = output / "frontend-execution-evidence.json"
    if not evidence_path.is_file():
        raise ValueError("frontend execution evidence is missing")
    evidence = FrontendExecutionEvidence.from_dict(
        json.loads(evidence_path.read_text(encoding="utf-8"))
    )
    result = certify_frontend_compiler(fixture_ir(), compilation, evidence)
    (output / "frontend-certification.json").write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not result.certified:
        raise RuntimeError("frontend certification failed: " + "; ".join(result.findings))
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--record-evidence", action="store_true")
    parser.add_argument("--certify", action="store_true")
    parser.add_argument("--build-log")
    parser.add_argument("--unit-log")
    parser.add_argument("--e2e-log")
    args = parser.parse_args(argv)
    output = Path(args.output_dir).resolve()
    if args.record_evidence:
        if not args.build_log or not args.unit_log or not args.e2e_log:
            parser.error("--record-evidence requires all three log paths")
        record_evidence(output, Path(args.build_log), Path(args.unit_log), Path(args.e2e_log))
    elif args.certify:
        certify(output)
    else:
        generate(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
