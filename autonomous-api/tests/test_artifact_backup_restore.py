import hashlib
import json
from pathlib import Path

import pytest

from app.engine.backends import (
    backup_verified_artifact,
    restore_verified_artifact,
)


def _artifact(root: Path, payload: str = "known-good") -> str:
    root.mkdir(parents=True, exist_ok=True)
    (root / "main.py").write_text(payload, encoding="utf-8")
    file_digest = hashlib.sha256((root / "main.py").read_bytes()).hexdigest()
    digest_payload = {
        "manifest_version": 1,
        "backend_id": "test",
        "architecture_hash": "arch-test",
        "files": {"main.py": file_digest},
    }
    digest = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    (root / "artifact-manifest.json").write_text(
        json.dumps({**digest_payload, "artifact_digest": digest}, sort_keys=True),
        encoding="utf-8",
    )
    return digest


def test_backup_is_restorable_to_known_good_state(tmp_path):
    source = tmp_path / "source"
    backup = tmp_path / "backup"
    destination = tmp_path / "live"

    digest = _artifact(source)
    backup_verified_artifact(str(source), str(backup), expected_digest=digest)

    destination.mkdir()
    (destination / "main.py").write_text("bad-state", encoding="utf-8")

    restore_verified_artifact(str(backup), str(destination), expected_digest=digest)

    assert (destination / "main.py").read_text(encoding="utf-8") == "known-good"
    assert (destination / "artifact-manifest.json").exists()


def test_tampered_backup_cannot_be_restored(tmp_path):
    source = tmp_path / "source"
    backup = tmp_path / "backup"
    destination = tmp_path / "live"

    digest = _artifact(source)
    backup_verified_artifact(str(source), str(backup), expected_digest=digest)
    (backup / "main.py").write_text("tampered", encoding="utf-8")

    with pytest.raises(ValueError, match="artifact file digest mismatch"):
        restore_verified_artifact(str(backup), str(destination), expected_digest=digest)


def test_promotion_keeps_previous_verified_artifact_as_rollback_point(tmp_path):
    from app.engine.backends import promote_verified_artifact

    first = tmp_path / "first"
    second = tmp_path / "second"
    destination = tmp_path / "live"

    first_digest = _artifact(first, "first-good")
    second_digest = _artifact(second, "second-good")

    promote_verified_artifact(str(first), str(destination), expected_digest=first_digest)
    promote_verified_artifact(str(second), str(destination), expected_digest=second_digest)

    backup = destination.with_name(f".{destination.name}.previous")
    assert backup.exists()
    restore_verified_artifact(str(backup), str(destination), expected_digest=first_digest)
    assert (destination / "main.py").read_text(encoding="utf-8") == "first-good"
