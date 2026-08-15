"""
ISR Snapshots.

Provides persistence of complete ISR snapshots for reproducibility.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.serialization.deserializer import ISRDeserializer
from constitutional_architecture.isr.serialization.serializer import ISRSerializer
from constitutional_architecture.isr.versioning.hash import ContentHasher


class SnapshotStore:
    """
    Persists ISR snapshots to disk.

    Each snapshot is stored as a JSON file named by its content hash.
    This enables perfect reproducibility and time-travel debugging.
    """

    def __init__(self, storage_dir: str | Path) -> None:
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, isr: ISR) -> str:
        content_hash = ContentHasher.hash_isr(isr)
        file_path = self._storage_dir / f"{content_hash}.json"

        if not file_path.exists():
            json_str = ISRSerializer.to_json(isr)
            file_path.write_text(json_str, encoding="utf-8")

        return content_hash

    def load(self, content_hash: str) -> Optional[ISR]:
        file_path = self._storage_dir / f"{content_hash}.json"
        if not file_path.exists():
            return None
        json_str = file_path.read_text(encoding="utf-8")
        return ISRDeserializer.from_json(json_str)

    def exists(self, content_hash: str) -> bool:
        return (self._storage_dir / f"{content_hash}.json").exists()

    def list_snapshots(self) -> list[str]:
        return [
            p.stem for p in self._storage_dir.glob("*.json")
        ]

    def delete(self, content_hash: str) -> bool:
        file_path = self._storage_dir / f"{content_hash}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False
