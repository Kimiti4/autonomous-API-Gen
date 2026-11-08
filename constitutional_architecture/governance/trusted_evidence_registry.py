"""Trusted immutable evidence registry (FS00-FS-039 foundation).

Callers must not invent ``evidence_id`` or ``record_hash``: only registration
through :meth:`TrustedEvidenceRegistry.register` produces ledger-backed
identifiers. Free-form strings in repair reports or APIs are not treated as
trusted evidence unless they resolve to a record in this registry.

Each line in the JSONL store is an append-only event with a SHA-256 hash chain
(prev_hash -> record_hash), matching the pattern used by
``certification/governance/registry.py`` and ``certification/evidence/ledger.py``.

Schema identity: ``tiannara.governance.trusted_evidence`` / ``1.0.0``.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import hashlib
import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

try:
    import fcntl  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore[assignment]

try:
    import msvcrt  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - non-Windows
    msvcrt = None  # type: ignore[assignment]

SCHEMA_ID = "tiannara.governance.trusted_evidence"
SCHEMA_VERSION = "1.0.0"
GENESIS_HASH = "0" * 64

# Hash-chained JSONL is tamper-evident, not independently authentic — see
# ``trusted_evidence_resolution`` module documentation.


@contextlib.contextmanager
def _append_lock(path: Path) -> Iterator[None]:
    """Serialize append operations (best-effort; not a distributed lock)."""
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lockf:
        if fcntl is not None:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
        elif msvcrt is not None and sys.platform == "win32":
            lockf.seek(0)
            msvcrt.locking(lockf.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)
            elif msvcrt is not None and sys.platform == "win32":
                lockf.seek(0)
                msvcrt.locking(lockf.fileno(), msvcrt.LK_UNLCK, 1)


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _utcnow_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class TrustedEvidenceRecord:
    """Content-addressed evidence row (before chain metadata).

    ``evidence_id`` is assigned by the registry at registration time.
    """

    evidence_id: str
    candidate_id: str
    evolution_run_id: str = ""
    generation_id: str = ""
    source_revision: str = ""
    source_tree_digest: str = ""
    artifact_manifest_digest: str = ""
    artifact_sha256: str = ""
    compiler_id: str = ""
    compiler_version: str = ""
    backend_id: str = ""
    backend_version: str = ""
    target_platform: str = ""
    compilation_result: str = ""
    build_result: str = ""
    static_analysis_result: str = ""
    security_scan_result: str = ""
    test_execution_results: str = ""
    runtime_verification_results: str = ""
    evaluation_mode: str = ""
    verifier_identity: str = ""
    verification_environment: str = ""
    captured_at: str = ""
    evidence_provenance: Mapping[str, Any] = field(default_factory=dict)
    evidence_status: str = "active"
    revocation_reason: str = ""
    expires_at: str = ""
    schema_id: str = SCHEMA_ID
    schema_version: str = SCHEMA_VERSION
    prev_hash: str = GENESIS_HASH
    record_hash: str = ""

    def content_dict(self) -> dict[str, Any]:
        """Payload hashed for ``record_hash`` (excludes chain fields)."""
        d = asdict(self)
        d.pop("prev_hash", None)
        d.pop("record_hash", None)
        return d


def _chain_hash(content: Mapping[str, Any], prev_hash: str) -> str:
    body = {k: v for k, v in content.items() if k not in ("prev_hash", "record_hash")}
    body["prev_hash"] = prev_hash
    return _sha256_hex(_canonical(body).encode("utf-8"))


class TrustedEvidenceRegistry:
    """Append-only trusted evidence store backed by a JSONL file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _tail_hash(self) -> str:
        try:
            last: dict[str, Any] | None = None
            with self.path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        last = json.loads(line)
            return str(last["record_hash"]) if last else GENESIS_HASH
        except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError):
            return GENESIS_HASH

    def known_evidence_ids(self) -> frozenset[str]:
        """Every ``evidence_id`` observed in the ledger (append-only)."""
        ids: set[str] = set()
        try:
            with self.path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    rec = entry.get("record") or {}
                    eid = rec.get("evidence_id")
                    if isinstance(eid, str) and eid.strip():
                        ids.add(eid.strip())
        except FileNotFoundError:
            pass
        return frozenset(ids)

    def register(
        self,
        *,
        candidate_id: str,
        evolution_run_id: str = "",
        generation_id: str = "",
        source_revision: str = "",
        source_tree_digest: str = "",
        artifact_manifest_digest: str = "",
        artifact_sha256: str = "",
        compiler_id: str = "",
        compiler_version: str = "",
        backend_id: str = "",
        backend_version: str = "",
        target_platform: str = "",
        compilation_result: str = "",
        build_result: str = "",
        static_analysis_result: str = "",
        security_scan_result: str = "",
        test_execution_results: str = "",
        runtime_verification_results: str = "",
        evaluation_mode: str = "",
        verifier_identity: str = "",
        verification_environment: str = "",
        captured_at: str | None = None,
        evidence_provenance: Mapping[str, Any] | None = None,
        evidence_status: str = "active",
        expires_at: str = "",
        evidence_id: str | None = None,
    ) -> TrustedEvidenceRecord:
        """Append one trusted evidence record. IDs and hashes are registry-owned."""
        with _append_lock(self.path):
            return self._register_locked(
                candidate_id=candidate_id,
                evolution_run_id=evolution_run_id,
                generation_id=generation_id,
                source_revision=source_revision,
                source_tree_digest=source_tree_digest,
                artifact_manifest_digest=artifact_manifest_digest,
                artifact_sha256=artifact_sha256,
                compiler_id=compiler_id,
                compiler_version=compiler_version,
                backend_id=backend_id,
                backend_version=backend_version,
                target_platform=target_platform,
                compilation_result=compilation_result,
                build_result=build_result,
                static_analysis_result=static_analysis_result,
                security_scan_result=security_scan_result,
                test_execution_results=test_execution_results,
                runtime_verification_results=runtime_verification_results,
                evaluation_mode=evaluation_mode,
                verifier_identity=verifier_identity,
                verification_environment=verification_environment,
                captured_at=captured_at,
                evidence_provenance=evidence_provenance,
                evidence_status=evidence_status,
                expires_at=expires_at,
                evidence_id=evidence_id,
            )

    def _register_locked(
        self,
        *,
        candidate_id: str,
        evolution_run_id: str = "",
        generation_id: str = "",
        source_revision: str = "",
        source_tree_digest: str = "",
        artifact_manifest_digest: str = "",
        artifact_sha256: str = "",
        compiler_id: str = "",
        compiler_version: str = "",
        backend_id: str = "",
        backend_version: str = "",
        target_platform: str = "",
        compilation_result: str = "",
        build_result: str = "",
        static_analysis_result: str = "",
        security_scan_result: str = "",
        test_execution_results: str = "",
        runtime_verification_results: str = "",
        evaluation_mode: str = "",
        verifier_identity: str = "",
        verification_environment: str = "",
        captured_at: str | None = None,
        evidence_provenance: Mapping[str, Any] | None = None,
        evidence_status: str = "active",
        expires_at: str = "",
        evidence_id: str | None = None,
    ) -> TrustedEvidenceRecord:
        prev = self._tail_hash()
        eid = evidence_id or f"tev-{uuid.uuid4().hex}"
        if eid in self.known_evidence_ids():
            raise ValueError(f"trusted-evidence-duplicate-id:{eid}")
        cap = captured_at or _utcnow_iso()
        rec = TrustedEvidenceRecord(
            evidence_id=eid,
            candidate_id=candidate_id,
            evolution_run_id=evolution_run_id,
            generation_id=generation_id,
            source_revision=source_revision,
            source_tree_digest=source_tree_digest,
            artifact_manifest_digest=artifact_manifest_digest,
            artifact_sha256=artifact_sha256,
            compiler_id=compiler_id,
            compiler_version=compiler_version,
            backend_id=backend_id,
            backend_version=backend_version,
            target_platform=target_platform,
            compilation_result=compilation_result,
            build_result=build_result,
            static_analysis_result=static_analysis_result,
            security_scan_result=security_scan_result,
            test_execution_results=test_execution_results,
            runtime_verification_results=runtime_verification_results,
            evaluation_mode=evaluation_mode,
            verifier_identity=verifier_identity,
            verification_environment=verification_environment,
            captured_at=cap,
            evidence_provenance=dict(evidence_provenance or {}),
            evidence_status=evidence_status,
            expires_at=expires_at,
            prev_hash=prev,
            record_hash="",
        )
        content = rec.content_dict()
        rhash = _chain_hash(content, prev)
        stored = TrustedEvidenceRecord(**{**content, "prev_hash": prev, "record_hash": rhash})
        inner = stored.content_dict() | {"prev_hash": prev, "record_hash": rhash}
        entry = {
            "prev_hash": prev,
            "record_hash": rhash,
            "record": inner,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(_canonical(entry) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return stored

    def verify_ledger_integrity(self) -> tuple[bool, str]:
        """Verify hash chain, line integrity, and reject duplicate evidence ids."""
        if not self.path.exists():
            return True, "empty"
        if not TrustedEvidenceRegistry.verify_chain(self.path):
            return False, "chain_broken"
        seen: set[str] = set()
        try:
            with self.path.open(encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    raw = line.rstrip("\n")
                    if not raw.strip():
                        continue
                    try:
                        entry = json.loads(raw)
                    except json.JSONDecodeError:
                        return False, f"malformed_line:{lineno}"
                    if not isinstance(entry.get("record"), dict):
                        return False, f"missing_record:{lineno}"
                    eid = entry["record"].get("evidence_id")
                    if not isinstance(eid, str) or not eid.strip():
                        return False, f"missing_evidence_id:{lineno}"
                    if eid in seen:
                        return False, f"duplicate_evidence_id:{eid}"
                    seen.add(eid)
        except OSError as exc:
            return False, f"read_error:{exc}"
        return True, "ok"

    def get(self, evidence_id: str) -> TrustedEvidenceRecord | None:
        """Return the latest row for ``evidence_id`` or None."""
        latest: TrustedEvidenceRecord | None = None
        try:
            with self.path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    rec = entry.get("record") or {}
                    if rec.get("evidence_id") != evidence_id:
                        continue
                    latest = _record_from_dict(rec)
        except FileNotFoundError:
            return None
        return latest

    def require_resolved(
        self,
        evidence_ids: Iterable[str],
        *,
        candidate_id: str,
        require_runtime: bool = True,
    ) -> tuple[TrustedEvidenceRecord, ...]:
        """Fail closed unless every id exists, matches candidate, and is active."""
        out: list[TrustedEvidenceRecord] = []
        for eid in evidence_ids:
            eid = str(eid).strip()
            if not eid:
                raise ValueError("trusted-evidence-missing-id")
            rec = self.get(eid)
            if rec is None:
                raise ValueError(f"trusted-evidence-unknown:{eid}")
            if rec.candidate_id != candidate_id:
                raise ValueError(f"trusted-evidence-candidate-mismatch:{eid}")
            if rec.evidence_status != "active":
                raise ValueError(f"trusted-evidence-not-active:{eid}:{rec.evidence_status}")
            if rec.expires_at:
                try:
                    exp = _dt.datetime.fromisoformat(rec.expires_at.replace("Z", "+00:00"))
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=_dt.timezone.utc)
                    if _dt.datetime.now(_dt.timezone.utc) > exp:
                        raise ValueError(f"trusted-evidence-expired:{eid}")
                except ValueError as exc:
                    if str(exc).startswith("trusted-evidence-expired"):
                        raise
                    raise ValueError(f"trusted-evidence-bad-expiry:{eid}") from exc
            if require_runtime and not str(rec.runtime_verification_results or "").strip():
                raise ValueError(f"trusted-evidence-runtime-missing:{eid}")
            out.append(rec)
        return tuple(out)

    @staticmethod
    def verify_chain(path: str | Path) -> bool:
        """Verify the full hash chain; False on any parse or link failure."""
        p = Path(path)
        prev = GENESIS_HASH
        try:
            with p.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        return False
                    if entry.get("prev_hash") != prev:
                        return False
                    rec = entry.get("record")
                    if not isinstance(rec, dict):
                        return False
                    body = {k: v for k, v in rec.items() if k not in ("prev_hash", "record_hash")}
                    body["prev_hash"] = prev
                    expected = _sha256_hex(_canonical(body).encode("utf-8"))
                    if entry.get("record_hash") != expected:
                        return False
                    prev = str(entry["record_hash"])
        except FileNotFoundError:
            return True
        return True


def _record_from_dict(rec: Mapping[str, Any]) -> TrustedEvidenceRecord:
    """Construct :class:`TrustedEvidenceRecord` from JSON ``record`` object."""
    return TrustedEvidenceRecord(
        evidence_id=str(rec["evidence_id"]),
        candidate_id=str(rec["candidate_id"]),
        evolution_run_id=str(rec.get("evolution_run_id", "") or ""),
        generation_id=str(rec.get("generation_id", "") or ""),
        source_revision=str(rec.get("source_revision", "") or ""),
        source_tree_digest=str(rec.get("source_tree_digest", "") or ""),
        artifact_manifest_digest=str(rec.get("artifact_manifest_digest", "") or ""),
        artifact_sha256=str(rec.get("artifact_sha256", "") or ""),
        compiler_id=str(rec.get("compiler_id", "") or ""),
        compiler_version=str(rec.get("compiler_version", "") or ""),
        backend_id=str(rec.get("backend_id", "") or ""),
        backend_version=str(rec.get("backend_version", "") or ""),
        target_platform=str(rec.get("target_platform", "") or ""),
        compilation_result=str(rec.get("compilation_result", "") or ""),
        build_result=str(rec.get("build_result", "") or ""),
        static_analysis_result=str(rec.get("static_analysis_result", "") or ""),
        security_scan_result=str(rec.get("security_scan_result", "") or ""),
        test_execution_results=str(rec.get("test_execution_results", "") or ""),
        runtime_verification_results=str(rec.get("runtime_verification_results", "") or ""),
        evaluation_mode=str(rec.get("evaluation_mode", "") or ""),
        verifier_identity=str(rec.get("verifier_identity", "") or ""),
        verification_environment=str(rec.get("verification_environment", "") or ""),
        captured_at=str(rec.get("captured_at", "") or ""),
        evidence_provenance=dict(rec.get("evidence_provenance") or {}),
        evidence_status=str(rec.get("evidence_status", "active") or "active"),
        revocation_reason=str(rec.get("revocation_reason", "") or ""),
        expires_at=str(rec.get("expires_at", "") or ""),
        schema_id=str(rec.get("schema_id", SCHEMA_ID)),
        schema_version=str(rec.get("schema_version", SCHEMA_VERSION)),
        prev_hash=str(rec.get("prev_hash", GENESIS_HASH)),
        record_hash=str(rec.get("record_hash", "") or ""),
    )
