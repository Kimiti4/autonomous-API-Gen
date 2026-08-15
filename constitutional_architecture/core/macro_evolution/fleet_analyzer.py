"""
Phase 20 — Fleet Telemetry Analyzer.

Identifies emergent architectural patterns across the global deployment
fleet: topologies that statistically outperform the CKB baseline are
candidates for new archetypes.

Safety gate: a topology must be observed across MIN_DEPLOYMENTS (10)
independent production systems before it can be considered emergent.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Dict, List

from constitutional_architecture.core.learning.empirical_fitness import (
    EmpiricalFitnessCalculator,
)
from constitutional_architecture.core.learning.telemetry_ingestor import (
    GenomeTelemetryProfile,
)
from constitutional_architecture.core.models.intent import QualityAttribute

MIN_DEPLOYMENTS = 10
BREAKTHROUGH_DEVIATION = 0.25


class FleetAnalyzer:
    """Analyzes cross-project telemetry to discover macro-evolutionary trends."""

    def __init__(self) -> None:
        self.fitness_calc = EmpiricalFitnessCalculator()

    def discover_emergent_patterns(
        self,
        fleet_profiles: List[GenomeTelemetryProfile],
        baseline_ckb_scores: Dict[str, Dict[QualityAttribute, float]],
    ) -> List[Dict]:
        """
        Group fleet data by architectural topology and identify combinations
        that significantly outperform CKB baselines.
        """
        topology_groups: Dict[str, List[GenomeTelemetryProfile]] = defaultdict(list)
        for profile in fleet_profiles:
            signature = profile.architecture_style
            topology_groups[signature].append(profile)

        emergent_patterns: List[Dict] = []

        for topology, profiles in topology_groups.items():
            if len(profiles) < MIN_DEPLOYMENTS:
                continue

            fleet_scores = self._aggregate_fleet_scores(profiles)
            baseline_scores = baseline_ckb_scores.get(topology, {})

            # Compare only the attributes the CKB baseline predicts for this
            # topology. An unknown topology (no baseline entry) is compared
            # across all empirical dimensions at the 0.5 neutral baseline,
            # which is how brand-new patterns get discovered.
            if baseline_scores:
                candidate_attrs = list(baseline_scores.keys())
            else:
                candidate_attrs = list(fleet_scores.keys())

            for attr in candidate_attrs:
                empirical_score = fleet_scores.get(attr, 0.5)
                baseline = baseline_scores.get(attr, 0.5)
                deviation = empirical_score - baseline
                if deviation > BREAKTHROUGH_DEVIATION:
                    emergent_patterns.append({
                        "topology_signature": topology,
                        "attribute": attr,
                        "empirical_score": round(empirical_score, 4),
                        "baseline_score": baseline,
                        "deviation": round(deviation, 4),
                        "sample_size": len(profiles),
                    })

        return emergent_patterns

    def _aggregate_fleet_scores(
        self, profiles: List[GenomeTelemetryProfile],
    ) -> Dict[QualityAttribute, float]:
        scores = [
            self.fitness_calc.calculate_real_world_fitness(p)
            for p in profiles
        ]
        avg_scores: Dict[QualityAttribute, float] = {}
        for attr in QualityAttribute:
            vals = [s.get(attr, 0.5) for s in scores]
            avg_scores[attr] = statistics.mean(vals)
        return avg_scores
