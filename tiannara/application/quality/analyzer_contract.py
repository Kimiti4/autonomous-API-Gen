"""R2.10.32.7 — The Analyzer Contract: the evidence-production boundary.

32.1–32.6 settled the OBLIGATION layer (what must be true and how it
originates); 32.7 settles the EVIDENCE layer (what produces the
measurements that certification judges). The invariant that governs it
is the three-way distinction, made structural rather than merely
documented:

    Analyzer observation != ISR obligation != Certification verdict

An analyzer produces OBSERVATIONS — Ruff finds an unused import, Bandit
finds a hardcoded secret, the responsibility analyzer finds a cluster
structure. None of those is an obligation (obligations originate in the
ISR) and none is a verdict (verdicts are the certifier's judgment
against gates). The moment an analyzer can declare "this architectural
decision is invalid," it has become a second source of architectural
truth. This contract makes that impossible: analyzers emit findings with
provenance, and the only legitimate path from a finding to an obligation
is the OPTIONAL `obligation_id` link to something the ISR (or a declared
derivation from it) already carries.

`obligation_id` being optional is the design decision that makes the
contract honest: obligation-realization evidence (32.2/32.4 traces)
carries an obligation_id; emergent-property evidence (32.5 concentration
findings) does not. Forcing both through a mandatory obligation field
would either fabricate obligations for emergent findings or strip the
linkage from realization findings — the optional field is what lets one
contract serve both while keeping the distinction visible.

No concrete external tools here (Ruff, ESLint, Clippy are 32.8
adapters): building an adapter before the contract is how tool semantics
leak into certification semantics. No verdict logic: the certifier
(32.0 substrate) remains the only verdict authority.
"""
import hashlib
from dataclasses import dataclass
from typing import Optional, Protocol

__all__ = [
    "Analyzer",
    "AnalyzerContractViolation",
    "AnalyzerFinding",
    "AnalyzerIdentity",
    "AnalyzerResult",
    "ReferenceAnalyzer",
    "derive_execution_identity",
    "obligation_exists",
    "validate_obligation_links",
]


class AnalyzerContractViolation(ValueError):
    """An analyzer result violates the evidence-production contract."""


@dataclass(frozen=True)
class AnalyzerIdentity:
    """An analyzer's declared identity: what it is, which languages it
    covers, and which evidence classes it produces."""

    analyzer_id: str
    analyzer_version: str
    supported_languages: tuple[str, ...]
    supported_evidence_classes: tuple[str, ...]


@dataclass(frozen=True)
class AnalyzerFinding:
    """A single OBSERVATION. Not an obligation — obligations originate in
    the ISR. Not a verdict — verdicts are the certifier's. The optional
    obligation_id is the only legitimate link from evidence to
    obligation, and it points at something the ISR (or a declared
    derivation from it) already carries."""

    finding_id: str
    analyzer_id: str
    analyzer_version: str
    artifact_identity: str  # which artifact this ran against
    configuration_identity: str  # the analyzer configuration
    execution_identity: str  # this execution instance
    severity: str
    category: str
    description: str
    location: Optional[str]
    evidence_refs: tuple[str, ...]
    obligation_id: Optional[str]  # optional: obligation-linked vs emergent evidence


@dataclass(frozen=True)
class AnalyzerResult:
    """An analyzer's full execution result, carrying enough provenance to
    answer: who produced this, which version, against which artifact,
    under which configuration, what was observed, where the evidence is,
    and whether it can be reproduced."""

    analyzer_id: str
    analyzer_version: str
    artifact_identity: str
    configuration_identity: str
    execution_identity: str
    deterministic: bool  # reproducible semantics, declared
    findings: tuple[AnalyzerFinding, ...]
    evidence_refs: tuple[str, ...]


def derive_execution_identity(
    analyzer_id: str,
    analyzer_version: str,
    artifact_identity: str,
    configuration_identity: str,
) -> str:
    """Deterministic execution identity: derived from the identity tuple, so
    replay reproduces the execution instance (canonical-form and
    ledger-replay discipline)."""
    seed = (
        f"{analyzer_id}::{analyzer_version}::{artifact_identity}"
        f"::{configuration_identity}"
    )
    return f"exec-{hashlib.sha256(seed.encode()).hexdigest()[:16]}"


