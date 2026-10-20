"""W01-W22 remediation register (machine-readable, fail-closed)."""

from certification.remediation.register import (
    DEFECTS,
    KNOWN_PRS,
    SCHEMA_ID,
    SCHEMA_VERSION,
    WORK_PACKAGES,
    CertificationTier,
    Defect,
    DefectStatus,
    Evidence,
    EvidenceKind,
    Status,
    WorkPackage,
    register_payload,
    validate_register,
)

__all__ = [
    "DEFECTS",
    "KNOWN_PRS",
    "SCHEMA_ID",
    "SCHEMA_VERSION",
    "WORK_PACKAGES",
    "CertificationTier",
    "Defect",
    "DefectStatus",
    "Evidence",
    "EvidenceKind",
    "Status",
    "WorkPackage",
    "register_payload",
    "validate_register",
]
