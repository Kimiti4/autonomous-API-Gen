"""Fail-closed publication contract.

Publication consumes independently earned certification and exact artifact
bytes. It never creates certification evidence or treats repository creation
alone as a successful upload.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath, PureWindowsPath
from typing import Callable, Mapping, Protocol

from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
from tiannara.domain.services.canonical import canonical_hash


@dataclass(frozen=True)
class SystemDeploymentBundle:
    isr_hash: str
    artifact_hash: str
    certification_refs: tuple[str, ...]
    deployment_ref: str
    artifact_files: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderPublicationReceipt:
    repo_url: str
    commit_sha: str
    artifact_hash: str


class RepositoryProvider(Protocol):
    def publish_repository(
        self,
        name: str,
        bundle: SystemDeploymentBundle,
        files: Mapping[str, str],
    ) -> ProviderPublicationReceipt: ...


@dataclass(frozen=True)
class PublicationResult:
    repo_url: str
    commit_refs: tuple[str, ...]
    ledger_ref: str
    bundle_hash: str


def _validate_artifact_files(files: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(files, Mapping) or not files:
        raise ValueError("publication blocked: exact artifact files are required")
    normalized: dict[str, str] = {}
    for path, content in files.items():
        if (
            not isinstance(path, str)
            or not path
            or "\x00" in path
            or "\\" in path
        ):
            raise ValueError(f"publication blocked: unsafe artifact path {path!r}")
        posix = PurePosixPath(path)
        windows = PureWindowsPath(path)
        if (
            posix.is_absolute()
            or windows.is_absolute()
            or bool(windows.drive)
            or any(part in ("", ".", "..") for part in posix.parts)
        ):
            raise ValueError(f"publication blocked: unsafe artifact path {path!r}")
        if not isinstance(content, str):
            raise ValueError(f"publication blocked: artifact {path!r} is not text")
        if path in normalized:
            raise ValueError(f"publication blocked: duplicate artifact path {path!r}")
        normalized[path] = content
    return normalized


def publish_bundle(
    bundle: SystemDeploymentBundle,
    provider: RepositoryProvider,
    ledger: EvolutionLedger,
    certification_gate: Callable[[str], bool],
) -> PublicationResult:
    """Publish exact bytes only after explicit, candidate-bound certification.

    The certification callback must return literal True. Ledger lookups and
    chain integrity are independently checked; a truthy object is not approval.
    """
    if not bundle.isr_hash or not bundle.artifact_hash:
        raise ValueError("publication blocked: ISR and artifact hashes are required")
    if not bundle.certification_refs:
        raise ValueError("publication blocked: no independent certification reference supplied")
    if not callable(certification_gate):
        raise ValueError("publication blocked: authoritative certification gate is required")
    if not ledger.verify_event_chain():
        raise ValueError("publication blocked: evidence ledger chain is invalid")

    files = _validate_artifact_files(bundle.artifact_files)
    computed_hash = canonical_hash(files)
    if computed_hash != bundle.artifact_hash:
        raise ValueError("publication blocked: artifact hash does not match supplied bytes")

    for ref in bundle.certification_refs:
        event = ledger.event_by_ref(ref)
        if event is None:
            raise ValueError(f"publication blocked: certification {ref!r} is missing")
        if event.event_type is not EventType.CERTIFICATION:
            raise ValueError(f"publication blocked: {ref!r} is not a certification event")
        if event.subject_id != bundle.artifact_hash:
            raise ValueError(f"publication blocked: certification {ref!r} is for another artifact")
        if event.payload.get("verdict") != "CERTIFIED" or event.payload.get("bounded") is not False:
            raise ValueError(f"publication blocked: certification {ref!r} is not unbounded CERTIFIED evidence")
        if event.payload.get("artifact_hash") != bundle.artifact_hash:
            raise ValueError(f"publication blocked: certification {ref!r} does not bind artifact hash")
        if event.payload.get("isr_hash") != bundle.isr_hash:
            raise ValueError(f"publication blocked: certification {ref!r} does not bind ISR hash")
        try:
            approved = certification_gate(ref)
        except Exception as exc:
            raise ValueError(
                f"publication blocked: certification gate failed for {ref!r}: {type(exc).__name__}"
            ) from exc
        if approved is not True:
            raise ValueError(f"publication blocked: certification gate did not explicitly approve {ref!r}")

    publish = getattr(provider, "publish_repository", None)
    if not callable(publish):
        raise ValueError("publication blocked: provider lacks an exact-bytes publish operation")
    receipt = publish(
        f"tiannara-{bundle.artifact_hash[:12]}",
        bundle,
        files,
    )
    if not isinstance(receipt, ProviderPublicationReceipt):
        raise ValueError("publication blocked: provider returned no verifiable publication receipt")
    if (
        not receipt.repo_url
        or not receipt.commit_sha
        or receipt.artifact_hash != computed_hash
    ):
        raise ValueError("publication blocked: provider receipt does not bind uploaded artifact bytes")

    event = EvolutionEvent(
        event_id=f"delivery-{bundle.artifact_hash[:12]}",
        evolution_id=bundle.artifact_hash,
        sequence=0,
        event_type=EventType.DELIVERY,
        subject_id=bundle.artifact_hash,
        artifact_hash=bundle.artifact_hash,
        isr_hash=bundle.isr_hash,
        payload={
            "kind": "repository_publication",
            "repo_url": receipt.repo_url,
            "commit_sha": receipt.commit_sha,
            "artifact_hash": computed_hash,
            "isr_hash": bundle.isr_hash,
            "certification_refs": list(bundle.certification_refs),
        },
    )
    ledger_ref = ledger.append_event(event, evolution_id=bundle.artifact_hash)
    return PublicationResult(
        repo_url=receipt.repo_url,
        commit_refs=(receipt.commit_sha,),
        ledger_ref=ledger_ref,
        bundle_hash=computed_hash,
    )
