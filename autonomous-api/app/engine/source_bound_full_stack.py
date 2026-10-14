"""Fail-closed boundary for source-bound full-stack IR projection.

This module deliberately does not infer routes, authorization, effects, or
replay policies from requirement prose. A trusted projection must provide
explicit mappings with provenance back to source requirement IDs. Until that
contract is populated by the authoritative ISR adapter, callers receive
structured blockers rather than fabricated IR.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping


REQUIRED_LAYERS = ("frontend", "api", "backend", "effects", "consequences")


@dataclass(frozen=True)
class ProjectionBlocker:
    code: str
    message: str
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceBoundProjection:
    status: str
    source_hash: str
    candidate_hash: str
    inputs: tuple[Any, Any, Any, Any, Any] | None
    blockers: tuple[ProjectionBlocker, ...]
    mapping_hash: str | None

    @property
    def ready(self) -> bool:
        return self.status == "ready" and self.inputs is not None and not self.blockers


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _as_dict(value: Any) -> dict[str, Any] | None:
    if hasattr(value, "model_dump"):
        result = value.model_dump()
    elif hasattr(value, "to_dict"):
        result = value.to_dict()
    elif isinstance(value, Mapping):
        result = dict(value)
    else:
        return None
    return result if isinstance(result, dict) else None


def project_source_bound_full_stack(
    *,
    source_artifacts: Any,
    candidate_files: Mapping[str, str],
    explicit_mapping: Mapping[str, Any] | None = None,
) -> SourceBoundProjection:
    """Validate an explicit source-to-IR mapping; never guess missing semantics.

    explicit_mapping must contain all five layers and provenance references.
    This is a fail-closed contract seam, not yet a semantic lowering engine.
    """
    blockers: list[ProjectionBlocker] = []
    source_dict = _as_dict(source_artifacts)
    if source_dict is None:
        source_hash = ""
        blockers.append(ProjectionBlocker(
            "SBFS-001", "source artifacts are not canonically serializable"
        ))
    else:
        source_hash = _canonical_hash(source_dict)

    if not isinstance(candidate_files, Mapping) or not candidate_files:
        candidate_hash = ""
        blockers.append(ProjectionBlocker(
            "SBFS-002", "candidate file manifest is missing or empty"
        ))
    elif any(not isinstance(path, str) or not path or not isinstance(body, str)
             for path, body in candidate_files.items()):
        candidate_hash = ""
        blockers.append(ProjectionBlocker(
            "SBFS-003", "candidate manifest must map non-empty paths to text contents"
        ))
    else:
        candidate_hash = _canonical_hash(dict(candidate_files))

    if not isinstance(explicit_mapping, Mapping):
        blockers.append(ProjectionBlocker(
            "SBFS-004",
            "explicit source-to-architecture mapping is absent; semantics will not be inferred"
        ))
        mapping_hash = None
    else:
        mapping_hash = _canonical_hash(dict(explicit_mapping))
        missing = [layer for layer in REQUIRED_LAYERS if layer not in explicit_mapping]
        for layer in missing:
            blockers.append(ProjectionBlocker(
                "SBFS-005", f"required architectural layer is unmapped: {layer}"
            ))
        provenance = explicit_mapping.get("provenance")
        if not isinstance(provenance, Mapping):
            blockers.append(ProjectionBlocker(
                "SBFS-006", "mapping provenance is missing"
            ))
        else:
            source_refs = provenance.get("source_refs")
            if not isinstance(source_refs, (list, tuple)) or not source_refs:
                blockers.append(ProjectionBlocker(
                    "SBFS-007", "mapping must reference source requirement/ISR identifiers"
                ))
            elif source_dict is not None:
                known_refs = set(source_dict.get("source_refs", ()))
                if known_refs and not set(source_refs).issubset(known_refs):
                    blockers.append(ProjectionBlocker(
                        "SBFS-008", "mapping references source identifiers absent from source artifacts",
                        tuple(str(x) for x in source_refs),
                    ))

        for layer in REQUIRED_LAYERS:
            if layer in explicit_mapping and explicit_mapping[layer] is None:
                blockers.append(ProjectionBlocker(
                    "SBFS-009", f"architectural layer is explicitly null: {layer}"
                ))

    # Do not construct IR objects here. A mapping contract is not proof that
    # it has been lowered into canonical IR classes or independently validated.
    return SourceBoundProjection(
        status="blocked" if blockers else "mapping_present_unverified",
        source_hash=source_hash,
        candidate_hash=candidate_hash,
        inputs=None,
        blockers=tuple(blockers),
        mapping_hash=mapping_hash,
    )
