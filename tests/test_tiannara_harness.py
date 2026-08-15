import asyncio

from tiannara.application.harness.calibration_harness import StratifiedCalibrationHarness
from tiannara.application.harness.manifest import ProjectEntry, StratifiedManifest
from tiannara.application.pipeline.execution_pipeline import ExecutionPipeline
from tiannara.application.publisher.gate_evaluator import GatePolicy, ExitGateEvaluator
from tiannara.application.publisher.publisher_orchestrator import (
    PublisherOrchestrator,
    PublishingIdentity,
)
from tiannara.domain.ports import CompilerBackend
from tiannara.domain.models.evidence import Verdict
from tiannara.infrastructure.backends.minimal_container_backend import MinimalContainerBackend
from tiannara.infrastructure.evolution.baseline_evolution_engine import BaselineEvolutionEngine
from tiannara.infrastructure.intent.structured_intent_compiler import StructuredIntentCompiler
from tiannara.infrastructure.ledger.jsonl_evidence_ledger import JsonlEvidenceLedger
from tiannara.infrastructure.publishers.local_publisher import LocalRepositoryPublisher
from tiannara.infrastructure.sandbox.local_environment import LocalExecutionEnvironment


def _assemble(tmp_path, pipeline=None, gates_policy=None):
    from pathlib import Path
    tmp_path = Path(tmp_path)
    pipeline = pipeline or ExecutionPipeline(
        intent_compiler=StructuredIntentCompiler(),
        evolution_engine=BaselineEvolutionEngine(),
        backends={"minimal-container": MinimalContainerBackend()},
    )
    policy = gates_policy or GatePolicy(
        min_test_pass_rate=0.995, require_compilation=True,
        require_security_scan=False, max_security_vulnerabilities=0,
    )
    ledger = JsonlEvidenceLedger(tmp_path / "evidence.jsonl")
    orch = PublisherOrchestrator(
        publisher=LocalRepositoryPublisher(tmp_path / "published"),
        gate_evaluator=ExitGateEvaluator(policy),
        ledger=ledger,
        fallback_identity=PublishingIdentity(owner="t", author_name="T", author_email="t@t"),
        quarantine_dir=tmp_path / "quarantine",
    )
    env = LocalExecutionEnvironment()
    return StratifiedCalibrationHarness(
        pipeline=pipeline, orchestrator=orch, environment=env, max_concurrency=2), ledger


def test_harness_runs_and_publishes_passing_projects(tmp_path):
    harness, ledger = _assemble(tmp_path)
    manifest = StratifiedManifest(projects=[
        ProjectEntry(id="p1", intent="a demo service", domain="general",
                     target_backend="minimal-container"),
        ProjectEntry(id="p2", intent="an audit service", domain="compliance",
                     target_backend="minimal-container", complexity_tier="simple"),
    ])
    results = asyncio.run(harness.run(manifest, auth=None))
    assert len(results) == 2
    assert all(e.verdict is Verdict.PASS for e in results)
    assert (tmp_path / "published" / "p1").exists()
    assert (tmp_path / "published" / "p2").exists()
    assert ledger.verify_chain() is True
    assert len(ledger.all()) == 2


def test_harness_quarantines_when_compilation_fails(tmp_path):
    class BrokenBackend(CompilerBackend):
        @property
        def name(self) -> str:
            return "broken"

        def compile(self, isr, genome, output_dir):
            raise RuntimeError("boom")

    pipeline = ExecutionPipeline(
        intent_compiler=StructuredIntentCompiler(),
        evolution_engine=BaselineEvolutionEngine(),
        backends={"broken": BrokenBackend()},
    )
    harness, ledger = _assemble(tmp_path, pipeline=pipeline)
    manifest = StratifiedManifest(projects=[
        ProjectEntry(id="p1", intent="x", domain="d", target_backend="broken"),
    ])
    results = asyncio.run(harness.run(manifest, auth=None))
    assert len(results) == 1
    assert results[0].verdict is Verdict.QUARANTINED
    assert results[0].error is not None
    assert ledger.verify_chain() is True


def test_manifest_load_json(tmp_path):
    import json
    (tmp_path / "m.json").write_text(json.dumps({"projects": [
        {"id": "j1", "intent": "hi", "domain": "general", "target_backend": "minimal-container"}]}),
        encoding="utf-8")
    manifest = StratifiedManifest.load(tmp_path / "m.json")
    assert manifest.size == 1
    assert manifest.projects[0].id == "j1"
