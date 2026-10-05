"""Cross-layer architectural consistency checks for ESAP Bucket 3.9.

This module compares a governed cross-layer model and detects missing,
stale, or mismatched links before a mutation is admitted. It is read-only:
finding consistency does not authorize implementation or certification.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Iterable, Literal

Layer = Literal[
    "requirement", "architecture", "api", "contract", "backend", "frontend",
    "test", "documentation", "deployment",
]

_VALID_LAYERS = {
    "requirement", "architecture", "api", "contract", "backend", "frontend",
    "test", "documentation", "deployment",
}


@dataclass(frozen=True)
class LayerArtifact:
    artifact_id: str
    layer: Layer
    requirement_ids: tuple[str, ...] = ()
    contract_ids: tuple[str, ...] = ()
    verification_ids: tuple[str, ...] = ()
    revision: str = ""

    def __post_init__(self) -> None:
        if not self.artifact_id.strip():
            raise ValueError("artifact-id-required")
        if self.layer not in _VALID_LAYERS:
            raise ValueError("invalid-layer")
        if len(set(self.requirement_ids)) != len(self.requirement_ids):
            raise ValueError("duplicate-requirement-link")
        if len(set(self.contract_ids)) != len(self.contract_ids):
            raise ValueError("duplicate-contract-link")
        if len(set(self.verification_ids)) != len(self.verification_ids):
            raise ValueError("duplicate-verification-link")


@dataclass(frozen=True)
class ConsistencyFinding:
    finding_id: str
    kind: str
    artifact_id: str
    related_id: str
    message: str
    blocking: bool = True


@dataclass(frozen=True)
class ConsistencyReport:
    project_id: str
    findings: tuple[ConsistencyFinding, ...]
    checked_artifact_ids: tuple[str, ...]
    digest: str

    @property
    def consistent(self) -> bool:
        return not any(f.blocking for f in self.findings)


class CrossLayerConsistencyEngine:
    """Deterministically detects drift in a supplied cross-layer model."""

    def __init__(self, *, project_id: str, artifacts: Iterable[LayerArtifact] = ()) -> None:
        if not project_id.strip():
            raise ValueError("project-id-required")
        self.project_id = project_id
        self._artifacts: dict[str, LayerArtifact] = {}
        for artifact in artifacts:
            self.add_artifact(artifact)

    def add_artifact(self, artifact: LayerArtifact) -> None:
        if artifact.artifact_id in self._artifacts:
            raise ValueError("duplicate-artifact-id")
        self._artifacts[artifact.artifact_id] = artifact

    def inspect(self) -> ConsistencyReport:
        findings: list[ConsistencyFinding] = []
        artifacts = self._artifacts

        def add(kind: str, artifact_id: str, related_id: str, message: str) -> None:
            raw = json.dumps(
                [self.project_id, kind, artifact_id, related_id, message],
                separators=(",", ":"),
            )
            finding_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
            findings.append(
                ConsistencyFinding(
                    finding_id=finding_id,
                    kind=kind,
                    artifact_id=artifact_id,
                    related_id=related_id,
                    message=message,
                )
            )

        # Every non-requirement artifact must retain a trace to at least one
        # requirement. Requirement artifacts are the authority roots.
        for artifact in artifacts.values():
            if artifact.layer != "requirement" and not artifact.requirement_ids:
                add(
                    "orphan-requirement-trace",
                    artifact.artifact_id,
                    "",
                    "artifact has no requirement trace",
                )

            for requirement_id in artifact.requirement_ids:
                target = artifacts.get(requirement_id)
                if target is None:
                    add(
                        "missing-requirement",
                        artifact.artifact_id,
                        requirement_id,
                        "requirement trace points to unknown artifact",
                    )
                elif target.layer != "requirement":
                    add(
                        "invalid-requirement-target",
                        artifact.artifact_id,
                        requirement_id,
                        "requirement trace does not target a requirement layer",
                    )

            for contract_id in artifact.contract_ids:
                target = artifacts.get(contract_id)
                if target is None:
                    add(
                        "missing-contract",
                        artifact.artifact_id,
                        contract_id,
                        "contract link points to unknown artifact",
                    )
                elif target.layer != "contract":
                    add(
                        "invalid-contract-target",
                        artifact.artifact_id,
                        contract_id,
                        "contract link does not target a contract layer",
                    )

        # API/backend/frontend artifacts that participate in a contract must
        # point to a contract. Tests must point to requirements as well.
        for artifact in artifacts.values():
            if artifact.layer in {"api", "backend", "frontend"} and not artifact.contract_ids:
                add(
                    "missing-cross-layer-contract",
                    artifact.artifact_id,
                    "",
                    "cross-layer implementation artifact has no contract trace",
                )
            if artifact.layer == "test" and not artifact.requirement_ids:
                add(
                    "untraced-verification",
                    artifact.artifact_id,
                    "",
                    "test artifact has no requirement trace",
                )

        ordered = tuple(sorted(
            findings,
            key=lambda f: (f.kind, f.artifact_id, f.related_id, f.finding_id),
        ))
        payload = {
            "schema_version": "esap.cross-layer-consistency.v1",
            "project_id": self.project_id,
            "artifacts": tuple(sorted(artifacts)),
            "findings": tuple(
                (f.finding_id, f.kind, f.artifact_id, f.related_id, f.message, f.blocking)
                for f in ordered
            ),
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return ConsistencyReport(
            project_id=self.project_id,
            findings=ordered,
            checked_artifact_ids=tuple(sorted(artifacts)),
            digest=digest,
        )
