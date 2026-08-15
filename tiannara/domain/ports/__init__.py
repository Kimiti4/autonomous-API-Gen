from typing import Protocol, runtime_checkable
from ..models.bundle import SystemDeploymentBundle
from ..models.evidence import CertificationEvidence
from ..models.genome import Genome
from ..models.isr import IntermediateSoftwareRepresentation
from .language_model import LanguageModelProvider


class EvolvedCandidate:
    def __init__(self, genome: Genome, rationale: str) -> None:
        self.genome = genome
        self.rationale = rationale


@runtime_checkable
class IntentCompiler(Protocol):
    def compile(self, statement: str, hints: dict) -> IntermediateSoftwareRepresentation: ...


@runtime_checkable
class EvolutionEngine(Protocol):
    """Operates exclusively on the ISR. Never on source code."""

    def evolve(self, isr: IntermediateSoftwareRepresentation) -> EvolvedCandidate: ...


@runtime_checkable
class CompilerBackend(Protocol):
    @property
    def name(self) -> str: ...

    def compile(
        self,
        isr: IntermediateSoftwareRepresentation,
        genome: Genome,
        output_dir: str,
    ) -> SystemDeploymentBundle: ...


@runtime_checkable
class ExecutionEnvironment(Protocol):
    async def run_verification(self, bundle: SystemDeploymentBundle) -> "TestRunResult": ...

    async def teardown(self, bundle: SystemDeploymentBundle) -> None: ...


@runtime_checkable
class EvidenceLedger(Protocol):
    def append(self, evidence: CertificationEvidence) -> CertificationEvidence: ...

    def verify_chain(self) -> bool: ...


@runtime_checkable
class RepositoryPublisher(Protocol):
    async def publish(
        self,
        bundle: SystemDeploymentBundle,
        evidence: CertificationEvidence,
        owner: str,
        author_name: str,
        author_email: str,
    ) -> str:
        """Returns the published repository URL."""
        ...


from ..models.evidence import TestRunResult  # noqa: E402
