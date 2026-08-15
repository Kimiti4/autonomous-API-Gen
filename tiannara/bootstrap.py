"""Composition root for the Stratified Calibration Harness (Phase 31).

Wires the constitutional pipeline with local reference adapters when no GitHub
token / Docker is configured, and with production adapters when they are. All
adapters are selected behind their ports — nothing in the Domain/Application
layers knows which implementation is in use.
"""
from pathlib import Path

from .application.harness.calibration_harness import StratifiedCalibrationHarness
from .application.pipeline.execution_pipeline import ExecutionPipeline
from .application.publisher.gate_evaluator import GatePolicy, ExitGateEvaluator
from .application.publisher.publisher_orchestrator import (
    PublisherOrchestrator,
    PublishingIdentity,
)
from .infrastructure.backends.minimal_container_backend import MinimalContainerBackend
from .application.compiler import FastAPIHexagonalBackend
from .infrastructure.config.settings import PlatformSettings
from .infrastructure.evolution.baseline_evolution_engine import BaselineEvolutionEngine
from .infrastructure.intent.structured_intent_compiler import StructuredIntentCompiler
from .infrastructure.ledger.jsonl_evidence_ledger import JsonlEvidenceLedger
from .infrastructure.publishers.local_publisher import LocalRepositoryPublisher
from .infrastructure.sandbox.docker_environment import DockerComposeEnvironment
from .infrastructure.sandbox.local_environment import LocalExecutionEnvironment


def build_harness() -> tuple[StratifiedCalibrationHarness, PlatformSettings]:
    settings = PlatformSettings()

    backends = {
        "minimal-container": MinimalContainerBackend(),
        "fastapi_hexagonal": FastAPIHexagonalBackend(),
    }
    pipeline = ExecutionPipeline(
        intent_compiler=StructuredIntentCompiler(),
        evolution_engine=BaselineEvolutionEngine(),
        backends=backends,
    )
    gates = ExitGateEvaluator(GatePolicy(
        min_test_pass_rate=settings.min_test_pass_rate,
        require_compilation=settings.require_compilation,
        require_security_scan=settings.require_security_scan,
        max_security_vulnerabilities=settings.max_security_vulnerabilities,
    ))
    ledger = JsonlEvidenceLedger(settings.ledger_path)
    fallback = PublishingIdentity(
        owner=settings.fallback_owner,
        author_name="Tiannara Evolution Engine",
        author_email=settings.fallback_email,
    )

    if settings.github_token is not None:
        from .infrastructure.git.github_publisher import GitHubRepositoryPublisher
        publisher = GitHubRepositoryPublisher(token=settings.github_token.get_secret_value())
    else:
        publisher = LocalRepositoryPublisher(Path("tiannara-published"))

    if settings.environment == "auto":
        if DockerComposeEnvironment.available():
            environment = DockerComposeEnvironment(timeout_seconds=settings.verification_timeout_seconds)
        else:
            environment = LocalExecutionEnvironment()
    elif settings.environment == "docker":
        environment = DockerComposeEnvironment(timeout_seconds=settings.verification_timeout_seconds)
    else:
        environment = LocalExecutionEnvironment()

    orchestrator = PublisherOrchestrator(
        publisher=publisher,
        gate_evaluator=gates,
        ledger=ledger,
        fallback_identity=fallback,
        quarantine_dir=Path(settings.quarantine_dir),
    )
    harness = StratifiedCalibrationHarness(
        pipeline=pipeline,
        orchestrator=orchestrator,
        environment=environment,
        max_concurrency=settings.max_concurrency,
    )
    return harness, settings
