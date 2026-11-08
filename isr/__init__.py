"""ISR constitutional substrate (ADR-008).

The immutable, content-addressed, typed directed graph that is the single
semantic source of truth for software architecture. Technology-independent;
persistence and evolution live behind ports.
"""

from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.canonicalization_registry import (
    CanonicalizationContract,
    F01_ISR_REVISION,
    F02_ISR_GRAPH,
    get_canonicalization_contract,
)
from isr.core.digest_envelope import DigestEnvelope
from isr.core.digest_verification import (
    assert_certification_digest_envelope,
    build_digest_envelope_for_revision,
)
from isr.core.identity import Provenance, compute_content_hash
from isr.core.invariants import (
    FORBIDDEN_IMPLEMENTATION_TERMS,
    ISRInvariantViolation,
    validate_invariants,
)
from isr.core.revision import ISRRevision

__all__ = [
    "CanonicalizationContract",
    "DigestEnvelope",
    "F01_ISR_REVISION",
    "F02_ISR_GRAPH",
    "assert_certification_digest_envelope",
    "build_digest_envelope_for_revision",
    "Edge",
    "EdgeType",
    "FORBIDDEN_IMPLEMENTATION_TERMS",
    "ISRGraph",
    "ISRInvariantViolation",
    "ISRRevision",
    "Node",
    "NodeType",
    "Provenance",
    "compute_content_hash",
    "get_canonicalization_contract",
    "validate_invariants",
]
