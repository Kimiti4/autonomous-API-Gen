import shutil
from dataclasses import dataclass
from pathlib import Path
from ...domain.ports import EvidenceLedger, RepositoryPublisher
from ...domain.models.bundle import SystemDeploymentBundle
from ...domain.models.evidence import CertificationEvidence, Verdict
from .gate_evaluator import ExitGateEvaluator


@dataclass(frozen=True)
class PublishingIdentity:
    owner: str
    author_name: str
    author_email: str


@dataclass(frozen=True)
class AuthContext:
    """Present when an end user authenticates with repo scope."""

    github_username: str
    has_repo_scope: bool


class PublisherOrchestrator:
    def __init__(
        self,
        publisher: RepositoryPublisher,
        gate_evaluator: ExitGateEvaluator,
        ledger: EvidenceLedger,
        fallback_identity: PublishingIdentity,
        quarantine_dir: Path,
    ) -> None:
        self._publisher = publisher
        self._gates = gate_evaluator
        self._ledger = ledger
        self._fallback = fallback_identity
        self._quarantine_dir = quarantine_dir
        self._quarantine_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_identity(self, auth: AuthContext | None) -> PublishingIdentity:
        if auth and auth.has_repo_scope:
            return PublishingIdentity(
                owner=auth.github_username,
                author_name="Tiannara Evolution Engine",
                author_email="noreply@tiannara.local",
            )
        return self._fallback

    async def process(
        self,
        bundle: SystemDeploymentBundle | None,
        evidence: CertificationEvidence,
        auth: AuthContext | None = None,
    ) -> None:
        passed, gate_results = self._gates.evaluate(evidence)
        evidence.gate_results = gate_results
        evidence.verdict = Verdict.PASS if passed else Verdict.FAIL

        if not passed or bundle is None:
            self._quarantine(bundle, evidence)
        else:
            identity = self._resolve_identity(auth)
            url = await self._publisher.publish(
                bundle=bundle,
                evidence=evidence,
                owner=identity.owner,
                author_name=identity.author_name,
                author_email=identity.author_email,
            )
            print(f"[PUBLISHED] {evidence.project_id} -> {url}")

        self._ledger.append(evidence)

    def _quarantine(self, bundle: SystemDeploymentBundle | None, evidence: CertificationEvidence) -> None:
        evidence.verdict = Verdict.QUARANTINED
        if bundle is not None and bundle.path.exists():
            destination = self._quarantine_dir / evidence.project_id
            if destination.exists():
                shutil.rmtree(destination)
            shutil.move(str(bundle.path), destination)
            print(f"[QUARANTINED] {evidence.project_id} -> {destination}")
        else:
            print(f"[QUARANTINED] {evidence.project_id} (no bundle)")
