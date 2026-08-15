"""
Observation Classification Engine.

Classifies every observation into:
- ARCHITECTURAL_DEFICIENCY -> evolution engine (fitness penalty)
- IMPLEMENTATION_BUG -> compiler backend
- OPERATIONAL_MISCONFIGURATION -> deployment engine
- REQUIREMENT_GAP -> IRR revision
- EXTERNAL_FACTOR -> contextual annotation
- UNKNOWN -> needs further analysis
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from constitutional_architecture.operations.observation_model import (
    Observation,
    ObservationClassification,
    ObservationSeverity,
    ObservationSource,
)


@dataclass(frozen=True)
class ClassificationResult:
    classification: ObservationClassification
    confidence: float = 0.0
    reasoning: str = ""
    signals: tuple[str, ...] = ()


class ObservationClassifier:

    ARCHITECTURAL_PATTERNS = [
        re.compile(r"(?i)high\s+coupling"),
        re.compile(r"(?i)low\s+cohesion"),
        re.compile(r"(?i)dependency\s+cycle"),
        re.compile(r"(?i)bottleneck\s+at\s+service"),
        re.compile(r"(?i)single\s+point\s+of\s+failure"),
        re.compile(r"(?i)tight\s+coupling"),
        re.compile(r"(?i)monolith"),
        re.compile(r"(?i)scalability\s+limit"),
        re.compile(r"(?i)stateful\s+service"),
    ]

    IMPLEMENTATION_PATTERNS = [
        re.compile(r"(?i)null\s*pointer"),
        re.compile(r"(?i)segmentation\s+fault"),
        re.compile(r"(?i)syntax\s+error"),
        re.compile(r"(?i)type\s+error"),
        re.compile(r"(?i)import\s+error"),
        re.compile(r"(?i)undefined\s+(variable|function|method)"),
        re.compile(r"(?i)stack\s+overflow"),
        re.compile(r"(?i)compilation\s+(error|failed)"),
    ]

    OPERATIONAL_PATTERNS = [
        re.compile(r"(?i)connection\s+refused"),
        re.compile(r"(?i)timeout\s+(exceeded|waiting)"),
        re.compile(r"(?i)dns\s+(resolution\s+)?fail"),
        re.compile(r"(?i)certificate\s+(expired|invalid)"),
        re.compile(r"(?i)permission\s+denied"),
        re.compile(r"(?i)out\s+of\s+memory"),
        re.compile(r"(?i)disk\s+space"),
        re.compile(r"(?i)port\s+(already\s+)?in\s+use"),
    ]

    REQUIREMENT_PATTERNS = [
        re.compile(r"(?i)missing\s+(feature|requirement|capability)"),
        re.compile(r"(?i)user\s+(request|need|expectation)"),
        re.compile(r"(?i)not\s+(supported|implemented)"),
        re.compile(r"(?i)feature\s+request"),
        re.compile(r"(?i)gap\s+in\s+(functionality|coverage)"),
    ]

    def classify(self, observation: Observation) -> ClassificationResult:
        text = f"{observation.title} {observation.description}".lower()
        signals: list[str] = []

        arch_score = self._match_patterns(text, self.ARCHITECTURAL_PATTERNS, signals, "arch")
        impl_score = self._match_patterns(text, self.IMPLEMENTATION_PATTERNS, signals, "impl")
        ops_score = self._match_patterns(text, self.OPERATIONAL_PATTERNS, signals, "ops")
        req_score = self._match_patterns(text, self.REQUIREMENT_PATTERNS, signals, "req")

        if observation.source == ObservationSource.HEALTH_CHECKS:
            ops_score += 0.2
            signals.append("health_check_source")
        elif observation.source == ObservationSource.METRICS:
            arch_score += 0.1
            signals.append("metrics_source")

        if observation.severity == ObservationSeverity.CRITICAL:
            arch_score += 0.1
            ops_score += 0.1

        scores = {
            ObservationClassification.ARCHITECTURAL_DEFICIENCY: arch_score,
            ObservationClassification.IMPLEMENTATION_BUG: impl_score,
            ObservationClassification.OPERATIONAL_MISCONFIGURATION: ops_score,
            ObservationClassification.REQUIREMENT_GAP: req_score,
        }

        best = max(scores, key=scores.get)
        best_score = scores[best]

        if self._is_external_factor(observation):
            return ClassificationResult(
                classification=ObservationClassification.EXTERNAL_FACTOR,
                confidence=0.8,
                reasoning="External factor detected (network, third-party, environment)",
                signals=tuple(signals + ["external_factor"]),
            )

        if best_score < 0.3:
            return ClassificationResult(
                classification=ObservationClassification.UNKNOWN,
                confidence=best_score,
                reasoning="No strong pattern match; requires manual analysis",
                signals=tuple(signals),
            )

        return ClassificationResult(
            classification=best,
            confidence=min(best_score, 1.0),
            reasoning=f"Best match: {best.value} (score={best_score:.2f})",
            signals=tuple(signals),
        )

    def _match_patterns(
        self,
        text: str,
        patterns: list[re.Pattern],
        signals: list[str],
        category: str,
    ) -> float:
        matches = 0
        for pattern in patterns:
            if pattern.search(text):
                matches += 1
                signals.append(f"{category}:{pattern.pattern}")
        return min(matches / max(len(patterns) * 0.3, 1), 1.0)

    def _is_external_factor(self, observation: Observation) -> bool:
        text = f"{observation.title} {observation.description}".lower()
        external_indicators = [
            "network outage", "third-party", "provider down",
            "internet", "isp", "cloud provider", "aws", "gcp", "azure",
            "ddos", "natural disaster", "power outage",
        ]
        return any(indicator in text for indicator in external_indicators)
