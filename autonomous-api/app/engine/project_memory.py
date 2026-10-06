"""Long-lived, evidence-bounded project memory for ESAP.

Memory is append-only and content-addressed. It preserves requirements, decisions,
constraints, observations, certifications, outcomes and advisory lessons without
allowing advisory material to masquerade as project truth.

The store is deliberately technology-neutral: callers choose where the JSONL file
lives. Every record links to the previous digest. Loading validates the complete
chain and fails closed on malformed, reordered, duplicated, or tampered records.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable, Literal, Mapping

MemoryKind = Literal[
    "requirement", "decision", "constraint", "observation",
    "certification", "outcome", "advisory",
]
MemoryStatus = Literal["authoritative", "certified", "observed", "advisory"]

_KINDS = {"requirement", "decision", "constraint", "observation", "certification", "outcome", "advisory"}
_STATUSES = {"authoritative", "certified", "observed", "advisory"}


@dataclass(frozen=True)
class ProjectMemory:
    memory_id: str
    project_id: str
    kind: MemoryKind
    statement: str
    status: MemoryStatus
    source: str
    evidence: tuple[str, ...] = ()
    supersedes: str | None = None
    parent_digest: str | None = None
    digest: str = ""
    schema_version: str = "esap.project-memory.v1"

    def canonical_payload(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "memory_id": self.memory_id,
            "project_id": self.project_id,
            "kind": self.kind,
            "statement": self.statement,
            "status": self.status,
            "source": self.source,
            "evidence": list(self.evidence),
            "supersedes": self.supersedes,
            "parent_digest": self.parent_digest,
        }

    def verify_digest(self) -> bool:
        return self.digest == _digest(self.canonical_payload())

    def to_json(self) -> str:
        return json.dumps(
            {**self.canonical_payload(), "digest": self.digest},
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        kind: MemoryKind,
        statement: str,
        status: MemoryStatus,
        source: str,
        evidence: Iterable[str] = (),
        supersedes: str | None = None,
        parent_digest: str | None = None,
    ) -> "ProjectMemory":
        if not project_id.strip() or not statement.strip() or not source.strip():
            raise ValueError("memory-requires-project-statement-and-source")
        if kind not in _KINDS:
            raise ValueError("invalid-memory-kind")
        if status not in _STATUSES:
            raise ValueError("invalid-memory-status")

        evidence_tuple = tuple(sorted(set(evidence)))
        if status in {"certified", "observed"} and not evidence_tuple:
            raise ValueError("verified-memory-requires-evidence")
        if status == "advisory" and kind != "advisory":
            raise ValueError("advisory-status-requires-advisory-kind")
        if status == "certified" and kind != "certification":
            raise ValueError("certified-status-requires-certification-kind")

        payload = {
            "schema_version": "esap.project-memory.v1",
            "project_id": project_id,
            "kind": kind,
            "statement": statement,
            "status": status,
            "source": source,
            "evidence": list(evidence_tuple),
            "supersedes": supersedes,
            "parent_digest": parent_digest,
        }
        memory_id = _digest(payload)[:16]
        full_payload = {**payload, "memory_id": memory_id}
        return cls(**full_payload, digest=_digest(full_payload), schema_version="esap.project-memory.v1")


class ProjectMemoryStore:
    """Append-only project memory with deterministic, tamper-evident persistence."""

    def __init__(self, entries: Iterable[ProjectMemory] = ()) -> None:
        self._entries: list[ProjectMemory] = []
        self._by_id: dict[str, ProjectMemory] = {}
        self._by_digest: dict[str, ProjectMemory] = {}
        for entry in entries:
            self._append(entry, validate_parent=True)

    @property
    def entries(self) -> tuple[ProjectMemory, ...]:
        return tuple(self._entries)

    @property
    def head_digest(self) -> str | None:
        return self._entries[-1].digest if self._entries else None

    def append(self, entry: ProjectMemory) -> ProjectMemory:
        if entry.parent_digest != self.head_digest:
            raise ValueError("memory-parent-digest-mismatch")
        return self._append(entry, validate_parent=False)

    def supersede(
        self,
        previous: ProjectMemory,
        *,
        statement: str,
        source: str,
        status: MemoryStatus,
        evidence: Iterable[str] = (),
    ) -> ProjectMemory:
        if previous.memory_id not in self._by_id:
            raise ValueError("cannot-supersede-unknown-memory")
        entry = ProjectMemory.create(
            project_id=previous.project_id,
            kind=previous.kind,
            statement=statement,
            status=status,
            source=source,
            evidence=evidence,
            supersedes=previous.memory_id,
            parent_digest=self.head_digest,
        )
        return self.append(entry)

    def current(self, *, include_advisory: bool = False) -> tuple[ProjectMemory, ...]:
        superseded = {e.supersedes for e in self._entries if e.supersedes}
        return tuple(
            e for e in self._entries
            if e.memory_id not in superseded
            and (include_advisory or e.status != "advisory")
        )

    def context(self, *, include_advisory: bool = False) -> dict[str, tuple[ProjectMemory, ...]]:
        """Separate truth channels so advisory lessons cannot become project requirements."""
        current = self.current(include_advisory=include_advisory)
        return {
            "authoritative": tuple(e for e in current if e.status == "authoritative"),
            "certified": tuple(e for e in current if e.status == "certified"),
            "observed": tuple(e for e in current if e.status == "observed"),
            "advisory": tuple(e for e in current if e.status == "advisory"),
        }

    def find(self, memory_id: str) -> ProjectMemory | None:
        return self._by_id.get(memory_id)

    def persist(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".tmp")
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                for entry in self._entries:
                    handle.write(entry.to_json() + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()

    @classmethod
    def load(cls, path: str | Path) -> "ProjectMemoryStore":
        target = Path(path)
        if not target.exists():
            return cls()
        entries: list[ProjectMemory] = []
        with target.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    raw = json.loads(line)
                    if not isinstance(raw, dict):
                        raise TypeError("record-is-not-an-object")
                    digest = raw.pop("digest")
                    raw["evidence"] = tuple(raw["evidence"])
                    entry = ProjectMemory(**raw, digest=digest)
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(f"invalid-memory-record:{line_number}") from exc
                entries.append(entry)
        return cls(entries)

    def _append(self, entry: ProjectMemory, *, validate_parent: bool) -> ProjectMemory:
        if not entry.verify_digest():
            raise ValueError("memory-digest-invalid")
        if entry.memory_id in self._by_id:
            raise ValueError("duplicate-memory-id")
        if entry.digest in self._by_digest:
            raise ValueError("duplicate-memory-digest")
        if validate_parent and entry.parent_digest != self.head_digest:
            raise ValueError("memory-chain-broken")
        if entry.supersedes and entry.supersedes not in self._by_id:
            raise ValueError("supersedes-unknown-memory")
        if self._entries and entry.project_id != self._entries[0].project_id:
            raise ValueError("memory-store-project-mismatch")
        self._entries.append(entry)
        self._by_id[entry.memory_id] = entry
        self._by_digest[entry.digest] = entry
        return entry


def _digest(payload: Mapping) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()
