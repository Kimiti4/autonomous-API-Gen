"""Durable orchestration run records (Checkpoint 055)."""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from certification.orchestration.contract import OrchestrationLifecycleState, assert_transition


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


@dataclass
class OrchestrationRunRecord:
    run_id: str
    workload_id: str
    candidate_id: str
    state: OrchestrationLifecycleState
    revision_id: str
    artifact_sha256: str
    isr_provenance: str
    transition_history: tuple[str, ...] = ()
    failure_reason: str = ""
    updated_at: str = ""
    created_at: str = ""

    def transition(self, nxt: OrchestrationLifecycleState, *, reason: str = "") -> None:
        assert_transition(self.state, nxt)
        prior = self.state
        self.state = nxt
        self.transition_history = self.transition_history + (f"{prior.value}->{nxt.value}",)
        if reason:
            self.failure_reason = reason
        self.updated_at = _utcnow()


class OrchestrationRunStore:
    """Filesystem-backed orchestration state for restart/recovery."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.runs_dir = self.root / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def save(self, record: OrchestrationRunRecord) -> None:
        path = self.runs_dir / f"{record.run_id}.json"
        payload = {
            "run_id": record.run_id,
            "workload_id": record.workload_id,
            "candidate_id": record.candidate_id,
            "state": record.state.value,
            "revision_id": record.revision_id,
            "artifact_sha256": record.artifact_sha256,
            "isr_provenance": record.isr_provenance,
            "transition_history": list(record.transition_history),
            "failure_reason": record.failure_reason,
            "updated_at": record.updated_at,
            "created_at": record.created_at,
        }
        fd, tmp = tempfile.mkstemp(dir=str(self.runs_dir), suffix=".part")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, sort_keys=True)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    def load(self, run_id: str) -> OrchestrationRunRecord | None:
        path = self.runs_dir / f"{run_id}.json"
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return OrchestrationRunRecord(
            run_id=data["run_id"],
            workload_id=data["workload_id"],
            candidate_id=data["candidate_id"],
            state=OrchestrationLifecycleState(data["state"]),
            revision_id=data["revision_id"],
            artifact_sha256=data["artifact_sha256"],
            isr_provenance=data["isr_provenance"],
            transition_history=tuple(data.get("transition_history", ())),
            failure_reason=data.get("failure_reason", ""),
            updated_at=data.get("updated_at", ""),
            created_at=data.get("created_at", ""),
        )

    def list_pending(self) -> list[OrchestrationRunRecord]:
        pending = {
            OrchestrationLifecycleState.AWAITING_GOVERNANCE,
            OrchestrationLifecycleState.PRODUCT_ACCEPTANCE_PENDING,
            OrchestrationLifecycleState.EVIDENCE_REGISTERING,
        }
        out: list[OrchestrationRunRecord] = []
        for path in sorted(self.runs_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            rec = self.load(str(data["run_id"]))
            if rec and rec.state in pending:
                out.append(rec)
        return out


def new_run_id() -> str:
    return f"orun-{uuid.uuid4().hex[:24]}"
