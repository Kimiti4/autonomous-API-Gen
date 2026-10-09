"""Shared generation helpers for TASKFLOW-ESAP-NATIVE-001.

Pure functions used both by the parent trial runner and by the isolated
generation child process (``isolated_generation.py``). Importing this module
must stay free of import-time side effects -- no ``sys.path`` mutation, no
network, no file access -- because the child imports it as part of its
trusted bootstrap before the audit-hook boundary engages, and the parent
imports it from test harnesses.
"""

from __future__ import annotations

import shutil
from pathlib import Path

EVIDENCE_SCHEMA = "taskflow.trial.evidence.v1"
INTERPRETER_MODEL_ID = "esap-interpreter@1"


def _interpreter_config():
    from tiannara.application.intent import IntentCompilerConfig

    return IntentCompilerConfig(model_id=INTERPRETER_MODEL_ID)


def _statement_hash(statement: str) -> str:
    from tiannara.application.intent.prompts import normalize

    return normalize(statement).source_statement_hash


def _interpreter_provider():
    from tiannara.infrastructure.llm.interpreting_provider import (
        InterpretingModelProvider,
    )

    return InterpretingModelProvider()


def compile_for_graph_evidence(statement: str) -> tuple[dict, dict]:
    from tiannara.application.intent import derive_system_id
    from tiannara.application.intent.compiler import IntentCompiler

    provider = _interpreter_provider()
    result = IntentCompiler(provider, config=_interpreter_config()).compile_full(
        statement, derive_system_id(statement)
    )
    model = (
        result.isr.system_model()
        if callable(getattr(result.isr, "system_model", None))
        else getattr(result.isr, "system_model", None)
    )
    graph_evidence = {
        "evidence_schema": EVIDENCE_SCHEMA,
        "isr_hash": result.isr.content_hash(),
        "system_name": getattr(model, "system_name", "")
        or getattr(result.isr, "system_name", ""),
        "graph_hash": result.requirement_graph.content_hash(),
        "repair_iterations": result.repair_iterations,
        "model_calls": len(result.call_records),
        "node_count": len(result.requirement_graph.nodes),
        "edge_count": len(result.requirement_graph.edges),
    }
    interpretation = {
        "evidence_schema": EVIDENCE_SCHEMA,
        "provider_model": INTERPRETER_MODEL_ID,
        "statement_hash": _statement_hash(statement),
        "repair_iterations": result.repair_iterations,
        "calls": [
            {
                "task": record.task,
                "model_id": record.model_id,
                "output_schema_id": record.output_schema_id,
                "signature_hash": record.signature_hash,
                "prompt_hash": record.prompt_hash,
                "response_hash": record.response_hash,
                "output": record.output_payload,
            }
            for record in result.call_records
        ],
    }
    return graph_evidence, interpretation


def default_verifier_factory(compilation_result):
    from tiannara.application.compiler.verification import BundleVerifier

    package = getattr(compilation_result, "system_name", "bundle")
    required = sorted(getattr(compilation_result, "files", {}).keys())
    return BundleVerifier(package=package, required_files=required)


def summarize_report(report) -> dict:
    bundles = []
    for outcome in getattr(report, "verification_outcomes", ()) or ():
        test_result = getattr(outcome, "test_result", None)
        test = None
        if test_result is not None:
            test = {
                "evaluated": bool(getattr(test_result, "evaluated", True)),
                "passed": bool(getattr(test_result, "passed", False)),
                "exit_code": int(getattr(test_result, "exit_code", -1)),
                "duration_seconds": float(
                    getattr(test_result, "duration_seconds", 0.0) or 0.0
                ),
                "logs_path": getattr(test_result, "logs_path", None),
            }
        bundles.append(
            {
                "backend_id": getattr(outcome, "bundle_backend_id", ""),
                "static_ok": bool(getattr(outcome, "static_ok", False)),
                "ok": bool(getattr(outcome, "ok", False)),
                "repair_attempts": int(getattr(outcome, "repair_attempts", 0)),
                "test": test,
            }
        )
    return {
        "evidence_schema": EVIDENCE_SCHEMA,
        "ok": bool(getattr(report, "ok", False)),
        "isr_hash": getattr(report, "isr_hash", ""),
        "statement_hash": getattr(report, "statement_hash", ""),
        "plan_id": getattr(report, "plan_id", ""),
        "bundles": bundles,
        "repair_attempts_total": sum(b["repair_attempts"] for b in bundles),
    }


def run_factory(
    statement: str,
    repo_root: Path,
    evidence_dir: Path,
    max_repair_attempts: int,
) -> tuple[dict, object]:
    from tiannara.application.compiler.composition import (
        build_compiler_registry,
        build_project_compiler,
    )
    from tiannara.application.factory import (
        RematerializationRepairProvider,
        SoftwareFactory,
        SoftwareFactoryError,
    )
    from tiannara.application.factory.evidence_sink import make_factory_evidence_sink
    from tiannara.application.materializer.materializer import RepositoryMaterializer
    from tiannara.infrastructure.ledger.jsonl_evidence_ledger import JsonlEvidenceLedger
    from tiannara.infrastructure.sandbox.profile_environment import (
        BuildProfileExecutionEnvironment,
    )
    from tiannara.infrastructure.source_control.local_git import LocalGitBackend

    registry = build_compiler_registry()
    compiler = build_project_compiler(
        provider=_interpreter_provider(),
        config=_interpreter_config(),
        registry=registry,
    )
    sc_backend = LocalGitBackend() if shutil.which("git") else None
    materializer = RepositoryMaterializer(sc_backend)
    ledger = JsonlEvidenceLedger(str(evidence_dir / "factory-ledger.jsonl"))
    factory = SoftwareFactory(
        project_compiler=compiler,
        materializer=materializer,
        execution_environment=BuildProfileExecutionEnvironment(registry),
        repair_provider=RematerializationRepairProvider(),
        verifier_factory=default_verifier_factory,
        max_repair_attempts=max_repair_attempts,
        evidence_sink=make_factory_evidence_sink(ledger),
        require_static=True,
        require_runtime=True,
    )
    try:
        report = factory.run(statement, out_root=str(repo_root), force=True)
    except SoftwareFactoryError as exc:
        failed_report = getattr(exc, "report", None)
        if failed_report is None:
            return (
                {
                    "evidence_schema": EVIDENCE_SCHEMA,
                    "ok": False,
                    "isr_hash": "",
                    "statement_hash": "",
                    "plan_id": "",
                    "bundles": [],
                    "repair_attempts_total": 0,
                    "error": repr(exc),
                },
                None,
            )
        summary = summarize_report(failed_report)
        summary["error"] = repr(exc)
        return summary, failed_report
    return summarize_report(report), report
