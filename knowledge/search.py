"""
Search abstraction.

The default implementation is a simple lexical search engine.

This preserves technology neutrality. A production system may replace this
with Elasticsearch, OpenSearch, vector search, or another plugin.
"""

from __future__ import annotations

import re
from typing import Protocol

from .models import Entity, SearchRequest, SearchResponse, SearchResult


def tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase alphanumeric tokens."""
    return {token for token in re.findall(r"[a-z0-9_]+", text.lower()) if token}


class SearchStore(Protocol):
    """Abstract search adapter."""

    def index_entity(self, entity: Entity) -> None:
        ...

    def search(self, request: SearchRequest) -> SearchResponse:
        ...


class InMemorySearchStore:
    """
    In-memory lexical search store.

    This is intentionally simple and deterministic.
    """

    def __init__(self) -> None:
        self._documents: dict[str, dict] = {}

    def index_entity(self, entity: Entity) -> None:
        searchable_text = " ".join(
            [
                entity.name,
                entity.description or "",
                " ".join(entity.labels),
                str(entity.properties),
            ]
        )

        self._documents[entity.id] = {
            "entity": entity,
            "tokens": tokenize(searchable_text),
            "searchable_text": searchable_text.lower(),
            "snippet": entity.description or entity.name,
        }

    def search(self, request: SearchRequest) -> SearchResponse:
        query_tokens = tokenize(request.text)

        if not query_tokens:
            return SearchResponse(results=[])

        results: list[SearchResult] = []

        for document in self._documents.values():
            entity: Entity = document["entity"]

            if request.entity_types and entity.entity_type not in request.entity_types:
                continue

            document_tokens: set[str] = document["tokens"]
            common = query_tokens.intersection(document_tokens)

            if common:
                score = len(common) / len(query_tokens)
            else:
                searchable = document.get("searchable_text", "")

                if request.text.lower() in searchable:
                    occurrences = searchable.count(request.text.lower())
                    score = 0.5 * occurrences / len(query_tokens)
                else:
                    continue

            if entity.name.lower() == request.text.lower():
                score += 0.25

            results.append(
                SearchResult(
                    entity_id=entity.id,
                    entity_type=entity.entity_type,
                    name=entity.name,
                    score=score,
                    snippet=document["snippet"],
                )
            )

        results.sort(key=lambda item: item.score, reverse=True)

        return SearchResponse(results=results[: request.limit])
