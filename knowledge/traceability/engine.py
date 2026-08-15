"""
Advanced traceability and impact engine.

This engine provides read-only impact analysis and path explanation over
the Knowledge Graph.

It does not mutate the graph.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Optional

from ..auth import Actor
from ..errors import NotFound
from ..ids import deterministic_id
from ..models import QueryRequest, utcnow
from .models import (
    ImpactEntry,
    ImpactMetadata,
    ImpactRequest,
    ImpactResult,
    PathExplanation,
    PathExplanationMetadata,
    PathExplanationRequest,
    PathExplanationResult,
    RelationHop,
)
from .weights import (
    PropagationDirection,
    get_impact_profile,
)


SENSITIVE_LEVELS = {"CONFIDENTIAL", "RESTRICTED"}
SENSITIVE_VIEWER_ROLES = {"knowledge_auditor", "knowledge_admin"}


class TraceabilityEngine:
    """Read-only traceability and impact engine."""

    def __init__(
        self,
        runtime,
        profiles: Optional[dict] = None,
    ) -> None:
        self._runtime = runtime
        self._profiles = profiles

    # ------------------------------------------------------------------
    # Impact analysis
    # ------------------------------------------------------------------

    def impact(
        self,
        request: ImpactRequest,
        actor: Optional[Actor] = None,
    ) -> ImpactResult:
        """
        Compute impact entries for a root entity.

        mode=forward:
            What entities may be impacted if the root changes?

        mode=backward:
            What upstream entities may impact the root?
        """

        root = self._runtime.get_entity(request.entity_id)

        if not self._can_view(root, actor, request.redact_sensitive):
            raise NotFound(f"Entity not found: {request.entity_id}")

        queue: deque = deque()
        queue.append((root.id, 1.0, 0, [], [root.id]))

        best_scores: dict[str, float] = {root.id: 1.0}
        entity_map: dict[str, Any] = {root.id: root}

        entries: list[ImpactEntry] = []
        excluded_sensitive_count = 0

        while queue:
            node_id, score, depth, hops, path_entity_ids = queue.popleft()

            if depth >= request.depth:
                continue

            for edge, neighbor_id, profile, propagation in self._propagate(
                node_id=node_id,
                mode=request.mode,
                relation_types=request.relation_types,
            ):
                try:
                    neighbor = self._runtime.get_entity(neighbor_id)
                except NotFound:
                    continue

                if not self._can_view(neighbor, actor, request.redact_sensitive):
                    excluded_sensitive_count += 1
                    continue

                entity_map[neighbor.id] = neighbor

                new_score = score * profile.weight

                if new_score < request.min_score:
                    continue

                if best_scores.get(neighbor.id, -1.0) >= new_score:
                    continue

                best_scores[neighbor.id] = new_score

                hop = RelationHop(
                    relation_id=edge.get("id", ""),
                    relation_type=edge.get("relation_type", "RELATED_TO"),
                    source_entity_id=edge.get("source_entity_id", ""),
                    target_entity_id=edge.get("target_entity_id", ""),
                    propagation=propagation,
                    weight=profile.weight,
                    reason=profile.reason,
                )

                new_hops = hops + [hop]
                new_path = path_entity_ids + [neighbor.id]
                new_depth = depth + 1

                queue.append(
                    (
                        neighbor.id,
                        new_score,
                        new_depth,
                        new_hops,
                        new_path,
                    )
                )

                if request.entity_types and neighbor.entity_type not in request.entity_types:
                    continue

                explanation = None

                if request.include_explanations:
                    explanation = self._explain_impact_entry(
                        root=root,
                        hops=new_hops,
                        entity_map=entity_map,
                    )

                entries.append(
                    ImpactEntry(
                        entity_id=neighbor.id,
                        name=neighbor.name,
                        entity_type=neighbor.entity_type,
                        score=new_score,
                        depth=new_depth,
                        direct=new_depth == 1,
                        transitive=new_depth > 1,
                        hops=new_hops,
                        path_entity_ids=new_path,
                        explanation=explanation,
                    )
                )

        entries.sort(key=lambda item: (-item.score, item.depth))
        entries = entries[: request.limit]

        metadata = ImpactMetadata(
            root_entity_id=root.id,
            mode=request.mode,
            depth=request.depth,
            min_score=request.min_score,
            node_count=len(entries),
            excluded_sensitive_count=excluded_sensitive_count,
            generated_at=utcnow().isoformat(),
        )

        return ImpactResult(
            metadata=metadata,
            entries=entries,
        )

    # ------------------------------------------------------------------
    # Path explanation
    # ------------------------------------------------------------------

    def explain_path(
        self,
        request: PathExplanationRequest,
        actor: Optional[Actor] = None,
    ) -> PathExplanationResult:
        """Explain paths between two entities."""

        source = self._runtime.get_entity(request.source_entity_id)
        target = self._runtime.get_entity(request.target_entity_id)

        if not self._can_view(source, actor, request.redact_sensitive):
            raise NotFound(f"Entity not found: {request.source_entity_id}")

        if not self._can_view(target, actor, request.redact_sensitive):
            raise NotFound(f"Entity not found: {request.target_entity_id}")

        queue: deque = deque()
        queue.append((source.id, [source.id], []))

        paths: list[PathExplanation] = []
        excluded_sensitive_count = 0

        while queue and len(paths) < request.max_paths:
            node_id, node_path, relation_ids = queue.popleft()

            if len(node_path) - 1 >= request.depth:
                continue

            for edge, neighbor_id in self._undirected_neighbors(
                node_id=node_id,
                relation_types=request.relation_types,
            ):
                if neighbor_id in node_path:
                    continue

                try:
                    neighbor = self._runtime.get_entity(neighbor_id)
                except NotFound:
                    continue

                if not self._can_view(neighbor, actor, request.redact_sensitive):
                    excluded_sensitive_count += 1
                    continue

                new_node_path = node_path + [neighbor_id]
                new_relation_ids = relation_ids + [edge.get("id", "")]

                if neighbor_id == target.id:
                    hops: list[RelationHop] = []
                    confidence = 1.0

                    for index, relation_id in enumerate(new_relation_ids):
                        relation = self._runtime.get_relation(relation_id)

                        from_node = new_node_path[index]
                        to_node = new_node_path[index + 1]

                        profile = get_impact_profile(
                            relation.relation_type,
                            self._profiles,
                        )

                        propagation = (
                            "forward"
                            if relation.source_entity_id == from_node
                            else "reverse"
                        )

                        confidence *= profile.weight

                        hops.append(
                            RelationHop(
                                relation_id=relation.id,
                                relation_type=relation.relation_type,
                                source_entity_id=relation.source_entity_id,
                                target_entity_id=relation.target_entity_id,
                                propagation=propagation,
                                weight=profile.weight,
                                reason=profile.reason,
                            )
                        )

                    evidence_refs: list[Any] = []

                    if request.include_provenance:
                        for relation_id in new_relation_ids:
                            relation = self._runtime.get_relation(relation_id)

                            evidence_refs.extend(
                                [
                                    source_ref.model_dump(mode="json")
                                    for source_ref in relation.source_refs
                                ]
                            )

                    human_summary = self._human_summary(
                        node_path=new_node_path,
                        hops=hops,
                    )

                    path_id = deterministic_id(
                        "path",
                        {
                            "nodes": new_node_path,
                            "relations": new_relation_ids,
                        },
                    )

                    paths.append(
                        PathExplanation(
                            path_id=path_id,
                            source_entity_id=source.id,
                            target_entity_id=target.id,
                            entity_ids=new_node_path,
                            relation_ids=new_relation_ids,
                            hops=hops,
                            confidence=confidence,
                            human_summary=human_summary,
                            evidence_refs=evidence_refs,
                        )
                    )

                    if len(paths) >= request.max_paths:
                        break
                else:
                    queue.append((neighbor_id, new_node_path, new_relation_ids))

        metadata = PathExplanationMetadata(
            source_entity_id=source.id,
            target_entity_id=target.id,
            path_count=len(paths),
            excluded_sensitive_count=excluded_sensitive_count,
            generated_at=utcnow().isoformat(),
        )

        return PathExplanationResult(
            metadata=metadata,
            paths=paths,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _can_view(
        self,
        entity,
        actor: Optional[Actor],
        redact_sensitive: bool,
    ) -> bool:
        if not redact_sensitive:
            return True

        classification = getattr(entity, "classification", None)

        if not classification:
            return True

        sensitivity = getattr(classification, "sensitivity", "INTERNAL")

        if sensitivity not in SENSITIVE_LEVELS:
            return True

        if not actor:
            return False

        return any(actor.has_role(role) for role in SENSITIVE_VIEWER_ROLES)

    def _touching_edges(
        self,
        node_id: str,
        relation_types: list[str],
    ) -> list[dict]:
        query = QueryRequest(
            query_type="NEIGHBORS",
            entity_id=node_id,
            direction="both",
            relation_types=relation_types,
            depth=1,
        )

        result = self._runtime.query(query)

        return result.get("edges", [])

    def _propagate(
        self,
        node_id: str,
        mode: str,
        relation_types: list[str],
    ):
        edges = self._touching_edges(node_id, relation_types)

        for edge in edges:
            relation_type = edge.get("relation_type", "RELATED_TO")
            source_id = edge.get("source_entity_id", "")
            target_id = edge.get("target_entity_id", "")

            profile = get_impact_profile(relation_type, self._profiles)

            if mode == "forward":
                if (
                    source_id == node_id
                    and profile.direction
                    in {PropagationDirection.FORWARD, PropagationDirection.BOTH}
                ):
                    yield edge, target_id, profile, "forward"

                if (
                    target_id == node_id
                    and profile.direction
                    in {PropagationDirection.REVERSE, PropagationDirection.BOTH}
                ):
                    yield edge, source_id, profile, "reverse"

            elif mode == "backward":
                if (
                    source_id == node_id
                    and profile.direction
                    in {PropagationDirection.REVERSE, PropagationDirection.BOTH}
                ):
                    yield edge, target_id, profile, "reverse"

                if (
                    target_id == node_id
                    and profile.direction
                    in {PropagationDirection.FORWARD, PropagationDirection.BOTH}
                ):
                    yield edge, source_id, profile, "forward"

    def _undirected_neighbors(
        self,
        node_id: str,
        relation_types: list[str],
    ):
        edges = self._touching_edges(node_id, relation_types)
        seen_edges: set[str] = set()

        for edge in edges:
            edge_id = edge.get("id", "")

            if edge_id in seen_edges:
                continue

            seen_edges.add(edge_id)

            source_id = edge.get("source_entity_id", "")
            target_id = edge.get("target_entity_id", "")

            if source_id == node_id:
                yield edge, target_id
            elif target_id == node_id:
                yield edge, source_id

    def _explain_impact_entry(
        self,
        root,
        hops: list[RelationHop],
        entity_map: dict[str, Any],
    ) -> str:
        current_id = root.id
        parts = [root.name]

        for hop in hops:
            if hop.source_entity_id == current_id:
                next_id = hop.target_entity_id
            else:
                next_id = hop.source_entity_id

            entity = entity_map.get(next_id)
            next_name = entity.name if entity else next_id

            parts.append(f"--{hop.relation_type}--> {next_name}")

            current_id = next_id

        return " ".join(parts)

    def _human_summary(
        self,
        node_path: list[str],
        hops: list[RelationHop],
    ) -> str:
        parts: list[str] = []

        for index, hop in enumerate(hops):
            from_id = node_path[index]
            to_id = node_path[index + 1]

            try:
                from_entity = self._runtime.get_entity(from_id)
                from_name = from_entity.name
            except NotFound:
                from_name = from_id

            try:
                to_entity = self._runtime.get_entity(to_id)
                to_name = to_entity.name
            except NotFound:
                to_name = to_id

            parts.append(f"{from_name} --{hop.relation_type}--> {to_name}")

        return "; ".join(parts)
