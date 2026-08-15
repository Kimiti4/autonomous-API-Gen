"""Phase 18 -- Software Factory composition root."""

from .factory import SoftwareFactory
from .fitness import build_fitness
from .repair_providers import (
    NullRepairProvider,
    RematerializationRepairProvider,
)
from .report import (
    SoftwareFactoryError,
    SoftwareFactoryReport,
    VerificationOutcome,
)

__all__ = [
    "SoftwareFactory",
    "build_fitness",
    "NullRepairProvider",
    "RematerializationRepairProvider",
    "SoftwareFactoryError",
    "SoftwareFactoryReport",
    "VerificationOutcome",
]
