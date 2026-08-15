"""
Population diversity measurement and selection.

This module extracts architectural features from ISR payloads and uses them
to preserve population diversity.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set

from .recombination import ARCHITECTURAL_BLOCKS


def _api_name(api) -> str:
    if isinstance(api, str):
        return api

    if isinstance(api, dict):
        return str(api.get("name", ""))

    return ""


def extract_isr_features(isr: Dict) -> Set[str]:
    """Extract stable architectural features from an ISR payload."""

    features: Set[str] = set()

    for block in ARCHITECTURAL_BLOCKS:
        if block in isr:
            features.add(f"block:{block}")

    domains = isr.get("domains", []) or []

    for domain in domains:
        if isinstance(domain, str):
            features.add(f"domain:{domain}")
            continue

        if not isinstance(domain, dict):
            continue

        domain_name = str(domain.get("name", ""))

        if domain_name:
            features.add(f"domain:{domain_name}")

        services = domain.get("services", []) or []

        for service in services:
            if isinstance(service, str):
                features.add(f"service:{service}")
                continue

            if not isinstance(service, dict):
                continue

            service_name = str(service.get("name", ""))

            if service_name:
                features.add(f"service:{service_name}")

            apis = service.get("apis", []) or []

            for api in apis:
                api_name = _api_name(api)

                if api_name:
                    features.add(f"api:{service_name}:{api_name}")

    top_level_services = isr.get("services", []) or []

    for service in top_level_services:
        if isinstance(service, str):
            features.add(f"service:{service}")
            continue

        if not isinstance(service, dict):
            continue

        service_name = str(service.get("name", ""))

        if service_name:
            features.add(f"service:{service_name}")

        apis = service.get("apis", []) or []

        for api in apis:
            api_name = _api_name(api)

            if api_name:
                features.add(f"api:{service_name}:{api_name}")

    return features


def jaccard_similarity(left: Set[str], right: Set[str]) -> float:
    """Compute Jaccard similarity between two feature sets."""

    if not left and not right:
        return 1.0

    union = left.union(right)

    if not union:
        return 1.0

    intersection = left.intersection(right)

    return len(intersection) / len(union)


class PopulationDiversityController:
    """Preserves diversity across candidate populations."""

    def __init__(self) -> None:
        self._features: Dict[str, Set[str]] = {}

    def register_candidate(
        self,
        candidate_id: str,
        isr: Dict,
    ) -> None:
        self._features[candidate_id] = extract_isr_features(isr)

    def register_offspring(self, offspring) -> None:
        self.register_candidate(offspring.id, offspring.isr)

    def similarity(self, candidate_a_id: str, candidate_b_id: str) -> float:
        left = self._features.get(candidate_a_id)
        right = self._features.get(candidate_b_id)

        if left is None or right is None:
            return 0.0

        return jaccard_similarity(left, right)

    def diversity_report(
        self,
        candidate_ids: Iterable[str],
    ) -> Dict[str, float]:
        candidate_list = list(candidate_ids)

        if len(candidate_list) < 2:
            return {
                "candidate_count": float(len(candidate_list)),
                "average_pairwise_similarity": 0.0,
            }

        total_similarity = 0.0
        pair_count = 0

        for index, candidate_id in enumerate(candidate_list):
            for other_id in candidate_list[index + 1:]:
                total_similarity += self.similarity(candidate_id, other_id)
                pair_count += 1

        average_similarity = (
            total_similarity / pair_count
            if pair_count
            else 0.0
        )

        return {
            "candidate_count": float(len(candidate_list)),
            "average_pairwise_similarity": average_similarity,
        }

    def select_diverse(
        self,
        candidate_ids: Iterable[str],
        max_select: int,
        existing_ids: Optional[Iterable[str]] = None,
    ) -> List[str]:
        remaining = set(candidate_ids)

        selected: List[str] = []

        reference_ids: List[str] = list(existing_ids or [])

        while remaining and len(selected) < max_select:
            best_id: Optional[str] = None
            best_score = -1.0

            for candidate_id in sorted(remaining):
                if not reference_ids:
                    min_distance = 1.0
                else:
                    min_distance = 1.0

                    for reference_id in reference_ids:
                        similarity = self.similarity(
                            candidate_id,
                            reference_id,
                        )

                        distance = 1.0 - similarity

                        if distance < min_distance:
                            min_distance = distance

                if (
                    min_distance > best_score
                    or (
                        min_distance == best_score
                        and (best_id is None or candidate_id < best_id)
                    )
                ):
                    best_score = min_distance
                    best_id = candidate_id

            if best_id is None:
                break

            selected.append(best_id)
            remaining.remove(best_id)
            reference_ids.append(best_id)

        return selected
