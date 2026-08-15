import enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .model_call import DecodingParameters, ModelCallRecord
from ..services.canonical import canonical_hash


class LocalityLevel(int, enum.Enum):
    """Cascade ordering. Lower = more deterministic, less intelligence."""

    L0_DETERMINISTIC = 0
    L1_ALGORITHMIC = 1
    L2_LOCAL_MODEL = 2
    L3_EXTERNAL_MODEL = 3


class ProviderClass(str, enum.Enum):
    DETERMINISTIC_COMPILER = "deterministic_compiler"
    ALGORITHMIC = "algorithmic"
    LOCAL_MODEL = "local_model"
    REMOTE_MODEL = "remote_model"


PROVIDER_CLASS_LOCALITY: dict[ProviderClass, LocalityLevel] = {
    ProviderClass.DETERMINISTIC_COMPILER: LocalityLevel.L0_DETERMINISTIC,
    ProviderClass.ALGORITHMIC: LocalityLevel.L1_ALGORITHMIC,
    ProviderClass.LOCAL_MODEL: LocalityLevel.L2_LOCAL_MODEL,
    ProviderClass.REMOTE_MODEL: LocalityLevel.L3_EXTERNAL_MODEL,
}


class TaskKind(str, enum.Enum):
    EXTRACTION = "extraction"
    SYNTHESIS = "synthesis"
    CLASSIFICATION = "classification"
    DIAGNOSIS = "diagnosis"
    EVALUATION = "evaluation"
    TRANSLATION = "translation"


class CapabilityDeclaration(BaseModel):
    """What a reasoning backend can do. The registry indexes on this.

    `metadata` carries topology facts (runtime, accelerator) as opaque
    provenance; the AIR core never interprets them.
    """

    model_config = ConfigDict(frozen=True)

    provider_id: str = Field(min_length=1)
    provider_class: ProviderClass
    task_kinds: list[TaskKind] = Field(min_length=1)
    output_schema_ids: list[str] = Field(default_factory=list)  # empty = any
    quality_profile: float = Field(default=0.5, ge=0.0, le=1.0)
    cost_profile: float = Field(default=0.5, ge=0.0, le=1.0)
    latency_profile: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def locality(self) -> LocalityLevel:
        return PROVIDER_CLASS_LOCALITY[self.provider_class]


class PrivacyClass(str, enum.Enum):
    INTERNAL = "internal"
    LOCAL_ONLY = "local_only"   # capped at L2 regardless of global policy


class IntelligenceTask(BaseModel):
    """A unit of reasoning addressed by capability, not by provider."""

    model_config = ConfigDict(frozen=True)

    task_kind: TaskKind
    task_label: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    output_schema_id: str = Field(min_length=1)
    decoding: DecodingParameters = Field(default_factory=DecodingParameters)
    model_hint: str | None = None
    subject_ref: str | None = None
    budget_tokens: int | None = Field(default=None, ge=1)
    privacy_class: PrivacyClass = PrivacyClass.INTERNAL
    #: In-process runtime context for schema validation. Deliberately
    #: excluded from the canonical signature: identity is output_schema_id.
    output_type: Any = None

    def signature(self) -> str:
        payload = {
            "task_kind": self.task_kind.value,
            "task_label": self.task_label,
            "prompt": self.prompt,
            "output_schema_id": self.output_schema_id,
            "decoding": self.decoding.model_dump(mode="json"),
            "model_hint": self.model_hint,
            "subject_ref": self.subject_ref,
            "budget_tokens": self.budget_tokens,
            "privacy_class": self.privacy_class.value,
        }
        return canonical_hash(payload)


class CascadeStepOutcome(str, enum.Enum):
    EXECUTED = "executed"
    FAILED = "failed"
    DEFLECTED = "deflected"   # a lower level already succeeded


class CascadeStep(BaseModel):
    provider_id: str
    provider_class: ProviderClass
    locality: LocalityLevel
    outcome: CascadeStepOutcome
    detail: str = ""


class IntelligenceResult(BaseModel):
    """Candidate output + provenance. Never an artifact by itself."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    output_payload: dict[str, Any]
    provider_id: str
    provider_class: ProviderClass
    locality: LocalityLevel
    model_record: ModelCallRecord
    cascade_path: list[CascadeStep] = Field(default_factory=list)
    #: Which routing policy served (and capped) this result. Audit trail
    #: for the Autonomy Certification.
    policy_name: str = ""
