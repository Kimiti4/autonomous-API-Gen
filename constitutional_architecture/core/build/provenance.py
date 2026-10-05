"""
Phase 16 — Artifact Provenance & Incremental Compilation Cache
Content-addressable caching (Nix/CCache semantics) for compiled bundles.

Cache key = Hash(compiler_id + compiler_version + scoped ISR signature +
scoped Genome signature + input bundle hashes). When a compiler declares its
consumed scope (genes/node types), only mutations inside that scope invalidate
its cache entry — mutating a frontend gene does not recompile the database.

Every artifact is stamped with immutable ArtifactProvenance, cryptographically
linking it to the Intent, Genome, ISR, and Compiler Version that produced it.
This provenance is the precondition for Phase 18's Runtime Learning Engine:
production telemetry can only be correlated with a Genome if the artifact
carries its genetic identity.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from constitutional_architecture.core.models.bundle import CompilationBundle
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.intent import IntentModel
from constitutional_architecture.core.models.isr import NodeType, UniversalISR


class ArtifactProvenance(BaseModel):
    """Immutable record of how an artifact was generated."""

    artifact_hash: str
    compiler_id: str
    compiler_version: str
    genome_id: str
    genome_hash: str
    isr_hash: str
    intent_hash: str
    timestamp: datetime
    input_dependencies: List[str] = []


def bundle_hash(bundle: CompilationBundle) -> str:
    """Content hash of a CompilationBundle (its output signature)."""
    return hashlib.sha256(
        json.dumps(bundle.model_dump(), sort_keys=True).encode()
    ).hexdigest()


def isr_signature(
    isr: UniversalISR,
    node_types: Optional[List[NodeType]] = None,
) -> str:
    """Deterministic signature of the ISR, optionally scoped to consumed
    node types. `None` hashes the entire ISR; `[]` hashes a constant scope."""
    if node_types is None:
        scope: Any = isr.model_dump()
    else:
        keep = set(node_types)
        nodes = {
            nid: n.model_dump() for nid, n in isr.nodes.items() if n.type in keep
        }
        edges = [
            e.model_dump() for e in isr.edges
            if e.source_id in nodes and e.target_id in nodes
        ]
        scope = {"nodes": nodes, "edges": edges}
    return hashlib.sha256(json.dumps(scope, sort_keys=True).encode()).hexdigest()


def genome_signature(
    genome: ArchitectureGenome,
    genes: Optional[List[str]] = None,
) -> str:
    """Deterministic signature of the Genome, optionally scoped to consumed
    gene ids. `None` hashes the whole genome; `[]` hashes a constant scope."""
    if genes is None:
        scope = genome.serialize()
    else:
        scope = {
            "categorical": {
                gid: genome.categorical_genes[gid].serialize()
                for gid in genes if gid in genome.categorical_genes
            },
            "continuous": {
                gid: genome.continuous_genes[gid].serialize()
                for gid in genes if gid in genome.continuous_genes
            },
        }
    return hashlib.sha256(json.dumps(scope, sort_keys=True).encode()).hexdigest()


def intent_signature(intent: IntentModel) -> str:
    return hashlib.sha256(intent.model_dump_json().encode()).hexdigest()[:12]


class EvolutionaryBuildCache:
    """Content-addressable cache for compiled bundles."""

    def __init__(self) -> None:
        self._cache: Dict[str, CompilationBundle] = {}
        self._provenance: Dict[str, ArtifactProvenance] = {}

    def compute_cache_key(
        self,
        compiler_id: str,
        compiler_version: str,
        isr_hash: str,
        genome_hash: str,
        input_bundle_hashes: List[str],
    ) -> str:
        payload = (
            f"{compiler_id}:{compiler_version}:{isr_hash}:{genome_hash}:"
            f"{','.join(sorted(input_bundle_hashes))}"
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, cache_key: str) -> Optional[CompilationBundle]:
        return self._cache.get(cache_key)

    def provenance_of(self, cache_key: str) -> ArtifactProvenance:
        return self._provenance[cache_key]

    def put(
        self,
        cache_key: str,
        bundle: CompilationBundle,
        provenance: ArtifactProvenance,
    ) -> None:
        self._cache[cache_key] = bundle
        self._provenance[cache_key] = provenance

    @property
    def size(self) -> int:
        return len(self._cache)
