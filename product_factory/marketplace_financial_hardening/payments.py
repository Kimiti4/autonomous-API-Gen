"""
Payment adapter framework and payment event engine.

Provider integrations are out of scope. Adapters implement normalize_event /
verify_signature and the engine enforces idempotency and webhook validation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .ledger import FinancialLedgerEngine
from .models import (
    FinancialAuditEvent,
    FinancialLedgerEntry,
    LedgerEntryType,
    MarketplaceFinancialPolicy,
    PaymentEvent,
    PaymentIntent,
    PaymentStatus,
    PaymentWebhookEnvelope,
)


class PaymentProviderAdapter:
    """Base contract for a payment provider adapter."""

    def normalize_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def verify_signature(self, envelope: PaymentWebhookEnvelope) -> bool:
        return True


class NoopPaymentAdapter(PaymentProviderAdapter):
    """Default no-op payment adapter used until a real provider is wired."""

    def normalize_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "provider": payload.get("provider", "unknown"),
            "provider_event_id": (
                payload.get("event_id")
                or payload.get("id")
                or payload.get("provider_event_id")
            ),
            "raw_status": payload.get("status", "CREATED"),
            "amount": float(payload.get("amount", 0.0)),
            "currency": payload.get("currency", "USD"),
            "order_id": payload.get("order_id", ""),
            "listing_id": payload.get("listing_id", ""),
            "tenant_id": payload.get("tenant_id", ""),
            "marketplace_id": payload.get("marketplace_id", ""),
            "intent_id": payload.get("intent_id"),
            "idempotency_key": payload.get("idempotency_key"),
        }

    def verify_signature(self, envelope: PaymentWebhookEnvelope) -> bool:
        return bool(envelope.signature)


class PaymentAdapterEngine:
    """Normalizes provider payment events with idempotency and audit."""

    def __init__(
        self,
        payment_adapter: Optional[PaymentProviderAdapter] = None,
        ledger: Optional[FinancialLedgerEngine] = None,
        policy: Optional[MarketplaceFinancialPolicy] = None,
    ) -> None:
        self.payment_adapter = payment_adapter or NoopPaymentAdapter()
        self.ledger = ledger
        self.policy = policy or MarketplaceFinancialPolicy()

        self._events_by_provider_event_id: Dict[str, PaymentEvent] = {}
        self._events_by_idempotency: Dict[str, PaymentEvent] = {}
        self.audit_events: List[FinancialAuditEvent] = []

    def create_payment_intent(
        self,
        marketplace_id: str,
        order_id: str,
        listing_id: str,
        tenant_id: str,
        amount: float,
        currency: str = "USD",
        provider: str = "",
        idempotency_key: Optional[str] = None,
        approval_ref: Optional[str] = None,
        governance_ref: Optional[str] = None,
    ) -> PaymentIntent:
        return PaymentIntent(
            marketplace_id=marketplace_id,
            order_id=order_id,
            listing_id=listing_id,
            tenant_id=tenant_id,
            amount=amount,
            currency=currency,
            provider=provider,
            idempotency_key=idempotency_key,
            approval_ref=approval_ref,
            governance_ref=governance_ref,
        )

    def map_status(self, raw_status: str) -> PaymentStatus:
        mapping = {
            "CREATED": PaymentStatus.CREATED,
            "INITIALIZED": PaymentStatus.CREATED,
            "AUTHORIZED": PaymentStatus.AUTHORIZED,
            "AUTHENTICATED": PaymentStatus.AUTHORIZED,
            "CAPTURED": PaymentStatus.CAPTURED,
            "PAID": PaymentStatus.CAPTURED,
            "SUCCEEDED": PaymentStatus.CAPTURED,
            "COMPLETED": PaymentStatus.CAPTURED,
            "FAILED": PaymentStatus.FAILED,
            "DECLINED": PaymentStatus.FAILED,
            "ERROR": PaymentStatus.FAILED,
            "REFUNDED": PaymentStatus.REFUNDED,
            "PARTIALLY_REFUNDED": PaymentStatus.PARTIALLY_REFUNDED,
            "CANCELLED": PaymentStatus.CANCELLED,
            "CANCELED": PaymentStatus.CANCELLED,
            "REQUIRES_ACTION": PaymentStatus.REQUIRES_ACTION,
            "REQUIRES_PAYMENT_METHOD": PaymentStatus.REQUIRES_ACTION,
        }

        return mapping.get(raw_status.upper(), PaymentStatus.REQUIRES_ACTION)

    def ingest_webhook(
        self,
        envelope: PaymentWebhookEnvelope,
    ) -> PaymentEvent:
        if (
            self.policy.payment_webhook_signature_required
            and not envelope.signature
        ):
            self._audit(
                action="webhook_rejected_unsigned",
                marketplace_id="",
                actor="provider_webhook",
                status="FAILED",
                reason="Missing webhook signature.",
            )

            raise ValueError(
                "Missing webhook signature; signature validation is required."
            )

        if not self.payment_adapter.verify_signature(envelope):
            self._audit(
                action="webhook_rejected_invalid_signature",
                marketplace_id="",
                actor="provider_webhook",
                status="FAILED",
                reason="Invalid webhook signature.",
            )

            raise ValueError("Invalid webhook signature; provider event rejected.")

        raw = self.payment_adapter.normalize_event(envelope.payload)

        provider_event_id = raw.get("provider_event_id")
        raw_status = raw.get("raw_status")

        if not provider_event_id or not raw_status:
            raise ValueError(
                "Invalid provider payment event: missing provider_event_id or status."
            )

        if (
            envelope.idempotency_key
            and envelope.idempotency_key in self._events_by_idempotency
        ):
            return self._events_by_idempotency[envelope.idempotency_key]

        if (
            provider_event_id
            and provider_event_id in self._events_by_provider_event_id
        ):
            return self._events_by_provider_event_id[provider_event_id]

        marketplace_id = raw.get("marketplace_id", "")

        event = PaymentEvent(
            marketplace_id=marketplace_id,
            order_id=raw.get("order_id", ""),
            listing_id=raw.get("listing_id", ""),
            tenant_id=raw.get("tenant_id", ""),
            provider=raw.get("provider", "unknown"),
            provider_event_id=provider_event_id,
            status=self.map_status(raw_status),
            amount=raw.get("amount", 0.0),
            currency=raw.get("currency", "USD"),
            idempotency_key=(
                envelope.idempotency_key or raw.get("idempotency_key")
            ),
            evidence_ref=(
                f"provider:{raw.get('provider', 'unknown')}"
                f":event:{provider_event_id}"
            ),
        )

        if raw.get("intent_id"):
            event.intent_id = raw["intent_id"]

        self._register(event)

        self._ledgerize_payment(event)

        self._audit(
            action="payment_event_processed",
            marketplace_id=marketplace_id,
            actor="provider_webhook",
            status="OK",
            amount=event.amount,
            currency=event.currency,
            idempotency_key=event.idempotency_key,
            source_event_id=event.event_id,
            evidence_ref=event.evidence_ref,
        )

        return event

    def get_payment_status(
        self,
        provider_event_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Optional[PaymentStatus]:
        event = None

        if provider_event_id and provider_event_id in self._events_by_provider_event_id:
            event = self._events_by_provider_event_id[provider_event_id]

        if not event and idempotency_key:
            event = self._events_by_idempotency.get(idempotency_key)

        return event.status if event else None

    def processed_events(self) -> List[PaymentEvent]:
        return list(self._events_by_provider_event_id.values())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _register(self, event: PaymentEvent) -> None:
        if event.idempotency_key:
            self._events_by_idempotency[event.idempotency_key] = event

        self._events_by_provider_event_id[event.provider_event_id] = event

    def _ledgerize_payment(self, event: PaymentEvent) -> None:
        if not self.ledger:
            return

        if event.status in (PaymentStatus.CAPTURED, PaymentStatus.AUTHORIZED):
            entry_type = LedgerEntryType.PAYMENT_CAPTURED
        elif event.status in (PaymentStatus.FAILED, PaymentStatus.CANCELLED):
            entry_type = LedgerEntryType.PAYMENT_FAILED
        else:
            return

        self.ledger.append(
            FinancialLedgerEntry(
                marketplace_id=event.marketplace_id,
                order_id=event.order_id,
                listing_id=event.listing_id,
                tenant_id=event.tenant_id,
                entry_type=entry_type,
                amount=event.amount,
                currency=event.currency,
                status=event.status.value,
                idempotency_key=event.idempotency_key or event.event_id,
                source_event_id=event.event_id,
                evidence_ref=event.evidence_ref,
            )
        )

    def _audit(
        self,
        action: str,
        marketplace_id: str,
        actor: str = "system",
        status: str = "OK",
        amount: Optional[float] = None,
        currency: Optional[str] = "USD",
        idempotency_key: Optional[str] = None,
        source_event_id: Optional[str] = None,
        governance_ref: Optional[str] = None,
        evidence_ref: Optional[str] = None,
        reason: str = "",
    ) -> FinancialAuditEvent:
        event = FinancialAuditEvent(
            marketplace_id=marketplace_id,
            action=action,
            actor=actor,
            status=status,
            amount=amount,
            currency=currency,
            idempotency_key=idempotency_key,
            source_event_id=source_event_id,
            governance_ref=governance_ref,
            evidence_ref=evidence_ref,
            reason=reason,
        )

        if self.ledger:
            self.ledger.record_audit(event)
        else:
            self.audit_events.append(event)

        return event
