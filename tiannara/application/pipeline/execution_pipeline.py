import tempfile
import traceback
from dataclasses import dataclass
from ...domain.ports import CompilerBackend, EvolutionEngine, IntentCompiler
from ...domain.models.bundle import SystemDeploymentBundle
from ...domain.models.evidence import CertificationEvidence, Verdict
from ...domain.models.fitness import FitnessVector


@dataclass
class PipelineResult:
    evidence: CertificationEvidence
    bundle: SystemDeploymentBundle | None


class ExecutionPipeline:
    """Intent -> ISR -> Evolution -> Compilation.

    Verification and publication are separate constitutional concerns
    handled by the harness and publisher respectively.
    """

    def __init__(
        self,
        intent_compiler: IntentCompiler,
        evolution_engine: EvolutionEngine,
        backends: dict[str, CompilerBackend],
    ) -> None:
        self._intent_compiler = intent_compiler
        self._evolution_engine = evolution_engine
        self._backends = backends

    async def execute(
        self,
        project_id: str,
        statement: str,
        target_backend: str,
        hints: dict,
    ) -> PipelineResult:
        backend = self._backends.get(target_backend)
        if backend is None:
            raise ValueError(f"Unknown compiler backend: {target_backend}")

        try:
            isr = self._intent_compiler.compile(statement, hints)
            isr.system_id = project_id
            isr.lineage.append(f"intent:{project_id}")

            candidate = self._evolution_engine.evolve(isr)
            isr.lineage.append(f"genome:{candidate.genome.genome_id}")
            isr_hash = isr.content_hash()

            output_dir = tempfile.mkdtemp(prefix=f"tiannara-{project_id}-")
            bundle = backend.compile(isr, candidate.genome, output_dir)

            evidence = CertificationEvidence(
                project_id=project_id,
                isr_hash=isr_hash,
                genome_id=candidate.genome.genome_id,
                backend_name=backend.name,
                compilation_success=True,
                fitness=FitnessVector(metrics={"compilation": 1.0}),
            )
            return PipelineResult(evidence=evidence, bundle=bundle)

        except Exception as exc:
            evidence = CertificationEvidence(
                project_id=project_id,
                isr_hash="unavailable",
                genome_id="unavailable",
                backend_name=target_backend,
                compilation_success=False,
                verdict=Verdict.FAIL,
                error=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
            )
            return PipelineResult(evidence=evidence, bundle=None)
