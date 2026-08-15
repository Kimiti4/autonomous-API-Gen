"""
Product publishing engine.
"""

from __future__ import annotations

from typing import Dict, Optional

from .certification import ProductCertificationEngine
from .models import (
    CertificationStatus,
    PublicationGuardrails,
    PublicationRequest,
    PublicationStatus,
    ProductCertificationPolicy,
    utcnow,
)


class PublishingEngine:
    """Publishes certified products to marketplaces."""

    def __init__(
        self,
        certification_engine: ProductCertificationEngine,
        policy: ProductCertificationPolicy,
        marketplace_engine=None,
    ) -> None:
        self.certification_engine = certification_engine
        self.policy = policy
        self.marketplace_engine = marketplace_engine

        self.publications: Dict[str, PublicationRequest] = {}

    def request_publication(
        self,
        product_id: str,
        product_version: str,
        marketplace_id: str,
        publisher_id: str,
        certification_report_id: str,
        pricing_plan_ref: Optional[str] = None,
        approval_ref: Optional[str] = None,
        guardrails: Optional[PublicationGuardrails] = None,
    ) -> PublicationRequest:
        report = self.certification_engine.reports.get(certification_report_id)

        if not report:
            raise KeyError(
                f"Certification report not found: {certification_report_id}"
            )

        if report.status not in {
            CertificationStatus.CERTIFIED,
            CertificationStatus.CONDITIONALLY_CERTIFIED,
        }:
            raise ValueError("Product is not certified for publication.")

        if report.product_id != product_id:
            raise ValueError("Certification report product mismatch.")

        if report.product_version != product_version:
            raise ValueError("Certification report version mismatch.")

        status = PublicationStatus.DRAFT

        if self.policy.require_human_first_publication and not approval_ref:
            status = PublicationStatus.PENDING_APPROVAL
        elif self.policy.allow_autonomous_publishing:
            status = PublicationStatus.APPROVED
        elif approval_ref:
            status = PublicationStatus.APPROVED
        else:
            status = PublicationStatus.PENDING_APPROVAL

        publication = PublicationRequest(
            product_id=product_id,
            product_version=product_version,
            marketplace_id=marketplace_id,
            publisher_id=publisher_id,
            pricing_plan_ref=pricing_plan_ref,
            certification_report_id=certification_report_id,
            status=status,
            approval_ref=approval_ref,
            guardrails=guardrails or PublicationGuardrails(),
        )

        self.publications[publication.id] = publication

        return publication

    def approve_publication(
        self,
        publication_id: str,
        approver_id: str,
        approval_ref: Optional[str] = None,
    ) -> PublicationRequest:
        publication = self._get_publication(publication_id)

        if publication.status != PublicationStatus.PENDING_APPROVAL:
            raise ValueError("Publication is not pending approval.")

        publication.status = PublicationStatus.APPROVED
        publication.approval_ref = approval_ref or f"approval:{approver_id}"
        publication.approved_at = utcnow()

        return publication

    def reject_publication(
        self,
        publication_id: str,
        approver_id: str,
        reason: str = "",
    ) -> PublicationRequest:
        publication = self._get_publication(publication_id)

        if publication.status != PublicationStatus.PENDING_APPROVAL:
            raise ValueError("Publication is not pending approval.")

        publication.status = PublicationStatus.REJECTED
        publication.delisting_reason = reason
        publication.approved_at = utcnow()

        return publication

    def publish(
        self,
        publication_id: str,
        approval_ref: Optional[str] = None,
    ) -> PublicationRequest:
        publication = self._get_publication(publication_id)

        if publication.status not in {
            PublicationStatus.APPROVED,
            PublicationStatus.STAGED,
        }:
            raise ValueError("Publication must be approved before publishing.")

        if approval_ref:
            publication.approval_ref = approval_ref

        if self.marketplace_engine:
            listing = self.marketplace_engine.publish_listing(
                listing_id=publication.marketplace_listing_id,
                approval_ref=publication.approval_ref,
            )

            publication.marketplace_listing_id = getattr(listing, "id", None)

        publication.status = PublicationStatus.PUBLISHED
        publication.published_at = utcnow()

        return publication

    def delist(
        self,
        publication_id: str,
        reason: str,
        actor_id: str,
    ) -> PublicationRequest:
        publication = self._get_publication(publication_id)

        publication.status = PublicationStatus.DELISTED
        publication.delisted_at = utcnow()
        publication.delisting_reason = reason

        if self.marketplace_engine and publication.marketplace_listing_id:
            self.marketplace_engine.delist_listing(
                listing_id=publication.marketplace_listing_id,
                reason=reason,
                actor_id=actor_id,
            )

        return publication

    def evaluate_guardrails(
        self,
        publication_id: str,
        metrics: Dict[str, float],
    ) -> PublicationRequest:
        publication = self._get_publication(publication_id)

        guardrails = publication.guardrails

        violations = []

        refund_rate = metrics.get("refund_rate", 0.0)

        if refund_rate > guardrails.max_refund_rate:
            violations.append("refund_rate_exceeded")

        fraud_score = metrics.get("fraud_score", 0.0)

        if fraud_score > guardrails.max_fraud_score:
            violations.append("fraud_score_exceeded")

        conversion_rate = metrics.get("conversion_rate", 0.0)

        if conversion_rate < guardrails.min_conversion_rate:
            violations.append("conversion_rate_below_minimum")

        if violations and guardrails.auto_delist_on_guardrail:
            publication.status = PublicationStatus.GUARDRAIL_TRIGGERED

            return self.delist(
                publication_id=publication.id,
                reason="Guardrail violation: " + ", ".join(violations),
                actor_id="guardrail_engine",
            )

        return publication

    def _get_publication(self, publication_id: str) -> PublicationRequest:
        publication = self.publications.get(publication_id)

        if not publication:
            raise KeyError(f"Publication request not found: {publication_id}")

        return publication
