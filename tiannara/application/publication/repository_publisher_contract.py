"""Publisher contract -- provider-neutral, ledger-addressable, never certifies."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
from tiannara.domain.services.canonical import canonical_hash

@dataclass(frozen=True)
class SystemDeploymentBundle:
    isr_hash: str; artifact_hash: str; certification_refs: tuple[str,...]; deployment_ref: str

class RepositoryProvider(Protocol):
    def create_repository(self, name: str, bundle: SystemDeploymentBundle) -> str: ...
    def push_repository(self, local_path: str, remote_url: str) -> str: ...
    def create_release(self, repo: str, tag: str) -> str: ...
    def create_milestone(self, repo: str, title: str) -> str: ...
    def create_issue(self, repo: str, title: str) -> str: ...

@dataclass(frozen=True)
class PublicationResult:
    repo_url: str; commit_refs: tuple[str,...]; ledger_ref: str; bundle_hash: str

def publish_bundle(bundle: SystemDeploymentBundle, provider: RepositoryProvider, ledger: EvolutionLedger, certification_gate) -> PublicationResult:
    # Gate: never publish if not CERTIFIED
    for ref in bundle.certification_refs:
        ev = ledger.event_by_ref(ref)
        if ev is None or ev.payload.get("verdict") != "CERTIFIED":
            raise ValueError(f"certification {ref} not CERTIFIED -- publication blocked")
        if ev.payload.get("bounded") or ev.payload.get("verdict") == "BOUNDED":
            raise ValueError("bounded evidence -- publication blocked")
    # Ledger-addressable
    payload = {"bundle_hash": canonical_hash(bundle.artifact_hash), "isr": bundle.isr_hash}
    ev = EvolutionEvent(event_id=f"publish-{bundle.artifact_hash[:8]}", evolution_id=bundle.artifact_hash, sequence=0, event_type=EventType.CERTIFICATION, subject_id=bundle.artifact_hash, payload=payload)
    ref = ledger.append_event(ev, evolution_id=bundle.artifact_hash)
    repo_url = provider.create_repository(f"tiannara-{bundle.artifact_hash[:8]}", bundle)
    return PublicationResult(repo_url, (ref,), ref, bundle.artifact_hash)
