import pytest

from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
from tiannara.application.publication.repository_publisher_contract import (
    ProviderPublicationReceipt,
    SystemDeploymentBundle,
    publish_bundle,
)
from tiannara.application.publication.providers.github import GitHubProvider
from tiannara.application.publication.uber_for_boats import run_uber_for_boats
from tiannara.domain.services.canonical import canonical_hash


FILES = {"app/main.py": "print('hello')\n"}
ISR_HASH = "isr-sha-256"
ARTIFACT_HASH = canonical_hash(FILES)


class _Provider:
    def __init__(self):
        self.calls = []

    def publish_repository(self, name, bundle, files):
        self.calls.append((name, bundle, dict(files)))
        return ProviderPublicationReceipt(
            repo_url="https://example.invalid/generated",
            commit_sha="commit-123",
            artifact_hash=canonical_hash(files),
        )

    def verify_publication(self, receipt, files):
        return receipt.artifact_hash == canonical_hash(files)


def _certified_ledger():
    ledger = EvolutionLedger()
    ref = ledger.append_event(
        EvolutionEvent(
            event_id="certificate-1",
            evolution_id="evolution-1",
            sequence=0,
            event_type=EventType.CERTIFICATION,
            subject_id=ARTIFACT_HASH,
            artifact_hash=ARTIFACT_HASH,
            isr_hash=ISR_HASH,
            payload={
                "verdict": "CERTIFIED",
                "bounded": False,
                "artifact_hash": ARTIFACT_HASH,
                "isr_hash": ISR_HASH,
            },
        ),
        evolution_id="evolution-1",
    )
    return ledger, ref


def _bundle(refs):
    return SystemDeploymentBundle(
        isr_hash=ISR_HASH,
        artifact_hash=ARTIFACT_HASH,
        certification_refs=tuple(refs),
        deployment_ref="deployment-1",
        artifact_files=FILES,
    )


def test_publication_requires_explicit_gate_approval_and_exact_bytes():
    ledger, ref = _certified_ledger()
    provider = _Provider()
    with pytest.raises(ValueError, match="did not explicitly approve"):
        publish_bundle(_bundle([ref]), provider, ledger, lambda _ref: False)
    assert provider.calls == []


def test_publication_requires_candidate_bound_certification():
    ledger, ref = _certified_ledger()
    bundle = _bundle([ref])
    bundle = SystemDeploymentBundle(
        isr_hash="different-isr",
        artifact_hash=bundle.artifact_hash,
        certification_refs=bundle.certification_refs,
        deployment_ref=bundle.deployment_ref,
        artifact_files=bundle.artifact_files,
    )
    provider = _Provider()
    with pytest.raises(ValueError, match="typed hashes do not bind"):
        publish_bundle(bundle, provider, ledger, lambda _ref: True)
    assert provider.calls == []


def test_publication_requires_artifact_hash_to_match_file_bytes():
    ledger, ref = _certified_ledger()
    bundle = SystemDeploymentBundle(
        isr_hash=ISR_HASH,
        artifact_hash="not-the-file-hash",
        certification_refs=(ref,),
        deployment_ref="deployment-1",
        artifact_files=FILES,
    )
    with pytest.raises(ValueError, match="does not match supplied bytes"):
        publish_bundle(bundle, _Provider(), ledger, lambda _ref: True)


def test_publication_requires_provider_receipt_bound_to_uploaded_bytes():
    ledger, ref = _certified_ledger()

    class _BadProvider:
        def publish_repository(self, name, bundle, files):
            return ProviderPublicationReceipt(
                repo_url="https://example.invalid/wrong",
                commit_sha="commit-123",
                artifact_hash="wrong-hash",
            )

        def verify_publication(self, receipt, files):
            return True

    with pytest.raises(ValueError, match="receipt does not bind uploaded artifact bytes"):
        publish_bundle(_bundle([ref]), _BadProvider(), ledger, lambda _ref: True)


def test_successful_publication_records_delivery_not_certification():
    ledger, ref = _certified_ledger()
    provider = _Provider()
    result = publish_bundle(_bundle([ref]), provider, ledger, lambda _ref: True)

    assert result.repo_url == "https://example.invalid/generated"
    assert result.commit_refs == ("commit-123",)
    assert provider.calls[0][2] == FILES
    event = ledger.event_by_ref(result.ledger_ref)
    assert event.event_type is EventType.DELIVERY
    assert event.payload["artifact_hash"] == ARTIFACT_HASH
    assert ledger.verify_event_chain()


def test_simulated_github_provider_never_returns_success():
    with pytest.raises(RuntimeError, match="no live API implementation"):
        GitHubProvider(token="secret").create_repository("demo", _bundle(["cert"]))


def test_uber_for_boats_demo_does_not_mint_certification_or_publish():
    ledger = EvolutionLedger()
    result = run_uber_for_boats(github_token="secret", ledger=ledger)

    assert result["status"] == "BLOCKED"
    assert result["verified"] is False
    assert result["published"] is False
    assert result["repo_url"] is None
    assert ledger.event_count == 0


def test_publication_requires_remote_readback_verification():
    ledger, ref = _certified_ledger()

    class _NoReadbackProvider:
        def __init__(self):
            self.calls = []

        def publish_repository(self, name, bundle, files):
            self.calls.append("publish")
            return ProviderPublicationReceipt(
                repo_url="https://example.invalid/repo",
                commit_sha="commit-123",
                artifact_hash=canonical_hash(files),
            )

    provider = _NoReadbackProvider()
    with pytest.raises(ValueError, match="remote read-back verification"):
        publish_bundle(_bundle([ref]), provider, ledger, lambda _ref: True)
    assert provider.calls == []


@pytest.mark.parametrize(
    "files",
    [
        {".git/config": "malicious"},
        {".TIANNARA/manifest.json": "reserved"},
        {"src/Main.py": "one", "src/main.py": "two"},
    ],
)
def test_publication_rejects_reserved_and_casefolded_paths(files):
    ledger, ref = _certified_ledger()
    bundle = SystemDeploymentBundle(
        isr_hash=ISR_HASH,
        artifact_hash=canonical_hash(files),
        certification_refs=(ref,),
        deployment_ref="deployment-1",
        artifact_files=files,
    )
    with pytest.raises(ValueError, match="unsafe artifact path|duplicate normalized"):
        publish_bundle(bundle, _Provider(), ledger, lambda _ref: True)
