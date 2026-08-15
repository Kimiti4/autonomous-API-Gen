"""
Marketplace experiment lifecycle.
"""

from __future__ import annotations

from typing import Dict

from .models import (
    ExperimentStatus,
    MarketplaceAutonomyPolicy,
    MarketplaceExperiment,
)


class ExperimentManager:
    """Manages marketplace experiments and guardrails."""

    def __init__(self, policy: MarketplaceAutonomyPolicy) -> None:
        self.policy = policy
        self.experiments: Dict[str, MarketplaceExperiment] = {}

    def create_experiment(
        self,
        proposal_id: str,
        marketplace_id: str,
        name: str,
        variant_config: Dict,
        traffic_pct: float,
    ) -> MarketplaceExperiment:
        if traffic_pct > self.policy.max_experiment_traffic_pct:
            raise ValueError(
                f"Traffic percent {traffic_pct} exceeds maximum "
                f"{self.policy.max_experiment_traffic_pct}."
            )

        experiment = MarketplaceExperiment(
            proposal_id=proposal_id,
            marketplace_id=marketplace_id,
            name=name,
            variant_config=variant_config,
            traffic_pct=traffic_pct,
            status=ExperimentStatus.DRAFT,
        )

        self.experiments[experiment.id] = experiment

        return experiment

    def start_experiment(self, experiment_id: str) -> MarketplaceExperiment:
        experiment = self._get_experiment(experiment_id)

        if experiment.status != ExperimentStatus.DRAFT:
            raise ValueError("Experiment must be in DRAFT state to start.")

        from .models import utcnow

        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = utcnow()

        return experiment

    def conclude_experiment(
        self,
        experiment_id: str,
        observed_metrics: Dict[str, float],
        conclusion: str,
    ) -> MarketplaceExperiment:
        experiment = self._get_experiment(experiment_id)

        if experiment.status != ExperimentStatus.RUNNING:
            raise ValueError("Experiment must be RUNNING to conclude.")

        from .models import utcnow

        experiment.observed_metrics = observed_metrics
        experiment.conclusion = conclusion
        experiment.status = ExperimentStatus.CONCLUDED
        experiment.ended_at = utcnow()

        refund_rate = observed_metrics.get("refund_rate", 0.0)
        fraud_score = observed_metrics.get("fraud_score", 0.0)
        conversion_rate = observed_metrics.get("conversion_rate", 0.0)

        if refund_rate > experiment.guardrails.max_refund_rate:
            experiment.status = ExperimentStatus.GUARDRAIL_TRIGGERED
            experiment.conclusion = "Guardrail triggered: refund rate too high."

        if fraud_score > experiment.guardrails.max_fraud_score:
            experiment.status = ExperimentStatus.GUARDRAIL_TRIGGERED
            experiment.conclusion = "Guardrail triggered: fraud score too high."

        if conversion_rate < experiment.guardrails.min_conversion_rate:
            experiment.status = ExperimentStatus.GUARDRAIL_TRIGGERED
            experiment.conclusion = "Guardrail triggered: conversion too low."

        return experiment

    def _get_experiment(self, experiment_id: str) -> MarketplaceExperiment:
        experiment = self.experiments.get(experiment_id)

        if not experiment:
            raise KeyError(f"Experiment not found: {experiment_id}")

        return experiment
