"""ModelCallTranscript -- append-only, hash-chained record stream.

Serves two roles:
  * a durable audit trail of every structured call (live or replayed);
  * the fixture source for deterministic replay.

A transcript recorded live in B6 can be committed and replayed hermetically
forever. Chain verification detects any post-hoc mutation.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from tiannara.domain.models.model_call import ModelCallRecord, ModelCallStatus
from tiannara.domain.services.canonical import sha256_hex

GENESIS_HASH = "0" * 64


class ModelCallTranscript:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    def append(self, record: ModelCallRecord) -> ModelCallRecord:
        with self._lock:
            previous = self._last_hash()
            record = record.model_copy(update={"previous_hash": previous})
            record_hash = self._hash_record(record, previous)
            record = record.model_copy(update={"record_hash": record_hash})
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(record.model_dump_json() + "\n")
            return record

    def iter_records(self):
        if not self._path.exists():
            return
        with self._path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    yield ModelCallRecord.model_validate_json(line)

    def index_by_signature(self) -> dict[str, ModelCallRecord]:
        """First-occurrence index of replayable records (non-empty payload)."""
        index: dict[str, ModelCallRecord] = {}
        for record in self.iter_records():
            if record.output_payload is None:
                continue
            if record.status is ModelCallStatus.FAILED:
                continue
            index.setdefault(record.signature_hash, record)
        return index

    def verify_chain(self) -> bool:
        previous = GENESIS_HASH
        for record in self.iter_records():
            payload = record.model_dump_json(
                exclude={"previous_hash", "record_hash"}
            )
            expected = sha256_hex(f"{previous}:{payload}")
            if record.previous_hash != previous or record.record_hash != expected:
                return False
            previous = record.record_hash
        return True

    def _last_hash(self) -> str:
        if not self._path.exists():
            return GENESIS_HASH
        last_line = ""
        with self._path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    last_line = line
        if not last_line.strip():
            return GENESIS_HASH
        return json.loads(last_line)["record_hash"]

    @staticmethod
    def _hash_record(record: ModelCallRecord, previous: str) -> str:
        payload = record.model_dump_json(exclude={"previous_hash", "record_hash"})
        return sha256_hex(f"{previous}:{payload}")
