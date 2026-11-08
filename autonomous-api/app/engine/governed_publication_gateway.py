"""Workspace bridge for governed publication (FS00 checkpoint 042+)."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import get_settings

_WORKSPACE = Path(__file__).resolve().parents[3]
if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))

from constitutional_architecture.governance.candidate_promotion_lifecycle import (  # noqa: E402
    GovernedCandidatePromotionService,
)
from constitutional_architecture.governance.trusted_evidence_resolution import (  # noqa: E402
    GovernedTrustedEvidenceService,
)
from tiannara.application.governance.production_boundary import (  # noqa: E402
    governed_production_enabled,
    open_production_evidence_service,
    open_production_promotion_service,
)
from tiannara.application.publication.governed_publication_boundary import (  # noqa: E402
    GovernedPublicationBlocked,
    GovernedPublicationRequest,
    publish_and_handoff_governed,
    publish_governed_candidate,
)
from tiannara.application.publication.repository_publisher_contract import (  # noqa: E402
    RepositoryProvider,
)
from tiannara.application.evolution.ledger import EvolutionLedger  # noqa: E402


class GovernedPublicationUnavailable(RuntimeError):
    """Raised when governed production stores are not configured."""


@dataclass(frozen=True)
class GovernedPublicationStatus:
    governed_production_enabled: bool
    trusted_evidence_ledger: str
    governance_candidate_store: str
    explicit_production_flag: bool


def publication_status() -> GovernedPublicationStatus:
    _sync_governed_env_from_settings()
    settings = get_settings()
    return GovernedPublicationStatus(
        governed_production_enabled=governed_production_enabled(),
        trusted_evidence_ledger=settings.ESAP_TRUSTED_EVIDENCE_LEDGER.strip(),
        governance_candidate_store=settings.ESAP_GOVERNANCE_CANDIDATE_STORE.strip(),
        explicit_production_flag=bool(settings.ESAP_GOVERNED_PRODUCTION),
    )


def _sync_governed_env_from_settings() -> None:
    settings = get_settings()
    if settings.ESAP_GOVERNED_PRODUCTION:
        os.environ["ESAP_GOVERNED_PRODUCTION"] = "1"
    if settings.ESAP_TRUSTED_EVIDENCE_LEDGER.strip():
        os.environ["ESAP_TRUSTED_EVIDENCE_LEDGER"] = settings.ESAP_TRUSTED_EVIDENCE_LEDGER.strip()
    if settings.ESAP_GOVERNANCE_CANDIDATE_STORE.strip():
        os.environ["ESAP_GOVERNANCE_CANDIDATE_STORE"] = (
            settings.ESAP_GOVERNANCE_CANDIDATE_STORE.strip()
        )


def require_governed_services() -> tuple[
    GovernedTrustedEvidenceService, GovernedCandidatePromotionService
]:
    _sync_governed_env_from_settings()
    if not governed_production_enabled():
        raise GovernedPublicationUnavailable("governed-publication-not-configured")
    evidence = open_production_evidence_service()
    promotion = open_production_promotion_service()
    return evidence, promotion


class LocalPublicationProvider(RepositoryProvider):
    """In-process provider for tests and dry-run; does not touch a real git host."""

    def __init__(self, base_url: str = "https://governed.local") -> None:
        self._base = base_url.rstrip("/")

    def create_repository(self, name: str, bundle) -> str:
        return f"{self._base}/{name}"

    def push_repository(self, local_path: str, remote_url: str) -> str:
        return remote_url

    def create_release(self, repo: str, tag: str) -> str:
        return tag

    def create_milestone(self, repo: str, title: str) -> str:
        return title

    def create_issue(self, repo: str, title: str) -> str:
        return title


def execute_governed_publish(
    *,
    request: GovernedPublicationRequest,
    include_handoff: bool = False,
    provider: RepositoryProvider | None = None,
    isr_ingress_authority: str = "isr.core.revision",
    governed_lineage_ref: str = "",
) -> dict[str, Any]:
    from certification.orchestration.implir_ingress_guard import (
        assert_trusted_publication_ingress,
    )

    assert_trusted_publication_ingress(
        isr_ingress_authority,
        governed_lineage_ref=governed_lineage_ref,
    )
    evidence, promotion = require_governed_services()
    provider = provider or LocalPublicationProvider()
    ledger = EvolutionLedger()

    def _gate(ref: str):
        return ledger.event_by_ref(ref)

    try:
        if include_handoff:
            return publish_and_handoff_governed(
                request,
                provider=provider,
                ledger=ledger,
                evidence_service=evidence,
                promotion_service=promotion,
                certification_gate=_gate,
            )
        result = publish_governed_candidate(
            request,
            provider=provider,
            ledger=ledger,
            evidence_service=evidence,
            promotion_service=promotion,
            certification_gate=_gate,
        )
        return {
            "publication": {
                "repo_url": result.repo_url,
                "ledger_ref": result.ledger_ref,
                "bundle_hash": result.bundle_hash,
            },
            "candidate_id": request.candidate_id,
            "artifact_sha256": request.artifact_sha256,
            "certification_id": request.certification_id,
        }
    except GovernedPublicationBlocked as exc:
        raise GovernedPublicationUnavailable(str(exc)) from exc
