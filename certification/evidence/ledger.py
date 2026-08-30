"""EvidenceLedger — append-only, tamper-evident hash chain for CBC-1 trials."""
from __future__ import annotations
import hashlib
import json
from typing import Any


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


GENESIS_HASH = "0" * 64


class EvidenceLedger:
    """Append-only ledger where each record binds the previous hash."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.prev = self._tail_hash() or GENESIS_HASH

    def _tail_hash(self) -> str | None:
        try:
            last: dict | None = None
            for line in open(self.path, encoding="utf-8"):
                line = line.strip()
                if line:
                    last = json.loads(line)
            return last["record_hash"] if last else None
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None

    def append(self, trial_dict: dict) -> str:
        body = _canonical(trial_dict)
        record_hash = hashlib.sha256(
            (self.prev + body).encode("utf-8")
        ).hexdigest()
        entry = {
            "prev_hash": self.prev,
            "record_hash": record_hash,
            "trial": trial_dict,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.prev = record_hash
        return record_hash

    @staticmethod
    def verify(path: str) -> bool:
        """Verify the full hash chain from genesis.

        Returns False (never raises) on corrupt/malformed records — a broken
        chain is a failed verification, not an exception the caller must catch.
        """
        prev = GENESIS_HASH
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                return False
            if entry.get("prev_hash") != prev:
                return False
            body = _canonical(entry.get("trial", {}))
            expected = hashlib.sha256(
                (prev + body).encode("utf-8")
            ).hexdigest()
            if entry.get("record_hash") != expected:
                return False
            prev = entry["record_hash"]
        return True

    @staticmethod
    def count(path: str) -> int:
        count = 0
        try:
            for line in open(path, encoding="utf-8"):
                if line.strip():
                    count += 1
        except FileNotFoundError:
            pass
        return count
