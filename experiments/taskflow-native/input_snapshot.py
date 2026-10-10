"""Immutable, fail-closed snapshots for generation-trial inputs.

The generation runner must consume the copied input files in the snapshot,
not reopen mutable source paths after capture. The verifier distinguishes
snapshot integrity from whether the original workspace files changed later.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

SCHEMA = "tiannara.trial-input-snapshot.v1"
CONTRACT_NAME = "TRIAL_CONTRACT.json"


class SnapshotError(RuntimeError):
    """Raised when the contract or an input cannot be safely snapshotted."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _safe_relative_file(root: Path, raw_path: str) -> tuple[Path, str]:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise SnapshotError("input path must be a non-empty string")
    rel = Path(raw_path)
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
        raise SnapshotError(f"unsafe relative input path: {raw_path!r}")
    candidate = (root / rel).resolve(strict=True)
    if not _inside(root.resolve(), candidate):
        raise SnapshotError(f"input path escapes trial root: {raw_path!r}")
    if not candidate.is_file():
        raise SnapshotError(f"declared input is not a regular file: {raw_path!r}")
    return candidate, rel.as_posix()


def capture_snapshot(
    trial_dir: Path,
    evidence_dir: Path,
    contract_name: str = CONTRACT_NAME,
) -> dict[str, Any]:
    """Snapshot contract bytes and every declared generator input atomically enough
    for a single CI job. Writes only beneath evidence_dir.
    """
    root = trial_dir.resolve(strict=True)
    contract_path, contract_rel = _safe_relative_file(root, contract_name)
    try:
        contract_bytes = contract_path.read_bytes()
        contract = json.loads(contract_bytes)
    except (OSError, ValueError) as exc:
        raise SnapshotError("contract is missing or invalid JSON") from exc

    declared = contract.get("generator_inputs")
    if not isinstance(declared, list) or not declared:
        raise SnapshotError("contract must declare a non-empty generator_inputs list")
    forbidden = contract.get("forbidden_inputs", [])
    if not isinstance(forbidden, list):
        raise SnapshotError("forbidden_inputs must be a list")
    forbidden_norm = {Path(item).as_posix().rstrip("/") for item in forbidden if isinstance(item, str)}

    evidence_dir = evidence_dir.resolve()
    if not _inside(root, evidence_dir):
        raise SnapshotError("evidence directory must be inside the trial root")
    if evidence_dir == root:
        raise SnapshotError("evidence directory cannot be the trial root")

    staged = evidence_dir.with_name(evidence_dir.name + ".staging")
    if staged.exists():
        shutil.rmtree(staged)
    staged.mkdir(parents=True)
    try:
        (staged / "inputs").mkdir()
        contract_copy = staged / "contract.snapshot.json"
        contract_copy.write_bytes(contract_bytes)
        entries = []
        seen = set()
        for raw in declared:
            source, rel = _safe_relative_file(root, raw)
            if rel in seen:
                raise SnapshotError(f"duplicate generator input: {rel}")
            seen.add(rel)
            if any(rel == item or rel.startswith(item + "/") for item in forbidden_norm):
                raise SnapshotError(f"declared input is forbidden: {rel}")
            destination = staged / "inputs" / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            entries.append({
                "path": rel,
                "snapshot_path": destination.relative_to(staged).as_posix(),
                "sha256": sha256_file(destination),
            })
        manifest = {
            "schema": SCHEMA,
            "contract_path": contract_rel,
            "contract_sha256": sha256_bytes(contract_bytes),
            "contract_snapshot_path": "contract.snapshot.json",
            "inputs": sorted(entries, key=lambda item: item["path"]),
        }
        (staged / "snapshot.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if evidence_dir.exists():
            shutil.rmtree(evidence_dir)
        staged.replace(evidence_dir)
        return manifest
    except Exception:
        shutil.rmtree(staged, ignore_errors=True)
        raise


def _safe_child(root: Path, raw_path: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise SnapshotError("manifest path must be a non-empty string")
    rel = Path(raw_path)
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
        raise SnapshotError("unsafe path in snapshot manifest")
    candidate = (root / rel).resolve(strict=False)
    if not _inside(root.resolve(), candidate):
        raise SnapshotError("snapshot manifest path escapes its root")
    return candidate


def verify_snapshot(trial_dir: Path, evidence_dir: Path) -> dict[str, Any]:
    root = trial_dir.resolve(strict=True)
    evidence = evidence_dir.resolve(strict=True)
    if not _inside(root, evidence) or evidence == root:
        raise SnapshotError("evidence directory must be inside the trial root")
    try:
        manifest = json.loads((evidence / "snapshot.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SnapshotError("snapshot manifest is missing or invalid") from exc
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise SnapshotError("unsupported snapshot schema")
    entries = manifest.get("inputs")
    if not isinstance(entries, list) or not isinstance(manifest.get("contract_sha256"), str):
        raise SnapshotError("snapshot manifest has invalid structure")

    issues = []
    contract_copy = _safe_child(evidence, manifest.get("contract_snapshot_path", ""))
    if not contract_copy.is_file() or sha256_file(contract_copy) != manifest["contract_sha256"]:
        issues.append("contract_snapshot_integrity")
    try:
        contract_rel = manifest.get("contract_path", CONTRACT_NAME)
        source_contract, _ = _safe_relative_file(root, contract_rel)
    except (SnapshotError, OSError):
        source_contract = None
        issues.append("source_contract_changed")
    if source_contract is not None and sha256_file(source_contract) != manifest["contract_sha256"]:
        issues.append("source_contract_changed")

    try:
        snap_contract = json.loads(contract_copy.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        snap_contract = None
    if not isinstance(snap_contract, dict):
        issues.append("contract_snapshot_invalid")
        declared = []
        forbidden = []
    else:
        declared = snap_contract.get("generator_inputs")
        forbidden = snap_contract.get("forbidden_inputs", [])
        if not isinstance(declared, list) or not declared or not isinstance(forbidden, list):
            issues.append("contract_snapshot_declarations_invalid")
            declared, forbidden = [], []

    seen = set()
    recorded = set()
    forbidden_norm = {
        Path(item).as_posix().rstrip("/") for item in forbidden if isinstance(item, str)
    }
    for item in entries:
        if not isinstance(item, dict):
            raise SnapshotError("snapshot input entry has invalid structure")
        rel = item.get("path", "")
        digest = item.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            raise SnapshotError("snapshot input entry has invalid hash")
        source, normalized = _safe_relative_file(root, rel)
        if normalized in seen:
            raise SnapshotError("duplicate path in snapshot manifest")
        seen.add(normalized)
        recorded.add(normalized)
        if any(normalized == item or normalized.startswith(item + "/") for item in forbidden_norm):
            issues.append(f"forbidden_input_recorded:{normalized}")
        snapshot_path = _safe_child(evidence, item.get("snapshot_path", ""))
        if not _inside(evidence.resolve(), snapshot_path.resolve(strict=False)):
            raise SnapshotError("snapshot input escapes evidence directory")
        if not snapshot_path.is_file() or sha256_file(snapshot_path) != digest:
            issues.append(f"snapshot_input_integrity:{normalized}")
        if sha256_file(source) != digest:
            issues.append(f"source_input_changed:{normalized}")

    normalized_declared = set()
    for raw in declared:
        _, rel = _safe_relative_file(root, raw)
        normalized_declared.add(rel)
    if normalized_declared != recorded:
        issues.append("manifest_inputs_do_not_match_contract")

    return {
        "schema": SCHEMA,
        "verdict": "PASS" if not issues else "FAIL",
        "issues": sorted(set(issues)),
        "contract_sha256": manifest.get("contract_sha256"),
        "input_count": len(entries),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trial-dir",
        default=None,
        help="root against which contract generator_inputs are resolved",
    )
    parser.add_argument(
        "--contract-name",
        default="experiments/taskflow-native/TRIAL_CONTRACT.json",
        help="contract path relative to --trial-dir",
    )
    parser.add_argument(
        "--evidence-dir",
        default="experiments/taskflow-native/out/evidence",
        help="evidence path relative to --trial-dir",
    )
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    trial_dir = Path(args.trial_dir).resolve() if args.trial_dir else Path(__file__).resolve().parents[2]
    evidence_dir = (trial_dir / args.evidence_dir).resolve()
    try:
        result = (
            verify_snapshot(trial_dir, evidence_dir)
            if args.verify
            else capture_snapshot(trial_dir, evidence_dir, contract_name=args.contract_name)
        )
    except SnapshotError as exc:
        print(f"snapshot: FAIL ({type(exc).__name__})")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("verdict", "PASS") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
