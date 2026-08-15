"""
Tests for Phase 24.10 Marketplace Financial Reconciliation and Settlement Hardening.
"""

from datetime import timedelta

import pytest

from product_factory.marketplace_settlement.engine import MarketplaceSettlementEngine
from product_factory.marketplace_settlement.gateway import (
    StaticGovernanceGateway,
    StaticSettlementAdapter,
)
from product_factory.marketplace_settlement.models import (
    FinancialEvent,
    FinancialEventType,
    SettlementPolicy,
)
from product_factory.marketplace_settlement.models import utcnow


def build_engine(governance_decision: str = "ALLOW") -> MarketplaceSettlementEngine:
    policy = SettlementPolicy(
        require_governance_for_settlement=True,
        allow_negative_settlement=False,
        allow_negative_balances=False,
    )

    return MarketplaceSettlementEngine(
        governance_gateway=StaticGovernanceGateway(decision=governance_decision),
        settlement_adapter=StaticSettlementAdapter(),
        policy=policy,
    )


def financial_event(
    event_type: FinancialEventType,
    amount: float,
    idempotency_key: str,
) -> FinancialEvent:
    return FinancialEvent(
        idempotency_key=idempotency_key,
        event_type=event_type,
        marketplace_id="marketplace_1",
        tenant_id="tenant_1",
        order_id="order_1",
        amount=amount,
        currency="USD",
    )


def test_idempotent_ledger_ingestion():
    engine = build_engine()

    event = financial_event(
        event_type=FinancialEventType.PAYMENT_CAPTURED,
        amount=100.0,
        idempotency_key="pay_1",
    )

    first = engine.ledger.ingest_event(event)
    second = engine.ledger.ingest_event(event)

    assert first is not None
    assert second is None

    balance = engine.ledger.balance(
        marketplace_id="marketplace_1",
        tenant_id="tenant_1",
        currency="USD",
    )

    assert balance == 100.0


def test_reconciliation_detects_negative_balance():
    engine = build_engine()

    engine.ledger.ingest_event(
        financial_event(
            event_type=FinancialEventType.PAYMENT_CAPTURED,
            amount=100.0,
            idempotency_key="pay_1",
        )
    )

    engine.ledger.ingest_event(
        financial_event(
            event_type=FinancialEventType.REFUND_ISSUED,
            amount=150.0,
            idempotency_key="refund_1",
        )
    )

    now = utcnow()

    report = engine.reconciliation.run(
        marketplace_id="marketplace_1",
        period_start=now - timedelta(hours=1),
        period_end=now + timedelta(hours=1),
    )

    assert report.status.value == "FAIL"

    mismatch_types = {
        mismatch.mismatch_type
        for mismatch in report.mismatches
    }

    assert "NEGATIVE_BALANCE" in mismatch_types


def test_settlement_batch_lifecycle():
    engine = build_engine("ALLOW")

    engine.ledger.ingest_event(
        financial_event(
            event_type=FinancialEventType.PAYMENT_CAPTURED,
            amount=100.0,
            idempotency_key="pay_1",
        )
    )

    engine.ledger.ingest_event(
        financial_event(
            event_type=FinancialEventType.FEE_CHARGED,
            amount=10.0,
            idempotency_key="fee_1",
        )
    )

    engine.ledger.ingest_event(
        financial_event(
            event_type=FinancialEventType.REFUND_ISSUED,
            amount=20.0,
            idempotency_key="refund_1",
        )
    )

    now = utcnow()

    reconciliation_report = engine.reconciliation.run(
        marketplace_id="marketplace_1",
        period_start=now - timedelta(hours=1),
        period_end=now + timedelta(hours=1),
    )

    assert reconciliation_report.status.value == "OK"

    batch = engine.settlement.create_batch(
        marketplace_id="marketplace_1",
        tenant_id="tenant_1",
        currency="USD",
        period_start=now - timedelta(hours=1),
        period_end=now + timedelta(hours=1),
        actor_id="finance_operator",
    )

    assert batch.net_amount == 70.0
    assert batch.status.value == "DRAFT"

    approved = engine.settlement.approve_settlement(
        batch_id=batch.id,
        actor_id="governance_admin",
    )

    assert approved.status.value == "APPROVED"

    settled = engine.settlement.execute_settlement(
        batch_id=batch.id,
        actor_id="settlement_operator",
    )

    assert settled.status.value == "SETTLED"

    balance = engine.ledger.balance(
        marketplace_id="marketplace_1",
        tenant_id="tenant_1",
        currency="USD",
    )

    assert balance == 0.0


def test_settlement_requires_governance():
    engine = build_engine("DENY")

    engine.ledger.ingest_event(
        financial_event(
            event_type=FinancialEventType.PAYMENT_CAPTURED,
            amount=100.0,
            idempotency_key="pay_1",
        )
    )

    now = utcnow()

    batch = engine.settlement.create_batch(
        marketplace_id="marketplace_1",
        tenant_id="tenant_1",
        currency="USD",
        period_start=now - timedelta(hours=1),
        period_end=now + timedelta(hours=1),
        actor_id="finance_operator",
    )

    with pytest.raises(PermissionError):
        engine.settlement.approve_settlement(
            batch_id=batch.id,
            actor_id="governance_admin",
        )
