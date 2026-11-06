import pytest

from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.application.publication.repository_publisher_contract import (
    SystemDeploymentBundle,
    publish_bundle,
)
from tiannara.application.publication.secret_boundary import scan_artifact_secrets
from tiannara.domain.services.canonical import canonical_hash


def test_secret_scanner_detects_common_tokens_and_private_key_material():
    files = {
        "src/config.py": "GITHUB_TOKEN = 'ghp_" + "A" * 36 + "'",
        "keys/deploy.pem": "not even needed",
        ".env.production": "DATABASE_PASSWORD=real-password-material",
        "src/key.txt": "-----BEGIN PRIVATE KEY-----",
        "src/db.txt": "DATABASE_URL=postgres://app:supersecretpassword@db.example/app",
    }
    findings = scan_artifact_secrets(files)
    assert any("GITHUB_TOKEN" in item for item in findings)
    assert any("SENSITIVE_CREDENTIAL_FILE" in item for item in findings)
    assert any(".env.production" in item for item in findings)
    assert any("PRIVATE_KEY_BLOCK" in item for item in findings)
    assert any("DATABASE_URL_CREDENTIALS" in item for item in findings)


def test_secret_scanner_allows_explicit_example_placeholders():
    findings = scan_artifact_secrets({
        ".env.example": "API_KEY=YOUR_API_KEY_HERE\nPASSWORD=change-this-before-use\n",
        "README.md": "Set your own credentials in your local environment.",
    })
    assert findings == ()


def test_publication_blocks_secret_bearing_artifact_before_provider_call():
    secret_files = {"app/config.py": "GITHUB_TOKEN = 'ghp_" + "B" * 36 + "'"}
    artifact_hash = canonical_hash(secret_files)
    ledger = EvolutionLedger()
    bundle = SystemDeploymentBundle(
        isr_hash="isr-hash",
        artifact_hash=artifact_hash,
        certification_refs=("not-looked-up",),
        deployment_ref="deployment-1",
        artifact_files=secret_files,
    )

    class _Provider:
        def __init__(self):
            self.calls = []

        def publish_repository(self, name, bundle, files):
            self.calls.append("publish")
            raise AssertionError("provider must not be called")

        def verify_publication(self, receipt, files):
            return False

    provider = _Provider()
    with pytest.raises(ValueError, match="artifact secret scan failed"):
        publish_bundle(bundle, provider, ledger, lambda _ref: True)
    assert provider.calls == []
