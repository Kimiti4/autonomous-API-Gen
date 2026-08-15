"""
Knowledge Graph error model.

All expected domain errors derive from KnowledgeGraphError so API layers
can fail closed with structured error handling.
"""


class KnowledgeGraphError(Exception):
    """Base error for the Knowledge Graph runtime."""


class OntologyViolation(KnowledgeGraphError):
    """Raised when an entity, relation, or property violates the ontology."""


class MissingProvenance(KnowledgeGraphError):
    """Raised when an entity or relation is created without provenance."""


class NotFound(KnowledgeGraphError):
    """Raised when a requested entity or relation does not exist."""


class InvalidQuery(KnowledgeGraphError):
    """Raised when a query request is malformed or unsupported."""
