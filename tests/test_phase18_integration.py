"""Phase 18 -- end-to-end SoftwareFactory run through the real compiler.

Reuses the hermetic recorded-provider seeding pattern from Phase 16: the same
deterministic prompt builders (``build_elicitation_request`` /
``build_extraction_request``) and ``IntentCompilerConfig`` defaults that the
real ``IntentCompiler`` uses produce byte-stable call signatures, so the REAL
``ProjectCompiler`` replays against a transcript fixture with no network and no
fabrication.

This exercises the full Phase 18 pipeline:
    Compile (P16 real) -> Materialize (P17, InMemorySourceControl) ->
    Static verify (BundleVerifier) -> Runtime verify (LocalExecutionEnvironment)
    -> bounded repair loop -> FitnessVector.
Nothing is stubbed except the LLM replay fixture.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tiannara.application.compiler.composition import build_project_compiler
from tiannara.application.compiler.verification import (
    BundleVerificationReport,
    BundleVerifier,
)
from tiannara.application.factory import (
    NullRepairProvider,
    RematerializationRepairProvider,
    SoftwareFactory,
    SoftwareFactoryError,
)
from tiannara.application.intent.config import IntentCompilerConfig
from tiannara.application.intent.prompts import (
    build_elicitation_request,
    build_extraction_request,
    normalize,
)
from tiannara.application.intent.schemas import (
    ElicitationOutput,
    ExtractionOutput,
)
from tiannara.application.materializer.materializer import (
    MaterializationResult,
    RepositoryMaterializer,
)
from tiannara.domain.models.model_call import (
    ModelCallRecord,
    compute_call_signature,
    hash_payload,
)
from tiannara.infrastructure.llm.transcript import ModelCallTranscript
from tiannara.infrastructure.sandbox.local_environment import (
    LocalExecutionEnvironment,
)
from tiannara.infrastructure.source_control.in_memory import (
    InMemorySourceControlBackend,
)

STATEMENT = "Order Management"

_ELICITATION: dict = {
    "inferred_capabilities": ["Order Processing"],
    "assumptions": [{"statement": "Clients place orders online"}],
    "clarifications": ["Payment provider"],
}

_EXTRACTION: dict = {
    "nodes": [
        {
            "ref": "req-order",
            "kind": "functional",
            "statement": "Process customer orders",
            "priority": "must",
        }
    ],
    "edges": [],
}


def _record(request, payload: dict) -> ModelCallRecord:
    """Build a ModelCallRecord exactly as the real compiler will request it."""
    return ModelCallRecord(
        signature_hash=compute_call_signature(request),
        model_id=request.model_id,
        task=request.task,
        output_schema_id=request.output_schema_id,
        output_payload=payload,
        response_hash=hash_payload(payload),
        decoding=request.decoding,
    )


def _seed_transcript(tmp_path: Path) -> Path:
    """Commit a minimal, schema-valid elicitation+extraction transcript."""
    config = IntentCompilerConfig()
    normalized = normalize(STATEMENT)
    elicitation = ElicitationOutput(**_ELICITATION)
    transcript_path = tmp_path / "transcript.jsonl"
    transcript = ModelCallTranscript(transcript_path)
    transcript.append(
        _record(build_elicitation_request(normalized, config), _ELICITATION)
    )
    transcript.append(
        _record(
            build_extraction_request(normalized, elicitation, config),
            _EXTRACTION,
        )
    )
    return transcript_path


def _default_verifier_factory(compilation_result) -> BundleVerifier:
    package = getattr(compilation_result, "system_name", "bundle")
    required = sorted(getattr(compilation_result, "files", {}).keys())
    return BundleVerifier(package=package, required_files=required)


class _SabotagingVerifier:
    """Verifier that deletes ``rel`` from the bundle on the first pass.

    The file remains present in ``source_artifacts`` (the compiled result), so
    the RematerializationRepairProvider can rewrite it from source -- exercising
    the real repair loop. Subsequent (post-repair) calls defer to the real
    BundleVerifier.
    """

    def __init__(self, inner: BundleVerifier, rel: str) -> None:
        self._inner = inner
        self._rel = rel
        self._first = True

    def verify(self, root):
        if self._first:
            self._first = False
            (Path(root) / self._rel).unlink(missing_ok=True)
            return BundleVerificationReport(ok=False, missing_files=[self._rel])
        return self._inner.verify(root)


def test_factory_end_to_end_with_real_compiler_and_materializer(tmp_path):
    transcript_path = _seed_transcript(tmp_path)
    compiler = build_project_compiler("recorded", transcript_path=transcript_path)
    sc = InMemorySourceControlBackend()
    materializer = RepositoryMaterializer(sc)

    factory = SoftwareFactory(
        project_compiler=compiler,
        materializer=materializer,
        execution_environment=LocalExecutionEnvironment(),
        repair_provider=RematerializationRepairProvider(),
        verifier_factory=_default_verifier_factory,
        max_repair_attempts=2,
    )

    out_root = tmp_path / "out"
    report = factory.run(STATEMENT, out_root=str(out_root))

    # -- orchestration verdict ------------------------------------------------
    assert report.ok is True
    assert report.isr_hash and report.plan_id and report.policy_name
    assert len(report.verification_outcomes) == 1
    outcome = report.verification_outcomes[0]
    assert outcome.repair_attempts == 0
    assert outcome.repaired is False
    assert outcome.static_report is not None
    assert outcome.static_report.ok is True

    # -- real materialization artifacts ---------------------------------------
    materialization = report.materialization
    assert isinstance(materialization, MaterializationResult)
    assert materialization.out_root == out_root
    assert materialization.manifest_path == out_root / "provenance/manifest.json"
    assert materialization.manifest_path.exists()

    bundle = materialization.bundles[0]
    slug = bundle.project_id
    assert (out_root / slug / "main.py").exists()
    assert (out_root / "Dockerfile").exists()
    assert f"{slug}/main.py" in bundle.artifacts
    assert "Dockerfile" in bundle.artifacts
    assert bundle.isr_hash == report.isr_hash

    # -- in-memory source-control commit recorded (no real git required) ------
    assert materialization.commit is not None
    assert materialization.commit.commit_id.startswith("sha-")
    assert materialization.commit.branch == "main"
    assert any(call[0] == "commit" for call in sc.calls)

    # -- fitness vector reflects a clean, repair-free pass --------------------
    metrics = report.fitness.metrics
    assert set(metrics) == {
        "build", "scan", "test", "verification", "repair_free",
    }
    assert metrics["verification"] == 1.0
    assert metrics["repair_free"] == 1.0


def test_factory_repair_loop_restores_missing_file(tmp_path):
    transcript_path = _seed_transcript(tmp_path)
    compiler = build_project_compiler("recorded", transcript_path=transcript_path)
    materializer = RepositoryMaterializer(InMemorySourceControlBackend())

    def verifier_factory(result):
        inner = _default_verifier_factory(result)
        return _SabotagingVerifier(inner, rel="Dockerfile")

    factory = SoftwareFactory(
        project_compiler=compiler,
        materializer=materializer,
        execution_environment=LocalExecutionEnvironment(),
        repair_provider=RematerializationRepairProvider(),
        verifier_factory=verifier_factory,
        max_repair_attempts=2,
    )

    out_root = tmp_path / "out"
    report = factory.run(STATEMENT, out_root=str(out_root))

    assert report.ok is True
    outcome = report.verification_outcomes[0]
    assert outcome.repaired is True
    assert outcome.repair_attempts == 1
    assert outcome.ok is True
    assert (out_root / "Dockerfile").exists()


def test_factory_deny_without_repair_on_missing_file(tmp_path):
    transcript_path = _seed_transcript(tmp_path)
    compiler = build_project_compiler("recorded", transcript_path=transcript_path)
    materializer = RepositoryMaterializer(InMemorySourceControlBackend())

    def verifier_factory(result):
        inner = _default_verifier_factory(result)
        return _SabotagingVerifier(inner, rel="Dockerfile")

    factory = SoftwareFactory(
        project_compiler=compiler,
        materializer=materializer,
        execution_environment=LocalExecutionEnvironment(),
        repair_provider=NullRepairProvider(),
        verifier_factory=verifier_factory,
        max_repair_attempts=2,
    )

    with pytest.raises(SoftwareFactoryError) as exc:
        factory.run(STATEMENT, out_root=str(tmp_path / "brk"))

    assert exc.value.report is not None
    assert exc.value.report.ok is False
    outcome = exc.value.report.verification_outcomes[0]
    assert outcome.repair_attempts == 1
    assert outcome.repaired is False
    assert outcome.ok is False


def test_cli_factory_subcommand_end_to_end(tmp_path, monkeypatch):
    """The ``tiannara factory`` CLI subcommand runs the real compiler loop."""
    # Force the hermetic path: no git on PATH -> in-memory-free materialize.
    import shutil as _shutil

    monkeypatch.setattr(_shutil, "which", lambda _name, *_a, **_k: None)

    from tiannara.interfaces.cli.main import main

    transcript_path = _seed_transcript(tmp_path)
    out_root = tmp_path / "cli-out"
    rc = main(
        [
            "factory",
            STATEMENT,
            "--transcript",
            str(transcript_path),
            "--out",
            str(out_root),
            "--max-repair-attempts",
            "2",
        ]
    )

    assert rc == 0
    assert (out_root / "Dockerfile").exists()
    assert (out_root / "provenance" / "manifest.json").exists()
    # The generated system directory (scaffolded alongside .github/ CI files)
    # is the one that owns the service entry-point `main.py`.
    system_dirs = [
        p for p in out_root.iterdir()
        if p.is_dir() and p.name != "provenance" and (p / "main.py").exists()
    ]
    assert len(system_dirs) == 1
    assert (system_dirs[0] / "main.py").exists()
