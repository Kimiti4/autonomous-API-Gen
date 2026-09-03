"""Infra-storm ledger — a SEPARATE, hash-chained, LEARN-ONLY ledger for
infrastructure-classified trial failures.

CRITICAL DESIGN RULES:

  1. **Separate file from the verdict ledger.** This is `cbc1-{wave}-infra-storm.jsonl`
     — NOT a column in `cbc1-{wave}-ledger.jsonl`. The verdict ledger feeds
     `verify_campaign_b_mode` and the certification chain. The infra-storm
     ledger NEVER does.

  2. **Append-only, hash-chained.** Same primitive as `EvidenceLedger`:
     `prev_hash` / `record_hash` (SHA-256 over canonical record + prev).
     Tamper-evident independently.

  3. **Content-addressable schema.** Every record carries `schema_id` +
     `schema_version` + `record_hash` + `cause` + `domain` + `cause_mark`
     so an external tool can verify the record belongs to this ledger
     without consulting the verdict ledger.

  4. **One-way correlation only.** Records carry a `trial_id` field so an
     auditor can look up the parent trial in the verdict ledger by id.
     The verdict ledger does NOT carry any reference to the infra-storm
     ledger. There is no `evidence_refs` reverse-edge.

  5. **Never feeds CertificationHarness.** `CertificationRig.make_certifier()`
     and `Phase31.evidence` operate on the verdict ledger only. The
     infra-storm ledger is read by external analysis tools (e.g. a
     post-wave infra-stability report) and is never part of the
     certification's evidence graph.

  6. **Never auto-evolves.** Per the master prompt §13 ("Never evolve a
     workload because Docker failed"), infrastructure failures do not
     produce evolution candidates. The infra-storm ledger exists so the
     signal is preserved OFF the verdict chain — it does not change the
     policy.

  7. **Optional — only instantiated on demand.** `InfraStormLedger(path)`
     is constructed by the wave runner when CBC1_INFRA_STORM=1 is set
     (default: 1). It is NEVER constructed by the certification path,
     the campaign-b mode-verify path, or any Tier-A test fixture.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable

GENESIS_HASH = "0" * 64

SCHEMA_ID = "tiannara.infra_storm.record"
SCHEMA_VERSION = "1.0.0"


def _canonical(obj: Any) -> str:
    """Canonical JSON form: sorted keys, no whitespace, ensure_ascii=False."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _utcnow_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@dataclass(frozen=True)
class InfraStormRecord:
    """A single infrastructure-failure signal mirrored off the verdict chain.

    `trial_id` is the only correlation to the verdict ledger. Every other
    field is self-describing so the record is independently auditable.
    """

    schema_id: str
    schema_version: str
    record_hash: str = ""
    prev_hash: str = GENESIS_HASH
    occurred_at: str = ""
    source_wave: str = ""
    trial_id: str = ""
    intent: str = ""
    backend: str = ""
    stage: str = ""
    cause: str = ""
    feedback_domain: str = ""
    cause_mark: str = ""
    detail_excerpt: str = ""
    retry_signatures: tuple[str, ...] = ()
    repair_eligible: bool = False

    def content(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("record_hash", None)
        d.pop("prev_hash", None)
        return d

    def to_envelope(self, prev_hash: str) -> dict[str, Any]:
        body = self.content()
        canonical = _canonical(body)
        rh = hashlib.sha256(
            (prev_hash + canonical).encode("utf-8")
        ).hexdigest()
        return {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "prev_hash": prev_hash,
            "record_hash": rh,
            "record": body,
        }

    @staticmethod
    def build(
        *,
        source_wave: str,
        trial_id: str,
        intent: str,
        backend: str,
        stage: str,
        cause: str,
        feedback_domain: str,
        cause_mark: str,
        detail_excerpt: str,
        retry_signatures: Iterable[str] = (),
        repair_eligible: bool,
    ) -> "InfraStormRecord":
        return InfraStormRecord(
            schema_id=SCHEMA_ID,
            schema_version=SCHEMA_VERSION,
            prev_hash=GENESIS_HASH,
            occurred_at=_utcnow_iso(),
            source_wave=source_wave,
            trial_id=trial_id,
            intent=intent,
            backend=backend,
            stage=stage,
            cause=cause,
            feedback_domain=feedback_domain,
            cause_mark=cause_mark,
            detail_excerpt=detail_excerpt[:512],
            retry_signatures=tuple(retry_signatures),
            repair_eligible=repair_eligible,
        )


class InfraStormLedger:
    """Append-only, hash-chained, JSONL infra-failure ledger.

    Independent file. Independent hash chain. Independent schema.
    The verdict ledger has no knowledge of this ledger's existence.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._prev = self._tail_hash() or GENESIS_HASH
        self._count = 0
        self._causes: dict[str, int] = {}
        self._stages: dict[str, int] = {}
        self._backends: dict[str, int] = {}

    def _tail_hash(self) -> str | None:
        try:
            last: dict | None = None
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        last = json.loads(line)
            return last["record_hash"] if last else None
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None

    @property
    def prev_hash(self) -> str:
        return self._prev

    def append(self, record: InfraStormRecord) -> str:
        envelope = record.to_envelope(self._prev)
        self._prev = envelope["record_hash"]
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(envelope, ensure_ascii=False) + "\n")
        self._count += 1
        self._causes[record.cause] = self._causes.get(record.cause, 0) + 1
        self._stages[record.stage] = self._stages.get(record.stage, 0) + 1
        self._backends[record.backend] = self._backends.get(record.backend, 0) + 1
        return envelope["record_hash"]

    def record(
        self,
        *,
        source_wave: str,
        trial_id: str,
        intent: str,
        backend: str,
        stage: str,
        cause: str,
        feedback_domain: str,
        cause_mark: str = "",
        detail_excerpt: str = "",
        retry_signatures: Iterable[str] = (),
        repair_eligible: bool,
    ) -> str:
        """Convenience constructor that builds and appends in one call."""
        r = InfraStormRecord.build(
            source_wave=source_wave,
            trial_id=trial_id,
            intent=intent,
            backend=backend,
            stage=stage,
            cause=cause,
            feedback_domain=feedback_domain,
            cause_mark=cause_mark,
            detail_excerpt=detail_excerpt,
            retry_signatures=retry_signatures,
            repair_eligible=repair_eligible,
        )
        return self.append(r)

    @staticmethod
    def verify(path: str) -> bool:
        """Verify the infra-storm chain from genesis.

        Returns False (never raises) on any corruption. Independent of
        the verdict ledger's verification.
        """
        prev = GENESIS_HASH
        if not os.path.exists(path):
            return True
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    env = json.loads(line)
                    body = env.get("record", {})
                    canonical = _canonical(body)
                    expected = hashlib.sha256(
                        (prev + canonical).encode("utf-8")
                    ).hexdigest()
                    if env.get("prev_hash") != prev:
                        return False
                    if env.get("record_hash") != expected:
                        return False
                    prev = env["record_hash"]
                except (json.JSONDecodeError, KeyError):
                    return False
        return True

    def summary(self) -> dict[str, Any]:
        """A small audit summary for the post-wave report."""
        return {
            "ledger_path": self.path,
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "record_count": self._count,
            "tail_hash": self._prev,
            "chain_verified": self.verify(self.path),
            "by_cause": dict(self._causes),
            "by_stage": dict(self._stages),
            "by_backend": dict(self._backends),
        }
