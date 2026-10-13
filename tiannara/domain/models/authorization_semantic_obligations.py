"""Typed authorization-semantic consumer for TaskFlow compilation.

This module turns the two authorization ledger entries into a typed,
immutable compiler input. It is intentionally not a runtime authorization
engine: backend/runtime enforcement must consume the resulting obligations
before the semantic trace can be marked complete.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tiannara.domain.models.semantic_resolution import (
    ResolutionKind,
    SemanticResolutionRecord,
    resolutions_by_field,
)

WORKSPACE_SCOPE_PATH = "authorization.workspace_membership_scope"
ROLE_PERMISSION_PATH = "authorization.owner_manager_member_permissions"
AUTHORIZATION_PATHS = (WORKSPACE_SCOPE_PATH, ROLE_PERMISSION_PATH)


class AuthorizationSemanticConsumptionError(ValueError):
    """Raised when authorization semantics cannot safely form typed obligations."""


class AuthorizationSemanticObligations(BaseModel):
    """Typed, immutable authorization obligations bound to their exact sources.

    The source values are retained as structured mappings so no policy detail
    is silently dropped or defaulted. The digest makes mutation detectable.
    This is an intermediate compiler contract, not proof of runtime enforcement.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_scope: dict[str, Any]
    role_permissions: dict[str, Any]
    source_graph_id: str = Field(min_length=1)
    source_graph_hash: str = Field(min_length=1)
    source_paths: tuple[str, ...]
    canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AuthorizationSemanticConsumptionError(
            "authorization semantic values must be canonical JSON data"
        ) from exc


def consume_authorization_semantics(
    record: SemanticResolutionRecord,
) -> AuthorizationSemanticObligations:
    """Consume both required authorization values without inventing policy.

    Unresolved, missing, scalar, empty, or non-canonical values fail closed.
    Exact source values are retained in typed fields; no extension-only mirror
    is treated as evidence of consumption.
    """
    if not all(path in record.required_fields for path in AUTHORIZATION_PATHS):
        raise AuthorizationSemanticConsumptionError(
            "record does not declare the authoritative authorization semantic paths"
        )

    by_path = resolutions_by_field(record)
    values: dict[str, dict[str, Any]] = {}
    for path in AUTHORIZATION_PATHS:
        item = by_path.get(path)
        if item is None or item.kind is ResolutionKind.UNRESOLVED:
            raise AuthorizationSemanticConsumptionError(
                f"required authorization semantic is unresolved: {path}"
            )
        if not isinstance(item.value, Mapping) or not item.value:
            raise AuthorizationSemanticConsumptionError(
                f"authorization semantic must be a non-empty object: {path}"
            )
        # Round-trip through canonical JSON to reject non-JSON values and
        # detach the consumer payload from mutable caller-owned objects.
        values[path] = json.loads(_canonical(dict(item.value)))

    payload = {
        "graph_id": record.graph_id,
        "graph_hash": record.graph_hash,
        "workspace_scope": values[WORKSPACE_SCOPE_PATH],
        "role_permissions": values[ROLE_PERMISSION_PATH],
        "source_paths": list(AUTHORIZATION_PATHS),
    }
    digest = hashlib.sha256(_canonical(payload)).hexdigest()
    return AuthorizationSemanticObligations(
        workspace_scope=values[WORKSPACE_SCOPE_PATH],
        role_permissions=values[ROLE_PERMISSION_PATH],
        source_graph_id=record.graph_id,
        source_graph_hash=record.graph_hash,
        source_paths=AUTHORIZATION_PATHS,
        canonical_sha256=digest,
    )
