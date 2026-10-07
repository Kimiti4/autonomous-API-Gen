"""Governed software marketplace publication and sale authorization."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib, json

class ProductStatus(str, Enum):
    DRAFT="draft"; VERIFIED="verified"; CERTIFIED="certified"; LISTED="listed"; SUSPENDED="suspended"; SOLD="sold"

@dataclass(frozen=True)
class HumanMarketplaceAuthorization:
    authorization_id: str
    authorized_by: str
    action: str
    product_id: str
    approved_evidence_digest: str
    def __post_init__(self):
        if not self.authorization_id.strip() or not self.authorized_by.strip():
            raise ValueError("marketplace-human-authorization-required")
        if self.action not in {"list","sell"}: raise ValueError("marketplace-invalid-authorization-action")
        if not self.product_id.strip() or len(self.approved_evidence_digest)!=64:
            raise ValueError("marketplace-authorization-evidence-required")
    def permits(self, action, product_id, evidence_digest):
        return self.action==action and self.product_id==product_id and self.approved_evidence_digest==evidence_digest

@dataclass(frozen=True)
class SoftwareListing:
    product_id: str
    version: str
    name: str
    price_minor: int
    currency: str
    artifact_digest: str
    evidence_digest: str
    status: ProductStatus
    license: str
    def can_list(self, authorization=None):
        return (self.status is ProductStatus.CERTIFIED and self.price_minor>=0 and len(self.artifact_digest)==64
                and len(self.evidence_digest)==64 and bool(self.license)
                and authorization is not None and authorization.permits("list",self.product_id,self.evidence_digest))
    def publish(self, authorization=None):
        if not self.can_list(authorization): raise ValueError("marketplace-listing-requires-certified-human-authorization")
        return SoftwareListing(**{**self.__dict__,"status":ProductStatus.LISTED})
    def sell(self, authorization=None):
        if self.status is not ProductStatus.LISTED: raise ValueError("marketplace-sale-requires-listed-product")
        if authorization is None or not authorization.permits("sell",self.product_id,self.evidence_digest):
            raise ValueError("marketplace-sale-requires-human-authorization")
        return SoftwareListing(**{**self.__dict__,"status":ProductStatus.SOLD})

def authorization_digest(authorization):
    payload={k:getattr(authorization,k) for k in ("authorization_id","authorized_by","action","product_id","approved_evidence_digest")}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
