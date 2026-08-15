"""
SQLite-backed persistence adapters for the Knowledge Graph.

These adapters provide a simple persistent reference implementation.

They are intentionally conservative:
- No external database dependency.
- Replaceable by PostgreSQL, Neo4j, OpenSearch, or other plugins.
- The Knowledge Graph core remains backend-neutral.
"""

from __future__ import annotations

import sqlite3
import threading
from typing import Optional

from ..errors import NotFound
from ..models import Entity, GraphPath, GraphSlice, Relation, SearchRequest, SearchResponse, SearchResult
from ..search import tokenize


class SQLiteGraphStore:
    """
    Persistent SQLite graph store.

    This is a reference persistent implementation of the GraphStore contract.
    """

    def __init__(self, database_path: str) -> None:
        self._database_path = database_path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            database_path,
            check_same_thread=False,
        )

        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    name TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_entities_type
                    ON entities(entity_type);

                CREATE INDEX IF NOT EXISTS idx_entities_namespace
                    ON entities(namespace);

                CREATE TABLE IF NOT EXISTS relations (
                    id TEXT PRIMARY KEY,
                    relation_type TEXT NOT NULL,
                    source_entity_id TEXT NOT NULL,
                    target_entity_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_relations_source
                    ON relations(source_entity_id);

                CREATE INDEX IF NOT EXISTS idx_relations_target
                    ON relations(target_entity_id);

                CREATE INDEX IF NOT EXISTS idx_relations_type
                    ON relations(relation_type);
                """
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def upsert_entity(self, entity: Entity) -> Entity:
        payload = entity.model_dump_json()

        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO entities (
                    id,
                    entity_type,
                    namespace,
                    name,
                    payload
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    entity.id,
                    entity.entity_type,
                    entity.namespace,
                    entity.name,
                    payload,
                ),
            )
            self._conn.commit()

        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        with self._lock:
            cursor = self._conn.execute(
                """
                SELECT payload
                FROM entities
                WHERE id = ?
                """,
                (entity_id,),
            )
            row = cursor.fetchone()

        if not row:
            return None

        return Entity.model_validate_json(row[0])

    def list_entities(
        self,
        entity_type: Optional[str] = None,
        namespace: Optional[str] = None,
        limit: int = 100,
    ) -> list[Entity]:
        where: list[str] = []
        params: list[str | int] = []

        if entity_type:
            where.append("entity_type = ?")
            params.append(entity_type)

        if namespace:
            where.append("namespace = ?")
            params.append(namespace)

        sql = "SELECT payload FROM entities"

        if where:
            sql += " WHERE " + " AND ".join(where)

        sql += " LIMIT ?"
        params.append(limit)

        with self._lock:
            cursor = self._conn.execute(sql, params)
            rows = cursor.fetchall()

        return [Entity.model_validate_json(row[0]) for row in rows]

    def upsert_relation(self, relation: Relation) -> Relation:
        payload = relation.model_dump_json()

        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO relations (
                    id,
                    relation_type,
                    source_entity_id,
                    target_entity_id,
                    payload
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    relation.id,
                    relation.relation_type,
                    relation.source_entity_id,
                    relation.target_entity_id,
                    payload,
                ),
            )
            self._conn.commit()

        return relation

    def get_relation(self, relation_id: str) -> Optional[Relation]:
        with self._lock:
            cursor = self._conn.execute(
                """
                SELECT payload
                FROM relations
                WHERE id = ?
                """,
                (relation_id,),
            )
            row = cursor.fetchone()

        if not row:
            return None

        return Relation.model_validate_json(row[0])

    def _fetch_relations_for_node(
        self,
        node_id: str,
        direction: str,
    ) -> list[Relation]:
        clauses: list[str] = []
        params: list[str] = []

        if direction in {"forward", "both"}:
            clauses.append("source_entity_id = ?")
            params.append(node_id)

        if direction in {"backward", "both"}:
            clauses.append("target_entity_id = ?")
            params.append(node_id)

        if not clauses:
            return []

        sql = f"""
        SELECT payload
        FROM relations
        WHERE {" OR ".join(clauses)}
        """

        with self._lock:
            cursor = self._conn.execute(sql, params)
            rows = cursor.fetchall()

        return [Relation.model_validate_json(row[0]) for row in rows]

    def neighbors(
        self,
        entity_id: str,
        direction: str,
        relation_types: list[str],
        depth: int,
    ) -> GraphSlice:
        if self.get_entity(entity_id) is None:
            raise NotFound(f"Entity not found: {entity_id}")

        visited_nodes: set[str] = {entity_id}
        visited_edges: set[str] = set()
        edges: list[Relation] = []
        frontier: list[str] = [entity_id]

        relation_filter = set(relation_types)

        for _ in range(depth):
            next_frontier: list[str] = []

            for node_id in frontier:
                relations = self._fetch_relations_for_node(node_id, direction)

                for relation in relations:
                    if relation_filter and relation.relation_type not in relation_filter:
                        continue

                    if relation.source_entity_id == node_id:
                        neighbor_id = relation.target_entity_id
                    else:
                        neighbor_id = relation.source_entity_id

                    if relation.id not in visited_edges:
                        visited_edges.add(relation.id)
                        edges.append(relation)

                    if neighbor_id not in visited_nodes:
                        visited_nodes.add(neighbor_id)
                        next_frontier.append(neighbor_id)

            frontier = next_frontier

        nodes: list[Entity] = []

        for node_id in visited_nodes:
            entity = self.get_entity(node_id)
            if entity:
                nodes.append(entity)

        return GraphSlice(nodes=nodes, edges=edges)

    def find_paths(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relation_types: list[str],
        depth: int,
        max_results: int,
    ) -> list[GraphPath]:
        if self.get_entity(source_entity_id) is None:
            raise NotFound(f"Source entity not found: {source_entity_id}")

        if self.get_entity(target_entity_id) is None:
            raise NotFound(f"Target entity not found: {target_entity_id}")

        relation_filter = set(relation_types)
        results: list[GraphPath] = []

        queue: list[tuple[str, list[str], list[str]]] = [
            (source_entity_id, [source_entity_id], [])
        ]

        while queue:
            node_id, node_path, relation_path = queue.pop(0)

            if len(node_path) - 1 >= depth:
                continue

            with self._lock:
                cursor = self._conn.execute(
                    """
                    SELECT payload
                    FROM relations
                    WHERE source_entity_id = ?
                    """,
                    (node_id,),
                )
                rows = cursor.fetchall()

            for row in rows:
                relation = Relation.model_validate_json(row[0])

                if relation_filter and relation.relation_type not in relation_filter:
                    continue

                next_node = relation.target_entity_id

                if next_node in node_path:
                    continue

                next_node_path = node_path + [next_node]
                next_relation_path = relation_path + [relation.id]

                if next_node == target_entity_id:
                    results.append(
                        GraphPath(
                            nodes=next_node_path,
                            relations=next_relation_path,
                        )
                    )

                    if len(results) >= max_results:
                        return results
                else:
                    queue.append((next_node, next_node_path, next_relation_path))

        return results


class SQLiteSearchStore:
    """
    Persistent SQLite lexical search store.

    This is intentionally simple. It should be replaced by a dedicated
    search engine adapter in larger deployments.
    """

    def __init__(self, database_path: str) -> None:
        self._database_path = database_path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            database_path,
            check_same_thread=False,
        )

        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS search_documents (
                    entity_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    text TEXT NOT NULL
                );
                """
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def index_entity(self, entity: Entity) -> None:
        searchable_text = " ".join(
            [
                entity.name,
                entity.description or "",
                " ".join(entity.labels),
                str(entity.properties),
            ]
        )

        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO search_documents (
                    entity_id,
                    entity_type,
                    name,
                    text
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    entity.id,
                    entity.entity_type,
                    entity.name,
                    searchable_text,
                ),
            )
            self._conn.commit()

    def search(self, request: SearchRequest) -> SearchResponse:
        query_tokens = tokenize(request.text)

        if not query_tokens:
            return SearchResponse(results=[])

        with self._lock:
            cursor = self._conn.execute(
                """
                SELECT entity_id, entity_type, name, text
                FROM search_documents
                """
            )
            rows = cursor.fetchall()

        results: list[SearchResult] = []

        for entity_id, entity_type, name, text in rows:
            if request.entity_types and entity_type not in request.entity_types:
                continue

            document_tokens = tokenize(f"{name} {text}")
            common = query_tokens.intersection(document_tokens)

            if not common:
                if request.text.lower() in f"{name} {text}".lower():
                    occurrences = f"{name} {text}".lower().count(request.text.lower())
                    score = 0.5 * occurrences / len(query_tokens)
                else:
                    continue
            else:
                score = len(common) / len(query_tokens)

            if name.lower() == request.text.lower():
                score += 0.25

            snippet = text[:160] if text else name

            results.append(
                SearchResult(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    name=name,
                    score=score,
                    snippet=snippet,
                )
            )

        results.sort(key=lambda item: item.score, reverse=True)

        return SearchResponse(results=results[: request.limit])
