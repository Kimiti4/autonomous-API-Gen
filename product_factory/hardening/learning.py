"""
Phase 24.4 — Customer Learning Loop and Product Evolution.
"""

from __future__ import annotations

from typing import Dict, List

from ..utils import deterministic_id, utcnow
from .models import (
    CustomerSignal,
    ProductFitnessReport,
    ProductImprovementRecommendation,
)


def clamp(value: float) -> float:
    return round(min(1.0, max(0.0, value)), 4)


class CustomerLearningEngine:
    """Converts customer signals into product fitness and improvement hints."""

    def __init__(self) -> None:
        self.signals: List[CustomerSignal] = []

    def ingest(self, signals: List[CustomerSignal]) -> int:
        self.signals.extend(signals)
        return len(signals)

    def product_fitness(self, product_id: str) -> ProductFitnessReport:
        product_signals = [
            signal
            for signal in self.signals
            if signal.product_id == product_id
        ]

        signups = sum(
            1 for signal in product_signals if signal.event_type == "signup"
        )

        activations = sum(
            1 for signal in product_signals if signal.event_type == "activated"
        )

        churns = sum(
            1 for signal in product_signals if signal.event_type == "churned"
        )

        successful_payments = sum(
            1
            for signal in product_signals
            if signal.event_type == "payment_succeeded"
        )

        failed_payments = sum(
            1
            for signal in product_signals
            if signal.event_type == "payment_failed"
        )

        incidents = sum(
            1 for signal in product_signals if signal.event_type == "incident"
        )

        latency_alerts = sum(
            1
            for signal in product_signals
            if signal.event_type == "latency_alert"
        )

        support_tickets = sum(
            1
            for signal in product_signals
            if signal.event_type == "support_ticket"
        )

        activation_rate = (
            activations / signups
            if signups > 0
            else 0.0
        )

        retention_rate = (
            clamp(1.0 - (churns / activations))
            if activations > 0
            else 0.5
        )

        payment_events = successful_payments + failed_payments

        revenue_health = (
            successful_payments / payment_events
            if payment_events > 0
            else 0.5
        )

        total_signals = max(1, len(product_signals))

        reliability_health = clamp(1.0 - (incidents / total_signals))

        performance_health = clamp(1.0 - (latency_alerts / total_signals))

        support_health = clamp(
            1.0 - (support_tickets / max(1, signups))
        )

        objectives = {
            "activation": round(activation_rate, 4),
            "retention": round(retention_rate, 4),
            "revenue_health": round(revenue_health, 4),
            "reliability": round(reliability_health, 4),
            "performance": round(performance_health, 4),
            "support_health": round(support_health, 4),
        }

        constraints = {
            "sufficient_customer_data": signups > 0,
            "sufficient_payment_data": payment_events > 0,
        }

        recommendations: List[ProductImprovementRecommendation] = []

        def add_recommendation(
            capability: str,
            action: str,
            rationale: str,
            priority: str,
        ) -> None:
            recommendations.append(
                ProductImprovementRecommendation(
                    id=deterministic_id(
                        "product_improvement_recommendation",
                        {
                            "product_id": product_id,
                            "capability": capability,
                            "action": action,
                        },
                    ),
                    product_id=product_id,
                    capability=capability,
                    action=action,
                    rationale=rationale,
                    priority=priority,
                )
            )

        if activation_rate < 0.30:
            add_recommendation(
                capability="onboarding",
                action="IMPROVE_ONBOARDING",
                rationale="Activation rate is below target.",
                priority="HIGH",
            )

        if retention_rate < 0.70:
            add_recommendation(
                capability="retention",
                action="IMPROVE_RETENTION",
                rationale="Retention rate is below target.",
                priority="HIGH",
            )

        if revenue_health < 0.80:
            add_recommendation(
                capability="billing",
                action="IMPROVE_BILLING_RELIABILITY",
                rationale="Payment health is below target.",
                priority="HIGH",
            )

        if reliability_health < 0.90:
            add_recommendation(
                capability="reliability",
                action="IMPROVE_RELIABILITY",
                rationale="Incident rate is affecting reliability.",
                priority="HIGH",
            )

        if performance_health < 0.80:
            add_recommendation(
                capability="performance",
                action="IMPROVE_PERFORMANCE",
                rationale="Latency alerts are affecting performance.",
                priority="MEDIUM",
            )

        if support_health < 0.75:
            add_recommendation(
                capability="support_experience",
                action="IMPROVE_SUPPORT_EXPERIENCE",
                rationale="Support ticket volume is high relative to adoption.",
                priority="MEDIUM",
            )

        return ProductFitnessReport(
            product_id=product_id,
            objectives=objectives,
            constraints=constraints,
            recommendations=recommendations,
            created_at=utcnow().isoformat(),
        )

    def evolution_feedback(self, product_id: str) -> Dict:
        report = self.product_fitness(product_id)

        genome_hints: List[Dict[str, str]] = []

        objective_to_chromosome = {
            "activation": "Frontend",
            "retention": "Architecture",
            "revenue_health": "Backend",
            "reliability": "Reliability",
            "performance": "Performance",
            "support_health": "Documentation",
        }

        for objective, value in report.objectives.items():
            if value < 0.70:
                chromosome = objective_to_chromosome.get(
                    objective,
                    "Architecture",
                )

                genome_hints.append(
                    {
                        "objective": objective,
                        "chromosome_family": chromosome,
                        "action": "STRENGTHEN",
                        "rationale": (
                            f"Objective {objective} is below target: {value}."
                        ),
                    }
                )

        return {
            "product_id": product_id,
            "generated_at": utcnow().isoformat(),
            "genome_hints": genome_hints,
            "recommendations": report.recommendations,
        }
