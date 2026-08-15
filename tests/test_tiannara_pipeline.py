import asyncio
import shutil

from tiannara.application.pipeline.execution_pipeline import ExecutionPipeline
from tiannara.infrastructure.backends.minimal_container_backend import MinimalContainerBackend
from tiannara.infrastructure.evolution.baseline_evolution_engine import BaselineEvolutionEngine
from tiannara.infrastructure.intent.structured_intent_compiler import StructuredIntentCompiler


def _pipeline():
    return ExecutionPipeline(
        intent_compiler=StructuredIntentCompiler(),
        evolution_engine=BaselineEvolutionEngine(),
        backends={"minimal-container": MinimalContainerBackend()},
    )


def test_pipeline_compiles_isr_to_bundle():
    result = asyncio.run(_pipeline().execute(
        project_id="p1", statement="a demo service",
        target_backend="minimal-container", hints={"domain": "general"},
    ))
    assert result.bundle is not None
    assert result.bundle.project_id == "p1"
    assert result.evidence.compilation_success is True
    assert result.evidence.isr_hash == result.bundle.isr_hash
    assert result.bundle.path.exists()
    shutil.rmtree(result.bundle.path, ignore_errors=True)


def test_pipeline_unknown_backend_raises():
    p = _pipeline()

    async def go():
        return await p.execute(
            project_id="p", statement="x", target_backend="nope", hints={})

    try:
        asyncio.run(go())
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "nope" in str(exc)
