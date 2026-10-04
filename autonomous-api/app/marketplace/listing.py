from dataclasses import dataclass
from enum import Enum


class ProductStatus(str, Enum):
    DRAFT = "draft"
    VERIFIED = "verified"
    CERTIFIED = "certified"
    LISTED = "listed"
    SUSPENDED = "suspended"


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

    def can_list(self) -> bool:
        return (
            self.status is ProductStatus.CERTIFIED
            and self.price_minor >= 0
            and len(self.artifact_digest) == 64
            and len(self.evidence_digest) == 64
            and bool(self.license)
        )

    def publish(self) -> "SoftwareListing":
        if not self.can_list():
            raise ValueError("marketplace-listing-requires-certified-evidence")
        return SoftwareListing(**{**self.__dict__, "status": ProductStatus.LISTED})
