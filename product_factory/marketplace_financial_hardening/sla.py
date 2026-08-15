"""
Marketplace SLA monitoring engine.

Tracks latency and rate-based SLAs over rolling windows and produces breach
alerts and operational health reports.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .models import (
    MarketplaceFinancialPolicy,
    SLAComparator,
    SLADefinition,
    SLAStatus,
    SLAStatusItem,
    SLAStatusOverall,
    SLAStatusReport,
    SLADomain,
    utcnow,
)


DEFAULT_SLA_DEFINITIONS: List[SLADefinition] = [
    SLADefinition(
        domain=SLADomain.PAYMENT_WEBHOOK_PROCESSING_LATENCY,
        target_value=500.0,
        comparator=SLAComparator.LESS_THAN_MS,
    ),
    SLADefinition(
        domain=SLADomain.PAYMENT_EVENT_INGESTION_SUCCESS_RATE,
        target_value=0.99,
        comparator=SLAComparator.GREATER_THAN_RATE,
    ),
    SLADefinition(
        domain=SLADomain.REFUND_PROCESSING_LATENCY,
        target_value=1000.0,
        comparator=SLAComparator.LESS_THAN_MS,
    ),
    SLADefinition(
        domain=SLADomain.RECONCILIATION_FRESHNESS,
        target_value=900.0,
        comparator=SLAComparator.LESS_THAN_MS,
    ),
    SLADefinition(
        domain=SLADomain.FRAUD_ASSESSMENT_LATENCY,
        target_value=200.0,
        comparator=SLAComparator.LESS_THAN_MS,
    ),
    SLADefinition(
        domain=SLADomain.TAX_CALCULATION_LATENCY,
        target_value=500.0,
        comparator=SLAComparator.LESS_THAN_MS,
    ),
    SLADefinition(
        domain=SLADomain.MARKETPLACE_API_AVAILABILITY,
        target_value=0.999,
        comparator=SLAComparator.GREATER_THAN_RATE,
    ),
    SLADefinition(
        domain=SLADomain.LISTING_PUBLICATION_LATENCY,
        target_value=3000.0,
        comparator=SLAComparator.LESS_THAN_MS,
    ),
]


class SLAMonitorEngine:
    """Tracks marketplace SLA observations and emits status reports."""

    def __init__(
        self,
        policy: Optional[MarketplaceFinancialPolicy] = None,
        marketplace_id: str = "marketplace_1",
        sla_definitions: Optional[List[SLADefinition]] = None,
    ) -> None:
        self.policy = policy or MarketplaceFinancialPolicy()
        self.marketplace_id = marketplace_id
        self.definitions: Dict[SLADomain, SLADefinition] = {
            d.domain: d for d in (sla_definitions or DEFAULT_SLA_DEFINITIONS)
        }

        self._observations: Dict[SLADomain, List[Dict]] = defaultdict(list)
        self._breach_counts: Dict[SLADomain, int] = {d: 0 for d in SLADomain}
        self._last_breach_at: Dict[SLADomain, Optional[datetime]] = {
            d: None for d in SLADomain
        }

    def record(
        self,
        domain: SLADomain,
        value: float,
        success: bool = True,
        recorded_at: Optional[datetime] = None,
    ) -> None:
        self._observations[domain].append(
            {
                "value": value,
                "success": success,
                "at": recorded_at or utcnow(),
            }
        )

    def _prune(self, domain: SLADomain, definition: SLADefinition) -> List[Dict]:
        window = timedelta(seconds=definition.window_seconds)

        now = utcnow()

        return [
            obs
            for obs in self._observations[domain]
            if now - obs["at"] <= window
        ]

    def _evaluate(self, domain: SLADomain, definition: SLADefinition) -> SLAStatus:
        recent = self._prune(domain, definition)

        comparator = definition.comparator

        if comparator == SLAComparator.LESS_THAN_MS:
            if not recent:
                return SLAStatus.WARNING

            latencies = [obs["value"] for obs in recent]
            latest = latencies[-1]

            if latest > definition.target_value:
                self._breach(domain)

                return SLAStatus.BREACH

            if latest > definition.target_value * definition.warning_threshold_pct:
                return SLAStatus.WARNING

            return SLAStatus.OK

        if not recent:
            return SLAStatus.WARNING

        successes = sum(1 for obs in recent if obs["success"])
        rate = successes / len(recent)

        if rate < definition.target_value:
            self._breach(domain)

            return SLAStatus.BREACH

        if rate < definition.target_value * definition.warning_threshold_pct:
            return SLAStatus.WARNING

        return SLAStatus.OK

    def _breach(self, domain: SLADomain) -> None:
        self._breach_counts[domain] += 1
        self._last_breach_at[domain] = utcnow()

    def get_sla_report(self) -> SLAStatusReport:
        items: List[SLAStatusItem] = []

        breaches: List[str] = []
        recommendations: List[str] = []
        overall = SLAStatusOverall.HEALTHY

        for domain, definition in self.definitions.items():
            recent = self._prune(domain, definition)

            if definition.comparator == SLAComparator.LESS_THAN_MS:
                current_value = (
                    recent[-1]["value"] if recent else definition.target_value
                )
            else:
                successes = sum(1 for obs in recent if obs["success"])
                current_value = successes / len(recent) if recent else definition.target_value

            status = self._evaluate(domain, definition)

            if status == SLAStatus.BREACH:
                breaches.append(f"SLA breach on {domain.value}")
                if overall.value == "HEALTHY":
                    overall = SLAStatusOverall.BREACH
                elif overall.value == "DEGRADED":
                    overall = SLAStatusOverall.BREACH
            elif status == SLAStatus.WARNING and overall.value == "HEALTHY":
                overall = SLAStatusOverall.DEGRADED

            items.append(
                SLAStatusItem(
                    domain=domain,
                    status=status,
                    current_value=round(current_value, 4),
                    target_value=definition.target_value,
                    breach_count=self._breach_counts[domain],
                    last_breach_at=self._last_breach_at[domain],
                )
            )

        if overall.value == SLAStatusOverall.BREACH:
            recommendations.append("Investigate SLA breaches and escalate if sustained.")

        if breaches:
            recommendations.append("Run governance review for repeated SLA breaches.")

        return SLAStatusReport(
            marketplace_id=self.marketplace_id,
            items=items,
            overall_status=overall,
            alerts=breaches,
            recommendations=recommendations,
        )

    def record_latency(
        self,
        domain: SLADomain,
        ms: float,
        success: bool = True,
    ) -> None:
        self.record(domain, ms, success=success)
