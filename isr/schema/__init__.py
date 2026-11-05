"""Canonical ISR schema registry exports.

The implementation lives only in :mod:`isr.schema.versions`; this package
is a compatibility re-export, not a second registry.
"""
from isr.schema.versions import (
    CURRENT_SCHEMA_VERSION,
    LATEST_MIGRATION,
    SCHEMA_REGISTRY,
    SUPPORTED_SCHEMA_VERSIONS,
    ISRSchemaViolation,
    migrate_1_0_to_1_1,
    migrate_1_1_to_2_0,
    migrate_graph,
    migrate_revision,
    validate_schema_graph,
)

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "LATEST_MIGRATION",
    "SCHEMA_REGISTRY",
    "SUPPORTED_SCHEMA_VERSIONS",
    "ISRSchemaViolation",
    "migrate_1_0_to_1_1",
    "migrate_1_1_to_2_0",
    "migrate_graph",
    "migrate_revision",
    "validate_schema_graph",
]
