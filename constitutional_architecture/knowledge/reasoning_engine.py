"""
Reasoning Engine — Pattern matching, inference, and knowledge discovery.

Combines information from all repositories to derive insights,
detect patterns, and generate recommendations.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from constitutional_architecture.knowledge.anti_pattern_repository import (
    AntiPatternEntry,
    AntiPatternRepository,
)
from constitutional_architecture.knowledge.compatibility_repository import (
    CompatibilityRepository,
)
from constitutional_architecture.knowledge.fitness_repository import (
    FitnessRepository,
)
from constitutional_architecture.knowledge.knowledge_types import (
    ConfidenceLevel,
    DomainFact,
    EvolutionLesson,
    HeuristicRule,
)
from constitutional_architecture.knowledge.mutation_repository import (
    MutationRepository,
)
from constitutional_architecture.knowledge.pattern_repository import PatternEntry, PatternRepository


class ReasoningResult:

    def __init__(
        self,
        description: str,
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
        supporting_evidence: Optional[list[str]] = None,
        suggested_actions: Optional[list[str]] = None,
        related_patterns: Optional[list[str]] = None,
    ) -> None:
        self.description = description
        self.confidence = confidence
        self.supporting_evidence = supporting_evidence or []
        self.suggested_actions = suggested_actions or []
        self.related_patterns = related_patterns or []


class ReasoningEngine:

    def __init__(
        self,
        pattern_repo: Optional[PatternRepository] = None,
        anti_pattern_repo: Optional[AntiPatternRepository] = None,
        mutation_repo: Optional[MutationRepository] = None,
        fitness_repo: Optional[FitnessRepository] = None,
        compatibility_repo: Optional[CompatibilityRepository] = None,
    ) -> None:
        self._patterns = pattern_repo or PatternRepository()
        self._anti_patterns = anti_pattern_repo or AntiPatternRepository()
        self._mutations = mutation_repo or MutationRepository()
        self._fitness = fitness_repo or FitnessRepository()
        self._compatibility = compatibility_repo or CompatibilityRepository()
        self._heuristics: list[HeuristicRule] = []
        self._domain_facts: list[DomainFact] = []
        self._lessons: list[EvolutionLesson] = []

    def register_heuristic(self, rule: HeuristicRule) -> None:
        self._heuristics.append(rule)

    def register_domain_fact(self, fact: DomainFact) -> None:
        self._domain_facts.append(fact)

    def register_lesson(self, lesson: EvolutionLesson) -> None:
        self._lessons.append(lesson)

    def infer_best_pattern(
        self,
        context: str,
        constraints: Optional[list[str]] = None,
    ) -> list[ReasoningResult]:
        results: list[ReasoningResult] = []

        context_lower = context.lower()

        pattern_matches = self._patterns.query(text=context)
        for pat in pattern_matches:
            evidence = []
            actions = []
            if pat.evidence_count > 0:
                evidence.append(f"Pattern '{pat.name}' has {pat.evidence_count} evidence records")

            # Check compatibility with existing patterns mentioned in constraints
            if constraints:
                compatible: list[str] = []
                conflicting: list[str] = []
                for constraint in constraints:
                    existing = self._patterns.get_by_name(constraint)
                    if existing and existing.pattern_id:
                        compat = self._compatibility.get_compatibility(
                            pat.name, constraint
                        )
                        if compat is not None:
                            if compat >= 0.6:
                                compatible.append(constraint)
                            else:
                                conflicting.append(constraint)
                if compatible:
                    evidence.append(f"Compatible with: {', '.join(compatible)}")
                if conflicting:
                    evidence.append(f"May conflict with: {', '.join(conflicting)}")

            # Fitness impact prediction
            prediction = self._fitness.predict(pat.name, context)
            if prediction.sample_size > 0:
                dims = ", ".join(
                    f"{k}={v:+.2f}" for k, v in prediction.expected_delta.items()
                )
                evidence.append(f"Expected fitness impact: {dims}")

            if pat.prerequisites:
                actions.append(f"Prerequisites: {', '.join(pat.prerequisites)}")
            if pat.contra_indicators:
                evidence.append(f"Contra-indicators: {', '.join(pat.contra_indicators)}")

            confidence = (
                ConfidenceLevel.HIGH if pat.evidence_count >= 10
                else ConfidenceLevel.MEDIUM if pat.evidence_count >= 3
                else ConfidenceLevel.LOW
            )

            results.append(ReasoningResult(
                description=f"Pattern '{pat.name}': {pat.description[:120]}",
                confidence=confidence,
                supporting_evidence=evidence,
                suggested_actions=actions,
                related_patterns=[pat.name],
            ))

        return results

    def detect_anti_patterns(
        self, context: str, tags: Optional[list[str]] = None
    ) -> list[ReasoningResult]:
        results: list[ReasoningResult] = []
        matches = self._anti_patterns.detect(context, tags)

        for ap in matches:
            evidence = []
            if ap.symptoms:
                evidence.append(f"Symptoms: {', '.join(ap.symptoms[:3])}")
            if ap.consequences:
                evidence.append(f"Consequences: {', '.join(ap.consequences[:2])}")

            level = (
                ConfidenceLevel.HIGH if ap.severity == "critical"
                else ConfidenceLevel.MEDIUM if ap.severity == "warning"
                else ConfidenceLevel.LOW
            )

            results.append(ReasoningResult(
                description=f"Anti-pattern detected: '{ap.name}' — {ap.description[:120]}",
                confidence=level,
                supporting_evidence=evidence,
                suggested_actions=list(ap.recommended_fixes),
                related_patterns=[ap.name],
            ))

        return results

    def suggest_mutation_strategy(
        self,
        operator_name: str,
        context: str = "",
    ) -> Optional[ReasoningResult]:
        success_rate = self._mutations.get_operator_success_rate(operator_name)
        prediction = self._fitness.predict(operator_name, context)

        evidence = [
            f"Historical success rate: {success_rate:.0%}",
        ]
        if prediction.sample_size > 0:
            dims = ", ".join(
                f"{k}={v:+.2f}" for k, v in prediction.expected_delta.items()
            )
            evidence.append(f"Predicted fitness impact: {dims}")
            evidence.append(f"Based on {prediction.sample_size} prior applications")

        if prediction.confidence < 0.3:
            confidence = ConfidenceLevel.LOW
        elif prediction.confidence < 0.7:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.HIGH

        return ReasoningResult(
            description=f"Mutation strategy for '{operator_name}'",
            confidence=confidence,
            supporting_evidence=evidence,
            suggested_actions=[f"Apply '{operator_name}' mutation"],
        )

    @property
    def heuristics(self) -> list[HeuristicRule]:
        return list(self._heuristics)

    @property
    def domain_facts(self) -> list[DomainFact]:
        return list(self._domain_facts)

    @property
    def lessons(self) -> list[EvolutionLesson]:
        return list(self._lessons)
