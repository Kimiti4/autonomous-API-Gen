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


def verify_snapshot(trial_dir: Path, evidence_dir: Path) -> dict[str, Any]:
    root = trial_dir.resolve(strict=True)
    evidence = evidence_dir.resolve(strict=True)
    if not _inside(root, evidence) or evidence == root:
        raise SnapshotError("evidence directory must be inside the trial root")
    try:
        manifest = json.loads((evidence / "snapshot.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SnapshotError("snapshot manifest is missing or invalid") from exc
    if manifest.get("schema") != SCHEMA:
        raise SnapshotError("unsupported snapshot schema")

    issues = []
    contract_snapshot = evidence / manifest.get("contract_snapshot_path", "")
    if not contract_snapshot.is_file() or sha256_file(contract_snapshot) != manifest.get("contract_sha256"):
        issues.append("contract_snapshot_integrity")
    source_contract = root / manifest.get("contract_path", CONTRACT_NAME)
    if not source_contract.is_file() or sha256_file(source_contract) != manifest.get("contract_sha256"):
        issues.append("source_contract_changed")

    for item in manifest.get("inputs", []):
        rel = item.get("path", "")
        snapshot_path = evidence / item.get("snapshot_path", "")
        if not snapshot_path.is_file() or sha256_file(snapshot_path) != item.get("sha256"):
            issues.append(f"snapshot_input_integrity:{rel}")
        source = root / rel
        if not source.is_file() or sha256_file(source) != item.get("sha256"):
            issues.append(f"source_input_changed:{rel}")

    return {
        "schema": SCHEMA,
        "verdict": "PASS" if not issues else "FAIL",
        "issues": issues,
        "contract_sha256": manifest.get("contract_sha256"),
        "input_count": len(manifest.get("inputs", [])),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial-dir", default=None)
    parser.add_argument("--evidence-dir", default="out/evidence")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    trial_dir = Path(args.trial_dir).resolve() if args.trial_dir else Path(__file__).resolve().parent
    evidence_dir = (trial_dir / args.evidence_dir).resolve()
    try:
        result = (
            verify_snapshot(trial_dir, evidence_dir)
            if args.verify
            else capture_snapshot(trial_dir, evidence_dir)
        )
    except SnapshotError as exc:
        print(f"snapshot: FAIL ({type(exc).__name__})")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("verdict", "PASS") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
