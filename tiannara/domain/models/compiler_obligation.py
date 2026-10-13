"""Framework-neutral semantic obligation and conformance evidence contract."""
from __future__ import annotations

import hashlib
import json
import re
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class Applicability(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    NOT_APPLICABLE = "not_applicable"


class Disposition(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    BLOCKED_UNRESOLVED = "BLOCKED_UNRESOLVED"
    BLOCKED_NO_CONSUMER = "BLOCKED_NO_CONSUMER"
    UNSUPPORTED = "UNSUPPORTED"


class Strength(str, Enum):
    MUST = "MUST"
    SHOULD = "SHOULD"
    MAY = "MAY"


class EnforcementPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    kind: str = Field(min_length=1, max_length=128)
    locator: str = Field(min_length=1, max_length=512)


class ScenarioEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    scenario_id: str = Field(min_length=1, max_length=256)
    outcome: str = Field(pattern=r"^(PASS|FAIL|ERROR|NOT_RUN|INCONCLUSIVE)$")
    evidence_ref: str = Field(min_length=1, max_length=2048)
    evidence_sha256: str
    build_id: str = Field(min_length=1, max_length=256)
    environment_fingerprint: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def valid_evidence_hash(self):
        if not _SHA256.fullmatch(self.evidence_sha256):
            raise ValueError("evidence_sha256 must be lowercase SHA-256 hex")
        return self


class CompilerObligationRecord(BaseModel):
    """Immutable source-bound obligation; PASS requires executed evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    schema_version: str = Field(pattern=r"^1\.0$")
    obligation_id: str = Field(min_length=1, max_length=256)
    source_graph_id: str = Field(min_length=1, max_length=256)
    source_graph_hash: str
    domain: str = Field(min_length=1, max_length=128)
    statement: str = Field(min_length=1, max_length=4000)
    applicability: Applicability
    applicability_reason: str = Field(default="", max_length=2000)
    required_strength: Strength
    enforcement_points: tuple[EnforcementPoint, ...] = ()
    consumer_binding: str = Field(default="", max_length=512)
    acceptance_scenarios: tuple[ScenarioEvidence, ...] = ()
    disposition: Disposition = Disposition.UNKNOWN
    limitations: tuple[str, ...] = ()
    obligation_hash: str = ""

    def canonical_payload(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "obligation_id": self.obligation_id,
            "source_graph_id": self.source_graph_id,
            "source_graph_hash": self.source_graph_hash,
            "domain": self.domain,
            "statement": self.statement,
            "applicability": self.applicability.value,
            "applicability_reason": self.applicability_reason,
            "required_strength": self.required_strength.value,
            "consumer_binding": self.consumer_binding,
            "enforcement_points": [
                {"kind": point.kind, "locator": point.locator}
                for point in self.enforcement_points
            ],
            "limitations": list(self.limitations),
        }

    def compute_hash(self) -> str:
        data = json.dumps(self.canonical_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @model_validator(mode="after")
    def validate_record(self):
        if not _SHA256.fullmatch(self.source_graph_hash):
            raise ValueError("source_graph_hash must be lowercase SHA-256 hex")
        if self.applicability is Applicability.NOT_APPLICABLE:
            if not self.applicability_reason.strip() or self.disposition is not Disposition.NOT_APPLICABLE:
                raise ValueError("NOT_APPLICABLE requires a reason and matching disposition")
        elif self.disposition is Disposition.NOT_APPLICABLE:
            raise ValueError("NOT_APPLICABLE disposition requires not_applicable applicability")
        if self.disposition is Disposition.PASS:
            if self.applicability is not Applicability.REQUIRED:
                raise ValueError("only required obligations may be marked PASS")
            if not self.consumer_binding.strip() or not self.enforcement_points:
                raise ValueError("PASS requires a consumer binding and enforcement point")
            if not self.acceptance_scenarios:
                raise ValueError("PASS requires executed acceptance evidence")
            if any(s.outcome != "PASS" for s in self.acceptance_scenarios):
                raise ValueError("PASS requires every listed scenario to pass")
        expected = self.compute_hash()
        if self.obligation_hash and self.obligation_hash != expected:
            raise ValueError("obligation_hash does not match canonical content")
        if not self.obligation_hash:
            object.__setattr__(self, "obligation_hash", expected)
        return self
