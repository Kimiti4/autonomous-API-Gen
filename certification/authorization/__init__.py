"""Source-bound authorization certification lane.

This lane certifies authorization enforcement for the Python backend against
explicit, source-bound policies. It is separate from the general Campaign A
substrate matrix, which is unchanged.
"""
from __future__ import annotations

from certification.authorization.corpus import (
    CORPUS_VERSION,
    AuthorizationWorkload,
    DeclaredOperation,
    MutationCase,
    OperationBinding,
    build_workload,
    corpus_hash,
    rebuild_workload,
    validate_workload,
)
from certification.authorization.workloads import (
    AUTHORIZATION_CORPUS,
    AUTHORIZATION_CORPUS_HASH,
    CORPUS_ID,
    CORPUS_METADATA,
)

__all__ = [
    "AUTHORIZATION_CORPUS",
    "AUTHORIZATION_CORPUS_HASH",
    "CORPUS_ID",
    "CORPUS_METADATA",
    "CORPUS_VERSION",
    "AuthorizationWorkload",
    "DeclaredOperation",
    "MutationCase",
    "OperationBinding",
    "build_workload",
    "corpus_hash",
    "rebuild_workload",
    "validate_workload",
]
