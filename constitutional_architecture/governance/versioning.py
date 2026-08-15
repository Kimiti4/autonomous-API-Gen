"""Phase 28 - Constitutional versioning.

Append-only, strictly increasing version chain over ConstitutionVersionISR.
Ratification requires an approved VoteOutcome; every ratification emits a
ChangeLineageISR. Persistence is behind ConstitutionVersionRepository
(dependency inversion); the in-memory implementation is the reference adapter.
A durable adapter can be swapped in later without touching VersionManager.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from .audit import EvidenceLedger
from .schemas import (
    ChangeKind,
    ChangeLineageISR,
    ConstitutionVersionISR,
    VersionStatus,
    utcnow,
)
from .voting import VoteOutcome


_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


class VersioningError(RuntimeError):
    """Raised when a versioning invariant is violated."""


def parse_semver(value: str) -> tuple[int, int, int]:
    match = _SEMVER.match(value.strip())
    if match is None:
        raise VersioningError(f"invalid semver:{value!r}")
    return (int(match[1]), int(match[2]), int(match[3]))


class ConstitutionVersionRepository(Protocol):
    def add(self, version: ConstitutionVersionISR) -> None: ...
    def replace(self, version: ConstitutionVersionISR) -> None: ...
    def get(self, version_id: str) -> ConstitutionVersionISR | None: ...
    def all(self) -> list[ConstitutionVersionISR]: ...


class InMemoryConstitutionVersionRepository:
    """Reference implementation; suitable for tests and single-process use."""

    def __init__(self) -> None:
        self._versions: dict[str, ConstitutionVersionISR] = {}

    def add(self, version: ConstitutionVersionISR) -> None:
        if version.version_id in self._versions:
            raise VersioningError(f"duplicate_version_id:{version.version_id}")
        self._versions[version.version_id] = version

    def replace(self, version: ConstitutionVersionISR) -> None:
        if version.version_id not in self._versions:
            raise VersioningError(f"unknown_version_id:{version.version_id}")
        self._versions[version.version_id] = version

    def get(self, version_id: str) -> ConstitutionVersionISR | None:
        return self._versions.get(version_id)

    def all(self) -> list[ConstitutionVersionISR]:
        return list(self._versions.values())


class FileBackedConstitutionVersionRepository:
    """Durable ConstitutionVersionRepository: persists ConstitutionVersionISR
    versions as a JSON document (``{version_id: version}``) with atomic
    writes. Drop-in for InMemoryConstitutionVersionRepository -- same Protocol
    semantics (add raises on duplicate, replace raises on unknown) -- so the
    constitutional version chain (and therefore constitutional_currency /
    audit_integrity) is durable across process restarts. Swap it in at any
    caller that currently constructs ``InMemoryConstitutionVersionRepository``.
    """

    def __init__(
        self,
        path: "str | os.PathLike[str] | None" = None,
        *,
        file_name: str = "constitution_versions.json",
    ) -> None:
        root = Path(path) if path is not None else Path(tempfile.gettempdir()) / "constitution_version_repo"
        self._root = root
        self._file = root / file_name

    def _read(self) -> dict[str, dict]:
        if not self._file.exists():
            return {}
        try:
            with self._file.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            return dict(data) if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _write(self, data: dict[str, dict]) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        tmp = self._file.with_suffix(self._file.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, sort_keys=True, indent=2, default=str)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self._file)

    def add(self, version: ConstitutionVersionISR) -> None:
        data = self._read()
        if version.version_id in data:
            raise VersioningError(f"duplicate_version_id:{version.version_id}")
        data[version.version_id] = version.model_dump(mode="json")
        self._write(data)

    def replace(self, version: ConstitutionVersionISR) -> None:
        data = self._read()
        if version.version_id not in data:
            raise VersioningError(f"unknown_version_id:{version.version_id}")
        data[version.version_id] = version.model_dump(mode="json")
        self._write(data)

    def get(self, version_id: str) -> ConstitutionVersionISR | None:
        data = self._read()
        raw = data.get(version_id)
        return ConstitutionVersionISR.model_validate(raw) if raw is not None else None

    def all(self) -> list[ConstitutionVersionISR]:
        data = self._read()
        return [ConstitutionVersionISR.model_validate(raw) for raw in data.values()]


class VersionManager:
    """Manages the constitutional version chain.

    Invariants enforced:
      * semver strictly increases across all versions (proposed or ratified)
      * only PROPOSED versions may be ratified
      * ratification requires an approved VoteOutcome
      * at most one RATIFIED head; superseded heads become SUPERSEDED
      * every ratification emits a ChangeLineageISR
    """

    def __init__(
        self,
        repository: ConstitutionVersionRepository,
        evidence: EvidenceLedger | None = None,
    ) -> None:
        self._repo = repository
        self._evidence = evidence
        self._lineages: list[ChangeLineageISR] = []
        self._proposals: dict[str, tuple[ChangeKind, str]] = {}

    # -- commands ----------------------------------------------------------

    def propose(
        self,
        *,
        semver: str,
        policy_set_ref: str,
        proposed_by: str,
        change_kind: ChangeKind,
        summary: str,
        now: datetime,
    ) -> ConstitutionVersionISR:
        candidate = parse_semver(semver)
        for existing in self._repo.all():
            if candidate <= parse_semver(existing.semver):
                raise VersioningError(
                    f"semver_must_strictly_increase:{semver}<={existing.semver}"
                )
        head = self.current()
        version = ConstitutionVersionISR(
            version_id=f"cv-{uuid4().hex}",
            semver=semver,
            status=VersionStatus.PROPOSED,
            policy_set_ref=policy_set_ref,
            proposed_by=proposed_by,
            proposed_at=now,
            predecessor_ref=head.version_id if head else None,
        )
        self._repo.add(version)
        self._proposals[version.version_id] = (change_kind, summary)
        self._record(
            "version_proposed", version, now,
            {"change_kind": change_kind.value, "summary": summary},
        )
        return version

    def ratify(
        self,
        *,
        version_id: str,
        outcome: VoteOutcome,
        now: datetime,
    ) -> ConstitutionVersionISR:
        version = self._repo.get(version_id)
        if version is None:
            raise VersioningError(f"unknown_version_id:{version_id}")
        if version.status is not VersionStatus.PROPOSED:
            raise VersioningError(
                f"only_proposed_versions_can_be_ratified:{version.status.value}"
            )
        if not outcome.approved:
            raise VersioningError(f"ratification_requires_approved_vote:{outcome.reason}")

        change_kind, summary = self._proposals.get(version_id, (ChangeKind.AMENDMENT, ""))
        head = self.current()
        lineage = ChangeLineageISR(
            lineage_id=f"cl-{uuid4().hex}",
            change_kind=change_kind,
            parent_version_refs=[head.version_id] if head else [],
            authorizing_workflow_ref=outcome.workflow_ref,
            summary=summary or f"ratify {version.semver}",
            created_at=now,
        )
        self._lineages.append(lineage)

        ratified = version.model_copy(update={
            "status": VersionStatus.RATIFIED,
            "ratification_workflow_ref": outcome.workflow_ref,
            "lineage_ref": lineage.lineage_id,
            "effective_at": now,
        })
        self._repo.replace(ratified)
        if head is not None:
            self._repo.replace(head.model_copy(update={"status": VersionStatus.SUPERSEDED}))
        self._record("version_ratified", ratified, now, {"workflow_ref": outcome.workflow_ref})
        return ratified

    # -- queries -----------------------------------------------------------

    def current(self) -> ConstitutionVersionISR | None:
        ratified = [v for v in self._repo.all() if v.status is VersionStatus.RATIFIED]
        if not ratified:
            return None
        if len(ratified) > 1:
            raise VersioningError("multiple_ratified_heads_detected")
        return ratified[0]

    def history(self) -> tuple[ConstitutionVersionISR, ...]:
        return tuple(sorted(self._repo.all(), key=lambda v: parse_semver(v.semver)))

    def lineage(self) -> tuple[ChangeLineageISR, ...]:
        return tuple(self._lineages)

    # -- internals ---------------------------------------------------------

    def _record(self, event_kind: str, version: ConstitutionVersionISR, now: datetime, extra: dict) -> None:
        if self._evidence is None:
            return
        self._evidence.record(
            actor="version_manager",
            event_kind=event_kind,
            subject_ref=version.version_id,
            payload={"semver": version.semver, **extra},
            recorded_at=now,
        )