def obligation_exists(
    obligation_id: str,
    isr,
    derived_obligations: tuple = (),
) -> bool:
    """Resolve an obligation link against the obligation-bearing carriers:
    F requirements, 32.1 decisions, 32.3 threats, and the 32.6 derived
    obligation set (an ephemeral product of the declared derivation
    rules)."""
    system = isr.system
    if any(r.requirement_id == obligation_id for r in system.requirements):
        return True
    if any(d.decision_id == obligation_id for d in system.architectural_decisions):
        return True
    if any(t.threat_id == obligation_id for t in system.security_threats):
        return True
    if any(f.failure_id == obligation_id for f in derived_obligations):
        return True
    return False


def validate_obligation_links(
    result: AnalyzerResult,
    isr,
    derived_obligations: tuple = (),
) -> None:
    """An obligation link that resolves to nothing is a contract violation,
    not a silent drop."""
    for finding in result.findings:
        if finding.obligation_id is None:
            continue
        if not obligation_exists(
            finding.obligation_id, isr, derived_obligations
        ):
            raise AnalyzerContractViolation(
                f"finding {finding.finding_id} links to obligation "
                f"{finding.obligation_id}, which resolves to nothing: an "
                "obligation link must point at an obligation the ISR or a "
                "declared derivation already carries"
            )


class Analyzer(Protocol):
    """The evidence-production contract. An analyzer produces observations
    with provenance; it never produces obligations or verdicts and never
    decides architectural truth."""

    @property
    def identity(self) -> AnalyzerIdentity: ...

    def analyze(self, artifact, configuration) -> AnalyzerResult: ...


class ReferenceAnalyzer:
    """The minimal deterministic reference implementation of the Analyzer
    contract — the conformance exemplar 32.8's real adapters implement
    rather than only a protocol. Deterministic by construction: findings
    are derived from the artifact's canonical content, and the execution
    identity is derived from the identity tuple."""

    _IDENTITY = AnalyzerIdentity(
        analyzer_id="reference-analyzer",
        analyzer_version="1.0.0",
        supported_languages=("python",),
        supported_evidence_classes=("reference_inspection",),
    )

    @property
    def identity(self) -> AnalyzerIdentity:
        return self._IDENTITY

    def analyze(self, artifact, configuration) -> AnalyzerResult:
        artifact_identity = artifact["provenance"]["artifact_hash"]
        configuration_identity = configuration["configuration_id"]
        execution_identity = derive_execution_identity(
            self._IDENTITY.analyzer_id,
            self._IDENTITY.analyzer_version,
            artifact_identity,
            configuration_identity,
        )
        findings = []
        for index, module in enumerate(
            sorted(artifact["modules"], key=lambda m: m["module_id"])
        ):
            module_id = module["module_id"]
            findings.append(
                AnalyzerFinding(
                    finding_id=f"{module_id}::reference-inspection",
                    analyzer_id=self._IDENTITY.analyzer_id,
                    analyzer_version=self._IDENTITY.analyzer_version,
                    artifact_identity=artifact_identity,
                    configuration_identity=configuration_identity,
                    execution_identity=execution_identity,
                    severity=(
                        "ADVISORY" if module.get("entities") else "WARNING"
                    ),
                    category="reference_inspection",
                    description=f"reference inspection of module {module_id}",
                    location=module_id,
                    evidence_refs=(
                        f"analysis-{artifact_identity[:8]}-{index}",
                    ),
                    obligation_id=None,
                )
            )
        evidence_refs = tuple(
            f"analysis-{artifact_identity[:8]}-{i}"
            for i in range(len(findings))
        )
        return AnalyzerResult(
            analyzer_id=self._IDENTITY.analyzer_id,
            analyzer_version=self._IDENTITY.analyzer_version,
            artifact_identity=artifact_identity,
            configuration_identity=configuration_identity,
            execution_identity=execution_identity,
            deterministic=True,
            findings=tuple(findings),
            evidence_refs=evidence_refs,
        )