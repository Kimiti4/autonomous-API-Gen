import asyncio
from ...domain.ports import ExecutionEnvironment
from .manifest import StratifiedManifest, ProjectEntry
from ..pipeline.execution_pipeline import ExecutionPipeline
from ..publisher.publisher_orchestrator import PublisherOrchestrator


class StratifiedCalibrationHarness:
    """Stratified calibration loop: Intent -> ISR -> Evolution -> Compile ->
    Verify -> Exit Gates -> Evidence Ledger -> Publish.

    The harness never learns what GitHub (or any publisher) is; it only knows
    its `PipelineContract` and the EvidenceLedger it feeds.
    """

    def __init__(
        self,
        pipeline: ExecutionPipeline,
        orchestrator: PublisherOrchestrator,
        environment: ExecutionEnvironment | None = None,
        max_concurrency: int = 10,
    ) -> None:
        self.pipeline = pipeline
        self.orchestrator = orchestrator
        self.environment = environment
        self.max_concurrency = max_concurrency

    async def run(self, manifest: StratifiedManifest, auth=None) -> list:
        projects = manifest.projects
        sem = asyncio.Semaphore(self.max_concurrency)

        async def bounded(spec: ProjectEntry):
            async with sem:
                return await self._execute_project(spec, auth)

        return await asyncio.gather(*[bounded(p) for p in projects])

    async def _execute_project(self, spec: ProjectEntry, auth=None):
        result = await self.pipeline.execute(
            project_id=spec.id,
            statement=spec.intent,
            target_backend=spec.target_backend,
            hints={"domain": spec.domain, "complexity_tier": spec.complexity_tier},
        )
        evidence, bundle = result.evidence, result.bundle

        if bundle is not None and self.environment is not None:
            run = await self.environment.run_verification(bundle)
            # An unevaluated run (no test command configured) means the runtime
            # stage did not happen: record NO test run so the exit gate reports
            # NOT_EVALUATED instead of trusting a fabricated pass or failing a
            # stage that was never authorized to run.
            if getattr(run, "evaluated", True):
                evidence.test_run = run

        await self.orchestrator.process(bundle=bundle, evidence=evidence, auth=auth)

        if bundle is not None and self.environment is not None:
            await self.environment.teardown(bundle)

        return evidence
