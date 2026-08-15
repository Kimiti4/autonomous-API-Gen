"""Constitutional governance seams for the Tiannara domain layer.

Exports the legacy-coupling boundary: the coupling registry (frozen debt
checklist) and the static coupling scanner used by the bidirectional guard
test.
"""

from .coupling_registry import (
    CouplingCategory,
    CouplingRegistryEntry,
    LEGACY_COUPLING_REGISTRY,
)
from .coupling_scanner import (
    CouplingFinding,
    scan_domain_models,
    scan_enum_class,
    scan_model_class,
)

__all__ = [
    "CouplingCategory",
    "CouplingRegistryEntry",
    "LEGACY_COUPLING_REGISTRY",
    "CouplingFinding",
    "scan_domain_models",
    "scan_enum_class",
    "scan_model_class",
]
