"""Fail-closed reader for immutable trial inputs.

Generation code must use the returned snapshot paths, never reconstruct paths
under the mutable checkout. This module intentionally does not read source
inputs after snapshot capture.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class SnapshotConsumptionError(RuntimeError):
    """Raised when the immutable snapshot cannot be trusted."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _child(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise SnapshotConsumptionError("snapshot path must be a non-empty string")
    rel = Path(relative)
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
        raise SnapshotConsumptionError("unsafe relative path in snapshot manifest")
    resolved_root = root.resolve(strict=True)
    candidate = (resolved_root / rel).resolve(strict=True)
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise SnapshotConsumptionError("snapshot path escapes evidence directory") from exc
    if not candidate.is_file():
        raise SnapshotConsumptionError("snapshot input is not a regular file")
    return candidate


def load_snapshot_inputs(evidence_dir: Path) -> dict[str, Any]:
    """Return verified snapshot metadata and immutable input paths.

    Returned paths are all beneath evidence_dir. No mutable source paths are
    returned or read, so callers can safely feed these paths to generation.
    """
    evidence = evidence_dir.resolve(strict=True)
    try:
        manifest = json.loads((evidence / "snapshot.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SnapshotConsumptionError("snapshot manifest missing or invalid") from exc
    if not isinstance(manifest, dict) or manifest.get("schema") != "tiannara.trial-input-snapshot.v1":
        raise SnapshotConsumptionError("unsupported snapshot manifest schema")
    contract_hash = manifest.get("contract_sha256")
    if not isinstance(contract_hash, str) or len(contract_hash) != 64:
        raise SnapshotConsumptionError("invalid contract hash in manifest")
    contract_path = _child(evidence, manifest.get("contract_snapshot_path", ""))
    if _sha256(contract_path) != contract_hash:
        raise SnapshotConsumptionError("contract snapshot hash mismatch")
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SnapshotConsumptionError("contract snapshot invalid JSON") from exc
    declared = contract.get("generator_inputs")
    entries = manifest.get("inputs")
    forbidden = contract.get("forbidden_inputs", [])
    if not isinstance(declared, list) or not declared or not isinstance(entries, list):
        raise SnapshotConsumptionError("contract or manifest input declarations invalid")
    if not isinstance(forbidden, list):
        raise SnapshotConsumptionError("forbidden_inputs must be a list")
    forbidden_paths = {
        Path(item).as_posix().rstrip("/")
        for item in forbidden
        if isinstance(item, str)
    }
    inputs: dict[str, Path] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise SnapshotConsumptionError("invalid input entry")
        rel = entry.get("path")
        digest = entry.get("sha256")
        if not isinstance(rel, str) or not isinstance(digest, str) or len(digest) != 64:
            raise SnapshotConsumptionError("invalid input path or hash")
        normalized = Path(rel).as_posix()
        if normalized in inputs:
            raise SnapshotConsumptionError("duplicate snapshot input")
        if any(normalized == item or normalized.startswith(item + "/") for item in forbidden_paths):
            raise SnapshotConsumptionError(f"forbidden input in snapshot: {normalized}")
        snapshot_path = _child(evidence, entry.get("snapshot_path", ""))
        if _sha256(snapshot_path) != digest:
            raise SnapshotConsumptionError(f"snapshot input hash mismatch: {normalized}")
        inputs[normalized] = snapshot_path
    normalized_declared = {
        Path(item).as_posix() for item in declared if isinstance(item, str)
    }
    if len(normalized_declared) != len(declared) or normalized_declared != set(inputs):
        raise SnapshotConsumptionError("manifest inputs do not exactly match contract")
    return {
        "contract": contract,
        "contract_sha256": contract_hash,
        "inputs": inputs,
        "evidence_dir": evidence,
    }
