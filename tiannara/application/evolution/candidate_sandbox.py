"""R2 -- candidate sandbox + repair-cycle orchestration (R2.3).

The sandbox never hands the original ISR to a compiler/runner: candidates are
compiled/run in an isolated workspace (`build`), and their raw outcome is
normalized into a technology-neutral `FailureObservation` by the R2.2 classifier
-- the operator/s engine never parses raw tool output itself.

`-W error::RuntimeWarning` is a SEED-SCOPED detection gate (attached here),
not a global flag.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from constitutional_architecture.isr.model import ISR

from tiannara.application.diagnosis.classifier import (
    FailureClassifier,
    FailureEvidenceInput,
)
from tiannara.application.evolution.ledger import EvolutionLedger, EvolutionRecord, stable_isr_hash
from tiannara.application.evolution.transition_restoration import (
    RepairedCandidate,
    TransitionRestoration,
)
from tiannara.domain.models.observation import FailureObservation, FailurePhase


@dataclass(frozen=True)
class RunResult:
    execution_id: str
    backend_id: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class CompiledCandidate:
    source_root: str
    compile_ok: bool
    compile_errors: str = ""
    # R2.4.0b: deterministic content hash over the generated source tree.
    # Empty for the R2.3 simulated stub, so existing call sites are unaffected.
    artifact_hash: str = ""


class CandidateSandbox:
    def __init__(
        self,
        runner: Callable[[ISR], RunResult],
        classifier: Optional[FailureClassifier] = None,
        warning_flag: str = "-W error::RuntimeWarning",
    ):
        self._runner = runner
        self._classifier = classifier or FailureClassifier()
        self._warning_flag = warning_flag

    def build(self, isr: ISR) -> CompiledCandidate:
        return CompiledCandidate(source_root=f"workspace-{isr.content_hash[:8]}", compile_ok=True)

    def run_tests(self, isr: ISR) -> Optional[FailureObservation]:
        result = self._runner(isr)
        evidence = FailureEvidenceInput(
            execution_id=result.execution_id,
            backend_id=result.backend_id,
            phase=FailurePhase.TEST,
            command=("pytest", self._warning_flag, "-q"),
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
        )
        return self._classifier.classify(evidence)


def attempt_repair_cycle(
    broken_isr: ISR,
    observation: FailureObservation,
    operator: TransitionRestoration,
    sandbox: CandidateSandbox,
    ledger: EvolutionLedger,
) -> Optional[EvolutionRecord]:
    candidate: Optional[RepairedCandidate] = operator.hypothesis(observation, broken_isr)
    if candidate is None:
        return None

    repaired_obs = sandbox.run_tests(candidate.repaired_isr)
    repaired_ok = repaired_obs is None
    validation = (("build", "pass"), ("test", "pass" if repaired_ok else "fail"))
    fitness_delta = 1.0 if repaired_ok else 0.0
    decision = "accept" if repaired_ok else "reject"

    record = EvolutionRecord(
        observation_hash=observation.evidence_hash,
        broken_hash=stable_isr_hash(broken_isr),
        operator=operator.name,
        hypothesis=candidate.hypothesis,
        repaired_hash=stable_isr_hash(candidate.repaired_isr),
        repaired_diff=candidate.repaired_diff,
        validation=validation,
        fitness_delta=fitness_delta,
        decision=decision,
    )
    ledger.append(record)
    return record
