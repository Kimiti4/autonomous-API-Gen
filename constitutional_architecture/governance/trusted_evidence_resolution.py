"""Mandatory trusted evidence resolution for governed production paths (FS00-FS-039 cp2).

Opaque strings (for example ``ci:run-17``) are never trusted. Production callers
must inject :class:`GovernedTrustedEvidenceService` backed by a durable
:class:`TrustedEvidenceRegistry` ledger.

**Security note:** The registry's SHA-256 hash chain provides tamper *evidence* for
an append-only file, not independent authenticity. An actor who can rewrite the
entire ledger file can forge a valid chain from genesis. External checkpoint
anchoring, asymmetric signatures on checkpoints, and strict filesystem ACLs are
not implemented in this checkpoint; do not describe the ledger as immutable against
a malicious host administrator.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from constitutional_architecture.governance.trusted_evidence_registry import (
    SCHEMA_ID,
    TrustedEvidenceRecord,
    TrustedEvidenceRegistry,
)

TRUSTED_EVIDENCE_LEDGER_ENV = "ESAP_TRUSTED_EVIDENCE_LEDGER"
CERTIFICATION_SCHEMA = "tiannara.governance.product_certification"
CERTIFICATION_VERSION = "1.0.0"
SAMPLE_CONTRACT_SCOPE = "sample_contract"
PRODUCT_SCOPE = "product"


class TrustBoundary(str, Enum):
    """Only ``legacy_development`` may accept opaque evidence references."""

    PRODUCTION = "production"
    LEGACY_DEVELOPMENT = "legacy_development"


@dataclass(frozen=True)
class EvidenceBinding:
    candidate_id: str
    artifact_sha256: str
    source_revision: str = ""
    artifact_manifest_digest: str = ""


@dataclass(frozen=True)
class GovernedProductCertification:
    """Product-level certification bound to exact artifact and evidence lineage."""

    certification_id: str
    candidate_id: str
    artifact_sha256: str
    source_revision: str
    evidence_ids: tuple[str, ...]
    verifier_identity: str
    verification_environment: str
    verification_scope: str
    issued_at: str
    expires_at: str
    certification_digest: str
    schema_id: str = CERTIFICATION_SCHEMA
    schema_version: str = CERTIFICATION_VERSION

    def verify_digest(self) -> bool:
        payload = {
            "certification_id": self.certification_id,
            "candidate_id": self.candidate_id,
            "artifact_sha256": self.artifact_sha256,
            "source_revision": self.source_revision,
            "evidence_ids": list(self.evidence_ids),
            "verifier_identity": self.verifier_identity,
            "verification_environment": self.verification_environment,
            "verification_scope": self.verification_scope,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
        }
        expected = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return self.certification_digest == expected


@dataclass(frozen=True)
class GovernedPromotionRequest:
    candidate_id: str
    artifact_sha256: str
    source_revision: str
    evidence_ids: tuple[str, ...]
    certification_id: str
    from_environment: str
    to_environment: str


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def is_trusted_evidence_id(ref: str) -> bool:
    """Registry-issued identifiers use the ``tev-`` prefix."""
    ref = str(ref).strip()
    return ref.startswith("tev-") and len(ref) > 12


class GovernedTrustedEvidenceService:
    """Fail-closed evidence resolution for governed production operations."""

    def __init__(self, registry: TrustedEvidenceRegistry) -> None:
        self._registry = registry
        ok, detail = registry.verify_ledger_integrity()
        if not ok:
            raise ValueError(f"trusted-evidence-ledger-unusable:{detail}")

    @property
    def registry(self) -> TrustedEvidenceRegistry:
        return self._registry

    @classmethod
    def require_for_boundary(
        cls,
        boundary: TrustBoundary,
        *,
        ledger_path: str | None = None,
        registry: TrustedEvidenceRegistry | None = None,
    ) -> GovernedTrustedEvidenceService | None:
        if boundary is TrustBoundary.LEGACY_DEVELOPMENT:
            return None
        if registry is not None:
            return cls(registry)
        path = (ledger_path or os.getenv(TRUSTED_EVIDENCE_LEDGER_ENV) or "").strip()
        if not path:
            raise ValueError("trusted-evidence-ledger-unconfigured")
        return cls(TrustedEvidenceRegistry(path))

    def reject_opaque_refs(self, refs: Iterable[str]) -> None:
        for ref in refs:
            r = str(ref).strip()
            if not r:
                raise ValueError("trusted-evidence-missing-id")
            if not is_trusted_evidence_id(r):
                raise ValueError(f"trusted-evidence-opaque-ref:{r}")

    def resolve_evidence(
        self,
        evidence_ids: Iterable[str],
        *,
        binding: EvidenceBinding,
        require_runtime: bool = True,
    ) -> tuple[TrustedEvidenceRecord, ...]:
        self.reject_opaque_refs(evidence_ids)
        records = self._registry.require_resolved(
            evidence_ids,
            candidate_id=binding.candidate_id,
            require_runtime=require_runtime,
        )
        for rec in records:
            if binding.artifact_sha256 and rec.artifact_sha256:
                if rec.artifact_sha256 != binding.artifact_sha256:
                    raise ValueError(
                        f"trusted-evidence-artifact-mismatch:{rec.evidence_id}"
                    )
            if binding.source_revision and rec.source_revision:
                if rec.source_revision != binding.source_revision:
                    raise ValueError(
                        f"trusted-evidence-source-revision-mismatch:{rec.evidence_id}"
                    )
            if binding.artifact_manifest_digest and rec.artifact_manifest_digest:
                if rec.artifact_manifest_digest != binding.artifact_manifest_digest:
                    raise ValueError(
                        f"trusted-evidence-manifest-mismatch:{rec.evidence_id}"
                    )
        return records

    def issue_product_certification(
        self,
        *,
        binding: EvidenceBinding,
        evidence_ids: Iterable[str],
        verifier_identity: str,
        verification_environment: str,
        verification_scope: str,
        issued_at: str,
        expires_at: str,
        require_runtime: bool = True,
    ) -> GovernedProductCertification:
        if verification_scope == SAMPLE_CONTRACT_SCOPE:
            raise ValueError(
                "governed-certification-sample-contract-not-product:"
                "use explicit sample-contract lane; cannot issue product certification"
            )
        if verification_scope != PRODUCT_SCOPE:
            raise ValueError("governed-certification-invalid-scope")
        resolved = self.resolve_evidence(
            evidence_ids,
            binding=binding,
            require_runtime=require_runtime,
        )
        cert_id = f"tev-cert-{binding.candidate_id[:8]}-{_digest({'e': [r.evidence_id for r in resolved]})[:16]}"
        self._registry.register(
            candidate_id=binding.candidate_id,
            artifact_sha256=binding.artifact_sha256,
            source_revision=binding.source_revision,
            artifact_manifest_digest=binding.artifact_manifest_digest,
            evaluation_mode="governed_product_certification",
            verifier_identity=verifier_identity,
            verification_environment=verification_environment,
            runtime_verification_results="bound",
            test_execution_results="bound",
            evidence_provenance={
                "verification_scope": verification_scope,
                "bound_evidence_ids": [r.evidence_id for r in resolved],
                "schema_id": CERTIFICATION_SCHEMA,
                "schema_version": CERTIFICATION_VERSION,
            },
            evidence_id=cert_id,
        )
        payload = {
            "certification_id": cert_id,
            "candidate_id": binding.candidate_id,
            "artifact_sha256": binding.artifact_sha256,
            "source_revision": binding.source_revision,
            "evidence_ids": [r.evidence_id for r in resolved],
            "verifier_identity": verifier_identity,
            "verification_environment": verification_environment,
            "verification_scope": verification_scope,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "schema_id": CERTIFICATION_SCHEMA,
            "schema_version": CERTIFICATION_VERSION,
        }
        return GovernedProductCertification(
            certification_id=cert_id,
            candidate_id=binding.candidate_id,
            artifact_sha256=binding.artifact_sha256,
            source_revision=binding.source_revision,
            evidence_ids=tuple(r.evidence_id for r in resolved),
            verifier_identity=verifier_identity,
            verification_environment=verification_environment,
            verification_scope=verification_scope,
            issued_at=issued_at,
            expires_at=expires_at,
            certification_digest=_digest(payload),
        )

    def reload_certification(
        self,
        certification_id: str,
        *,
        binding: EvidenceBinding,
        require_runtime: bool = True,
    ) -> GovernedProductCertification:
        self.reject_opaque_refs((certification_id,))
        rec = self._registry.get(certification_id)
        if rec is None:
            raise ValueError(f"governed-certification-unknown:{certification_id}")
        if rec.evaluation_mode != "governed_product_certification":
            raise ValueError(f"governed-certification-wrong-type:{certification_id}")
        prov = dict(rec.evidence_provenance or {})
        scope = str(prov.get("verification_scope", ""))
        if scope != PRODUCT_SCOPE:
            raise ValueError(f"governed-certification-not-product:{certification_id}")
        bound_ids = tuple(str(x) for x in prov.get("bound_evidence_ids", ()))
        if not bound_ids:
            raise ValueError(f"governed-certification-missing-evidence-refs:{certification_id}")
        self.resolve_evidence(
            bound_ids,
            binding=binding,
            require_runtime=require_runtime,
        )
        issued_at = rec.captured_at
        expires_at = rec.expires_at or ""
        payload = {
            "certification_id": certification_id,
            "candidate_id": binding.candidate_id,
            "artifact_sha256": binding.artifact_sha256,
            "source_revision": binding.source_revision,
            "evidence_ids": list(bound_ids),
            "verifier_identity": rec.verifier_identity,
            "verification_environment": rec.verification_environment,
            "verification_scope": scope,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "schema_id": CERTIFICATION_SCHEMA,
            "schema_version": CERTIFICATION_VERSION,
        }
        cert = GovernedProductCertification(
            certification_id=certification_id,
            candidate_id=binding.candidate_id,
            artifact_sha256=binding.artifact_sha256,
            source_revision=binding.source_revision,
            evidence_ids=bound_ids,
            verifier_identity=rec.verifier_identity,
            verification_environment=rec.verification_environment,
            verification_scope=scope,
            issued_at=issued_at,
            expires_at=expires_at,
            certification_digest=_digest(payload),
        )
        if rec.candidate_id != binding.candidate_id:
            raise ValueError("governed-certification-candidate-mismatch")
        if rec.artifact_sha256 and rec.artifact_sha256 != binding.artifact_sha256:
            raise ValueError("governed-certification-artifact-mismatch")
        if rec.source_revision and rec.source_revision != binding.source_revision:
            raise ValueError("governed-certification-source-revision-mismatch")
        return cert

    def authorize_promotion(
        self,
        request: GovernedPromotionRequest,
        *,
        require_runtime: bool = True,
    ) -> GovernedProductCertification:
        binding = EvidenceBinding(
            candidate_id=request.candidate_id,
            artifact_sha256=request.artifact_sha256,
            source_revision=request.source_revision,
        )
        cert = self.reload_certification(
            request.certification_id,
            binding=binding,
            require_runtime=require_runtime,
        )
        self.resolve_evidence(
            request.evidence_ids,
            binding=binding,
            require_runtime=require_runtime,
        )
        if set(request.evidence_ids) != set(cert.evidence_ids):
            raise ValueError("governed-promotion-evidence-changed-since-certification")
        return cert

    def authorize_publication(
        self,
        *,
        binding: EvidenceBinding,
        certification_id: str,
        supplemental_evidence_ids: Iterable[str] = (),
        require_runtime: bool = True,
    ) -> GovernedProductCertification:
        cert = self.reload_certification(
            certification_id,
            binding=binding,
            require_runtime=require_runtime,
        )
        if supplemental_evidence_ids:
            self.resolve_evidence(
                supplemental_evidence_ids,
                binding=binding,
                require_runtime=require_runtime,
            )
        return cert
