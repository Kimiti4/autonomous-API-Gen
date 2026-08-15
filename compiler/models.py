"""
Universal Compiler data models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    """Return timezone-aware UTC current time."""
    return datetime.now(timezone.utc)


class CompilationTarget(BaseModel):
    """Requested compilation target."""

    backend_id: str
    backend_version: Optional[str] = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class CompilationRequest(BaseModel):
    """Request to compile an ISR payload."""

    isr: dict[str, Any]
    target: CompilationTarget

    environment: str = "development"
    actor_id: Optional[str] = None

    options: dict[str, Any] = Field(default_factory=dict)


class BackendCapabilities(BaseModel):
    """Capabilities declared by a compiler backend."""

    supported_targets: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    artifact_types: list[str] = Field(default_factory=list)
    deployment_targets: list[str] = Field(default_factory=list)

    maturity: str = "experimental"


class BackendManifest(BaseModel):
    """Manifest describing a compiler backend."""

    backend_id: str
    name: str
    version: str

    description: str = ""

    capabilities: BackendCapabilities

    entrypoint: str = ""
    config_schema: dict[str, Any] = Field(default_factory=dict)


class BackendHealth(BaseModel):
    """Health status for a compiler backend."""

    backend_id: str
    status: Literal[
        "ok",
        "degraded",
        "error",
    ]
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class CapabilityQuery(BaseModel):
    """Query for discovering capable backends."""

    supported_targets: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    artifact_types: list[str] = Field(default_factory=list)
    deployment_targets: list[str] = Field(default_factory=list)


class CompilationPlan(BaseModel):
    """Deterministic compilation plan."""

    plan_id: str

    isr_id: str
    isr_version: str

    backend_id: str
    backend_version: str

    environment: str

    parameters: dict[str, Any] = Field(default_factory=dict)
    passes: list[str] = Field(default_factory=list)

    validation_level: str = "standard"

    created_at: str


class GeneratedArtifact(BaseModel):
    """Artifact produced by a compiler backend."""

    path: str
    content: str
    content_type: str = "text/plain"


class CompilationOutput(BaseModel):
    """Output returned by a compiler backend."""

    artifacts: list[GeneratedArtifact] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)


class CompilationContext(BaseModel):
    """Context passed to a compiler backend."""

    plan: CompilationPlan
    isr: dict[str, Any]
    output_directory: str


class ArtifactFile(BaseModel):
    """Packaged artifact metadata."""

    path: str
    content_hash: str
    size_bytes: int
    content_type: str


class ArtifactManifest(BaseModel):
    """Manifest describing packaged compilation artifacts."""

    manifest_id: str
    compilation_job_id: str

    backend_id: str
    backend_version: str

    created_at: str

    files: list[ArtifactFile] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    """Validation issue."""

    severity: Literal[
        "ERROR",
        "WARNING",
        "INFO",
    ]

    code: str
    message: str
    path: Optional[str] = None


class ValidationReport(BaseModel):
    """Validation report."""

    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)


class CompilationResult(BaseModel):
    """Compilation job result."""

    job_id: str

    status: Literal[
        "PENDING",
        "RUNNING",
        "SUCCEEDED",
        "FAILED",
    ]

    plan: Optional[CompilationPlan] = None

    started_at: str
    completed_at: Optional[str] = None

    artifact_manifest: Optional[ArtifactManifest] = None
    validation_report: Optional[ValidationReport] = None

    logs: list[str] = Field(default_factory=list)
    error: Optional[str] = None