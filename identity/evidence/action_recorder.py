"""Action recorder — project AutonomousActionRecord to v1.1 evidence format."""
from __future__ import annotations
import hashlib
from pydantic import BaseModel, ConfigDict
from identity.core.autonomous_action import AutonomousActionRecord


class ActionEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidenceId: str
    evidenceType: str
    producedBy: str
    producedAt: str
    subjectRef: str
    summary: str
    contentHash: str


def project_action_to_v11_evidence(rec: AutonomousActionRecord) -> ActionEvidence:
    canonical = f"{rec.action_id}:{rec.principal_id}:{rec.capability}:{rec.result}"
    content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return ActionEvidence(
        evidenceId=f"autonomous-action:{rec.action_id}",
        evidenceType="autonomous-action",
        producedBy=f"identity:{rec.actor}",
        producedAt=rec.timestamp,
        subjectRef=rec.isr_revision_id or "",
        summary=f"{rec.capability} -> {rec.result}",
        contentHash=content_hash,
    )
