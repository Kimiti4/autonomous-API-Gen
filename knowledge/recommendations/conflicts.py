"""
Recommendation conflict detection.

This module detects explicit contradictions and opposing recommended actions.
"""

from __future__ import annotations

from ..ids import deterministic_id
from .models import ConflictRecord, RecommendationRecord
from .scoring import normalize_tokens


ACTION_ANTONYMS: list[tuple[str, str]] = [
    ("increase", "decrease"),
    ("enable", "disable"),
    ("add", "remove"),
    ("introduce", "retire"),
    ("migrate", "retain"),
    ("scale_up", "scale_down"),
    ("allow", "deny"),
    ("relax", "enforce"),
    ("open", "restrict"),
]


def find_conflicts(
    recommendations: list[RecommendationRecord],
) -> list[ConflictRecord]:
    """Find conflicts between recommendations."""

    conflicts: list[ConflictRecord] = []
    seen: set[tuple[str, tuple[str, str]]] = set()

    recommendation_by_id = {
        recommendation.id: recommendation
        for recommendation in recommendations
    }

    # Explicit contradictions.
    for recommendation in recommendations:
        for contradicted_id in recommendation.contradicts:
            if contradicted_id not in recommendation_by_id:
                continue

            pair = tuple(sorted((recommendation.id, contradicted_id)))
            key = ("EXPLICIT", pair)

            if key in seen:
                continue

            seen.add(key)

            conflict_id = deterministic_id(
                "conflict",
                {
                    "conflict_type": "EXPLICIT_CONTRADICTION",
                    "recommendation_ids": list(pair),
                },
            )

            conflicts.append(
                ConflictRecord(
                    conflict_id=conflict_id,
                    recommendation_ids=list(pair),
                    conflict_type="EXPLICIT_CONTRADICTION",
                    severity="HIGH",
                    reason="One recommendation explicitly contradicts another.",
                )
            )

    # Opposing actions targeting the same entity.
    for index, left in enumerate(recommendations):
        for right in recommendations[index + 1 :]:
            if not left.target_entity_id:
                continue

            if left.target_entity_id != right.target_entity_id:
                continue

            left_tokens = normalize_tokens(left.suggested_action)
            right_tokens = normalize_tokens(right.suggested_action)

            for positive, negative in ACTION_ANTONYMS:
                opposing = (
                    (positive in left_tokens and negative in right_tokens)
                    or (negative in left_tokens and positive in right_tokens)
                )

                if not opposing:
                    continue

                pair = tuple(sorted((left.id, right.id)))
                key = ("OPPOSING_ACTION", pair)

                if key in seen:
                    continue

                seen.add(key)

                conflict_id = deterministic_id(
                    "conflict",
                    {
                        "conflict_type": "OPPOSING_ACTION",
                        "recommendation_ids": list(pair),
                        "positive": positive,
                        "negative": negative,
                    },
                )

                conflicts.append(
                    ConflictRecord(
                        conflict_id=conflict_id,
                        recommendation_ids=list(pair),
                        conflict_type="OPPOSING_ACTION",
                        severity="MEDIUM",
                        reason=(
                            "Recommendations propose opposing actions "
                            f"({positive}/{negative}) for the same target."
                        ),
                    )
                )

    return conflicts
