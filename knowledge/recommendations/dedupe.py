"""
Duplicate recommendation detection.

This module uses deterministic text similarity to identify likely duplicate
recommendations.
"""

from __future__ import annotations

from itertools import combinations

from ..ids import deterministic_id
from .models import DuplicateCluster, RecommendationRecord
from .scoring import normalize_tokens


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    """Compute Jaccard similarity between two token sets."""

    if not left and not right:
        return 0.0

    intersection = len(left.intersection(right))
    union = len(left.union(right))

    if union == 0:
        return 0.0

    return intersection / union


class DisjointSet:
    """Minimal disjoint-set structure for clustering."""

    def __init__(self, items: list[str]) -> None:
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)

        if left_root != right_root:
            self.parent[right_root] = left_root


def find_duplicate_clusters(
    recommendations: list[RecommendationRecord],
    threshold: float,
) -> list[DuplicateCluster]:
    """Find likely duplicate recommendation clusters."""

    if len(recommendations) < 2:
        return []

    dsu = DisjointSet([recommendation.id for recommendation in recommendations])
    pair_similarity: dict[tuple[str, str], float] = {}

    for index, recommendation in enumerate(recommendations):
        left_text = f"{recommendation.title} {recommendation.description}"
        left_tokens = normalize_tokens(left_text)

        for other in recommendations[index + 1 :]:
            right_text = f"{other.title} {other.description}"
            right_tokens = normalize_tokens(right_text)

            similarity = jaccard_similarity(left_tokens, right_tokens)

            if similarity >= threshold:
                dsu.union(recommendation.id, other.id)

                pair_key = tuple(sorted((recommendation.id, other.id)))
                pair_similarity[pair_key] = max(
                    pair_similarity.get(pair_key, 0.0),
                    similarity,
                )

    clusters: dict[str, list[str]] = {}

    for recommendation in recommendations:
        root = dsu.find(recommendation.id)
        clusters.setdefault(root, []).append(recommendation.id)

    duplicate_clusters: list[DuplicateCluster] = []

    for member_ids in clusters.values():
        if len(member_ids) < 2:
            continue

        sorted_ids = sorted(member_ids)

        similarities = [
            pair_similarity.get(tuple(sorted(pair)), threshold)
            for pair in combinations(sorted_ids, 2)
        ]

        similarity = max(similarities) if similarities else threshold

        cluster_id = deterministic_id(
            "duplicate_cluster",
            {
                "recommendation_ids": sorted_ids,
            },
        )

        duplicate_clusters.append(
            DuplicateCluster(
                cluster_id=cluster_id,
                recommendation_ids=sorted_ids,
                similarity=similarity,
                reason="Text similarity exceeded duplicate threshold.",
            )
        )

    return duplicate_clusters
