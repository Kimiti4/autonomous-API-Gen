"""One system checkpoint binding artifact digest + database-state digest.

EV-A08-002 closes only when a single restore unit covers both the verified
artifact and the SQLite control-plane state. The checkpoint manifest binds
both digests under one checkpoint digest; restore refuses to move either
half when the binding does not verify, and a failure of the second half
rolls the first half back.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.engine import Engine

from app.engine.backends import (
    _validate_verified_artifact,
    backup_verified_artifact,
    restore_verified_artifact,
)
from app.storage.backup import (
    _database_path,
    _integrity_check,
    _sha256,
    backup_sqlite_database,
    restore_sqlite_database,
)

CHECKPOINT_SCHEMA = "evolution.system-checkpoint"
CHECKPOINT_SCHEMA_VERSION = 1
MANIFEST_NAME = "system-checkpoint.json"
DATABASE_IMAGE_NAME = "database.db"
ARTIFACT_DIR_NAME = "artifact"


def _binding_payload(manifest: dict) -> dict:
    return {
        "schema": manifest["schema"],
        "schema_version": manifest["schema_version"],
        "artifact_digest": manifest["artifact_digest"],
        "database_digest": manifest["database_digest"],
    }


def _binding_digest(manifest: dict) -> str:
    return hashlib.sha256(
        json.dumps(_binding_payload(manifest), sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _read_manifest(checkpoint_dir: Path) -> dict:
    manifest_path = checkpoint_dir / MANIFEST_NAME
    if not manifest_path.is_file():
        raise ValueError(f"system checkpoint manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != CHECKPOINT_SCHEMA:
        raise ValueError(f"unknown system checkpoint schema: {manifest.get('schema')!r}")
    if manifest.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported system checkpoint schema version: {manifest.get('schema_version')!r}"
        )
    for field in ("artifact_digest", "database_digest", "checkpoint_digest"):
        if not isinstance(manifest.get(field), str) or not manifest[field]:
            raise ValueError(f"system checkpoint manifest is missing {field}")
    return manifest


def create_system_checkpoint(
    engine: Engine,
    *,
    artifact_dir: str,
    artifact_digest: str,
    checkpoint_dir: str,
) -> dict:
    """Create one atomic checkpoint binding the verified artifact and the database."""
    artifact_source = Path(artifact_dir).resolve()
    _validate_verified_artifact(str(artifact_source), artifact_digest)

    destination = Path(checkpoint_dir).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.", dir=str(destination.parent))
    )
    try:
        database_digest = backup_sqlite_database(engine, staging / DATABASE_IMAGE_NAME)
        backup_verified_artifact(
            str(artifact_source),
            str(staging / ARTIFACT_DIR_NAME),
            expected_digest=artifact_digest,
        )
        manifest = {
            "schema": CHECKPOINT_SCHEMA,
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "artifact_digest": artifact_digest,
            "database_digest": database_digest,
        }
        manifest["checkpoint_digest"] = _binding_digest(manifest)
        (staging / MANIFEST_NAME).write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        if destination.exists():
            shutil.rmtree(destination) if destination.is_dir() else destination.unlink()
        staging.rename(destination)
        return manifest
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def verify_system_checkpoint(
    checkpoint_dir: str,
    *,
    expected_checkpoint_digest: str,
) -> dict:
    """Verify the checkpoint binding and both halves without restoring either."""
    checkpoint = Path(checkpoint_dir).resolve()
    manifest = _read_manifest(checkpoint)
    if manifest["checkpoint_digest"] != _binding_digest(manifest):
        raise ValueError("system checkpoint binding digest does not match its manifest")
    if manifest["checkpoint_digest"] != expected_checkpoint_digest:
        raise ValueError("system checkpoint digest mismatch")

    database_image = checkpoint / DATABASE_IMAGE_NAME
    _integrity_check(database_image)
    if _sha256(database_image) != manifest["database_digest"]:
        raise ValueError("system checkpoint database digest mismatch")

    _validate_verified_artifact(
        str(checkpoint / ARTIFACT_DIR_NAME), manifest["artifact_digest"]
    )
    return manifest


def restore_system_checkpoint(
    engine: Engine,
    checkpoint_dir: str,
    *,
    expected_checkpoint_digest: str,
    artifact_destination: str,
) -> dict:
    """Restore both halves as one unit, rolling the database back if either fails."""
    manifest = verify_system_checkpoint(
        checkpoint_dir, expected_checkpoint_digest=expected_checkpoint_digest
    )
    checkpoint = Path(checkpoint_dir).resolve()

    restore_sqlite_database(
        engine, checkpoint / DATABASE_IMAGE_NAME, manifest["database_digest"]
    )
    live_database = _database_path(engine)
    rollback = live_database.with_name(f".{live_database.name}.previous")
    try:
        restore_verified_artifact(
            str(checkpoint / ARTIFACT_DIR_NAME),
            artifact_destination,
            expected_digest=manifest["artifact_digest"],
        )
    except Exception:
        if rollback.is_file():
            os.replace(rollback, live_database)
        raise
    return manifest
