import hashlib
import json
from pydantic import BaseModel, Field
from .intent import IntentSpecification
from .system_model import (
    SystemModel,
    TechnologyCouplingError,
    scan_for_technology_coupling,
)


#: ISR envelope payload discriminators (additive; do NOT participate in
#: content_hash, which remains computed over the architectural sections).
PAYLOAD_TYPE_LEGACY = "legacy"
PAYLOAD_TYPE_SYSTEM_MODEL_V1 = "system_model.v1"


class ServiceSpec(BaseModel):
    name: str
    responsibilities: list[str] = Field(default_factory=list)
    exposed_capabilities: list[str] = Field(default_factory=list)
    port: int = 8000


class DataModelSpec(BaseModel):
    name: str
    fields: dict[str, str] = Field(default_factory=dict)


class SecuritySpec(BaseModel):
    authentication: str = "anonymous"
    authorization_model: str = "none"
    secrets_via_env: bool = True


class ObservabilitySpec(BaseModel):
    health_endpoint: str = "/health"
    readiness_endpoint: str = "/ready"
    structured_logging: bool = True


class ResourceLimits(BaseModel):
    memory: str = "256m"
    cpus: float = 0.5


class DeploymentSpec(BaseModel):
    container_runtime: str = "docker"
    replicas: int = 1
    limits: ResourceLimits = Field(default_factory=ResourceLimits)


class IntermediateSoftwareRepresentation(BaseModel):
    schema_version: str = "1.0"
    system_id: str
    system_name: str
    intent: IntentSpecification
    services: list[ServiceSpec] = Field(default_factory=list)
    data_models: list[DataModelSpec] = Field(default_factory=list)
    security: SecuritySpec = Field(default_factory=SecuritySpec)
    observability: ObservabilitySpec = Field(default_factory=ObservabilitySpec)
    deployment: DeploymentSpec = Field(default_factory=DeploymentSpec)
    lineage: list[str] = Field(default_factory=list)

    # Capability A: dual-path envelope. Both fields are serialization-excluded
    # so content_hash (sha256 of model_dump_json(exclude={"lineage"})) is
    # byte-identical for legacy envelopes and therefore hash-chain compatible.
    payload_type: str = Field(PAYLOAD_TYPE_LEGACY, exclude=True)
    content: dict | None = Field(default=None, exclude=True)

    def content_hash(self) -> str:
        payload = self.model_dump_json(exclude={"lineage"})
        return hashlib.sha256(payload.encode()).hexdigest()

    # ------------------------------------------------------------------
    # Capability A: typed ISR accessors
    # ------------------------------------------------------------------
    @classmethod
    def from_system_model(
        cls,
        system_id: str,
        model: SystemModel,
        lineage: list[str] | None = None,
    ) -> "IntermediateSoftwareRepresentation":
        """Build a typed-v1 envelope carrying a SystemModel payload.

        Enforces the constitutional technology-agnostic boundary: a SystemModel
        containing technology tokens is rejected (TechnologyCouplingError)
        before it can enter the evidence chain.
        """
        violations = scan_for_technology_coupling(model)
        if violations:
            raise TechnologyCouplingError(violations)
        domain = model.domains[0].id if model.domains else "general"
        return cls(
            system_id=system_id,
            system_name=model.system_name,
            intent=IntentSpecification(
                statement=model.problem_statement or model.system_name,
                domain=domain,
            ),
            lineage=list(lineage or []),
            payload_type=PAYLOAD_TYPE_SYSTEM_MODEL_V1,
            content={"system_model": model.canonical_payload()},
        )

    def system_model(self) -> SystemModel | None:
        """Decode the typed payload, or None for legacy envelopes."""
        if self.payload_type != PAYLOAD_TYPE_SYSTEM_MODEL_V1:
            return None
        return SystemModel.model_validate(self.content["system_model"])
