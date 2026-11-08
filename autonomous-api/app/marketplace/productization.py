"""Evidence-bound ESAP productization for the final marketplace phase."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from constitutional_architecture.governance.trusted_evidence_resolution import (  # noqa: E402
    GovernedProductCertification,
    TrustBoundary,
)

from app.engine.governed_pipeline import GovernedPipelineResult
from app.marketplace.listing import HumanMarketplaceAuthorization, SoftwareListing, ProductStatus
from certification.orchestration.implir_ingress_guard import (  # noqa: E402
    IsrIngressAuthority,
    assert_trusted_marketplace_ingress,
)

@dataclass(frozen=True)
class MarketplaceProductCandidate:
    product_id: str
    version: str
    name: str
    price_minor: int
    currency: str
    license: str
    pipeline_digest: str
    certification_digest: str
    artifact_digest: str
    evidence_digest: str
    documentation_digest: str

    def __post_init__(self):
        for value, label in (
            (self.product_id,"product-id"),(self.version,"version"),(self.name,"name"),
            (self.currency,"currency"),(self.license,"license"),(self.pipeline_digest,"pipeline"),
            (self.certification_digest,"certification"),(self.artifact_digest,"artifact"),
            (self.evidence_digest,"evidence"),(self.documentation_digest,"documentation")
        ):
            if not str(value).strip(): raise ValueError("marketplace-product-missing-"+label)
        for value,label in ((self.pipeline_digest,"pipeline"),(self.certification_digest,"certification"),
                            (self.artifact_digest,"artifact"),(self.evidence_digest,"evidence"),
                            (self.documentation_digest,"documentation")):
            if len(value)!=64: raise ValueError("marketplace-product-invalid-"+label+"-digest")
        if self.price_minor < 0: raise ValueError("marketplace-product-invalid-price")

    @property
    def product_digest(self):
        payload=self.__dict__.copy()
        return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def prepare_certified_product(
    pipeline: GovernedPipelineResult,
    *,
    product_id: str, version: str, name: str,
    price_minor: int, currency: str, license: str,
    certification_digest: str, artifact_digest: str,
    evidence_digest: str, documentation_digest: str,
    trust_boundary: TrustBoundary = TrustBoundary.LEGACY_DEVELOPMENT,
    governed_certification: GovernedProductCertification | None = None,
    ingress_authority: str = IsrIngressAuthority.ISR_REVISION.value,
    governed_lineage_ref: str = "",
) -> MarketplaceProductCandidate:
    if trust_boundary is TrustBoundary.PRODUCTION:
        assert_trusted_marketplace_ingress(
            ingress_authority,
            governed_lineage_ref=governed_lineage_ref or certification_digest,
        )
    if not pipeline.closure.ready_to_stop:
        raise ValueError("marketplace-product-requires-complete-certified-pipeline")
    if pipeline.closure.digest != certification_digest:
        raise ValueError("marketplace-product-certification-mismatch")
    if trust_boundary is TrustBoundary.PRODUCTION:
        if governed_certification is None:
            raise ValueError("marketplace-product-governed-certification-required")
        if not governed_certification.verify_digest():
            raise ValueError("marketplace-product-governed-certification-invalid")
        if governed_certification.certification_digest != certification_digest:
            raise ValueError("marketplace-product-governed-certification-digest-mismatch")
        if governed_certification.artifact_sha256 != artifact_digest:
            raise ValueError("marketplace-product-governed-artifact-mismatch")
        if len(evidence_digest) != 64:
            raise ValueError("marketplace-product-governed-evidence-digest-invalid")
    return MarketplaceProductCandidate(
        product_id,version,name,price_minor,currency,license,pipeline.pipeline_digest,
        certification_digest,artifact_digest,evidence_digest,documentation_digest,
    )

def materialize_listing(candidate: MarketplaceProductCandidate) -> SoftwareListing:
    return SoftwareListing(
        product_id=candidate.product_id, version=candidate.version, name=candidate.name,
        price_minor=candidate.price_minor, currency=candidate.currency,
        artifact_digest=candidate.artifact_digest, evidence_digest=candidate.evidence_digest,
        status=ProductStatus.CERTIFIED, license=candidate.license,
    )

def require_human_listing_authorization(candidate: MarketplaceProductCandidate, authorization: HumanMarketplaceAuthorization) -> None:
    if not authorization.permits("list", candidate.product_id, candidate.evidence_digest):
        raise ValueError("marketplace-listing-human-authorization-mismatch")
