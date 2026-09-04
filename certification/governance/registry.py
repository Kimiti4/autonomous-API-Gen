"""Certification Governance Registry — cross-phase attempt/verdict tracking.

Phase 31 spec's "Cross-Cutting Gaps to Close Before Phase 31" item #5:
  "Certification Governance registry: Tracks attempts, verdicts,
   regressions across phases; makes the whole program auditable."

The registry is a SEPARATE append-only hash-chained JSONL ledger. Each
record is an `AttemptRecord` (one row per certification attempt). The
registry is cross-phase: it covers Phase 31 and any future phase that
wants to log a verdict.

Design rules:

  1. Append-only. The hash chain is per-record (prev_hash -> record_hash);
     tampering any prior record breaks the chain.
  2. Schema-addressable. Each record carries `schema_id` and `schema_version`
     so a future reader can validate the record shape.
  3. Cross-phase. Records are keyed by (phase_id, attempt_id), not by
     wave_id. A phase can have many attempts (each on a different config
     or scale).
  4. Honest missing data. If a field is not supplied, the record says
     so — never silently zero.
  5. No coupling to the verdict ledger. The wave's verdict chain
     (`cbc1-b-*.jsonl`) feeds certification, but the governance
     registry is a separate concern. It can record the same event
     with a different lens (cross-phase regression instead of
     single-wave integrity).

Regressions are detected by the `detect_regressions()` method: for
each (phase_id, attempt_id) series, if the most recent verdict is
NOT_CERTIFIED or QUALIFIED_PARTIAL but a prior verdict was CERTIFIED,
the attempt has regressed. The output is a list of regression
findings, each with a before/after diff so an auditor can see what
changed.

Default registry path:
  release/evidence/cbc1-governance.jsonl

(Per .gitignore, `release/evidence/` is gitignored. The registry file
is regenerated from the policy log on every run; auditors archive
their own copies.)
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

GENESIS_HASH = "0" * 64

SCHEMA_ID = "tiannara.governance.attempt"
SCHEMA_VERSION = "1.0.0"

DEFAULT_PATH = "release/evidence/cbc1-governance.jsonl"


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _utcnow_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _h(record_dict: dict, prev_hash: str) -> str:
    """SHA-256 of canonical(record) with prev_hash and record_hash removed."""
    body = {k: v for k, v in record_dict.items() if k not in ("prev_hash", "record_hash")}
    body["prev_hash"] = prev_hash
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AttemptRecord:
    """A single certification attempt. Immutable.

    Attributes:
        schema_id / schema_version   : the record's own schema identity.
        attempt_id                    : the per-(phase, config) attempt id.
        phase_id                      : the certification phase
                                       (e.g. "phase_31_5_certification").
        recorded_at                   : ISO timestamp the record was
                                       emitted (UTC).
        verdict                       : "CERTIFIED" / "NOT_CERTIFIED"
                                       / "QUALIFIED_PARTIAL".
        verdict_reason                : human-readable short reason.
        evidence_refs                 : tuple of ledger event refs that
                                       support this verdict.
        metrics                       : optional free-form metrics
                                       (e.g. {"envelope": 500,
                                        "certified_pct": 0.85}).
        parent_attempt_id              : the previous attempt id, if
                                       this is a follow-on.
        issued_by                     : who/what emitted the record.
        prev_hash                     : chain link (set by registry.append).
        record_hash                   : content hash (set by registry.append).
    """

    attempt_id: str
    phase_id: str
    recorded_at: str
    verdict: str
    verdict_reason: str
    evidence_refs: tuple[str, ...] = ()
    metrics: Mapping[str, Any] = field(default_factory=dict)
    parent_attempt_id: str = ""
    issued_by: str = "campaign_b"
    schema_id: str = SCHEMA_ID
    schema_version: str = SCHEMA_VERSION
    prev_hash: str = GENESIS_HASH
    record_hash: str = ""

    def content(self) -> dict:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "attempt_id": self.attempt_id,
            "phase_id": self.phase_id,
            "recorded_at": self.recorded_at,
            "verdict": self.verdict,
            "verdict_reason": self.verdict_reason,
            "evidence_refs": list(self.evidence_refs),
            "metrics": dict(self.metrics),
            "parent_attempt_id": self.parent_attempt_id,
            "issued_by": self.issued_by,
        }

    def to_envelope(self, prev_hash: str) -> dict:
        body = self.content()
        body["prev_hash"] = prev_hash
        rh = _h(body, prev_hash)
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "prev_hash": prev_hash,
            "record_hash": rh,
            "record": body,
        }


class CertificationGovernanceRegistry:
    """Append-only, hash-chained, cross-phase certification registry.

    Default path is `release/evidence/cbc1-governance.jsonl` (gitignored).
    Tests can override the path.
    """

    def __init__(self, path: str = DEFAULT_PATH) -> None:
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._prev = self._tail_hash() or GENESIS_HASH
        self._count = 0
        self._by_phase_attempt: dict[tuple[str, str], dict] = {}

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

    def append(self, record: AttemptRecord) -> str:
        envelope = record.to_envelope(self._prev)
        self._prev = envelope["record_hash"]
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(envelope, ensure_ascii=False) + "\n")
        self._count += 1
        key = (record.phase_id, record.attempt_id)
        self._by_phase_attempt[key] = envelope
        return envelope["record_hash"]

    def record(
        self,
        *,
        attempt_id: str,
        phase_id: str,
        verdict: str,
        verdict_reason: str,
        evidence_refs: Iterable[str] = (),
        metrics: dict | None = None,
        parent_attempt_id: str = "",
        issued_by: str = "campaign_b",
        recorded_at: str | None = None,
    ) -> str:
        """Convenience constructor that builds an AttemptRecord and appends."""
        r = AttemptRecord(
            attempt_id=attempt_id,
            phase_id=phase_id,
            recorded_at=recorded_at or _utcnow_iso(),
            verdict=verdict,
            verdict_reason=verdict_reason,
            evidence_refs=tuple(evidence_refs),
            metrics=metrics or {},
            parent_attempt_id=parent_attempt_id,
            issued_by=issued_by,
        )
        return self.append(r)

    @staticmethod
    def verify(path: str) -> bool:
        """Verify the registry chain from genesis. Returns False (never
        raises) on corruption."""
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
                    expected = _h(body, prev)
                    if env.get("prev_hash") != prev:
                        return False
                    if env.get("record_hash") != expected:
                        return False
                    prev = env["record_hash"]
                except (json.JSONDecodeError, KeyError):
                    return False
        return True

    @staticmethod
    def read_all(path: str = DEFAULT_PATH) -> list[dict]:
        """Read all envelopes from the registry. Returns the raw JSON
        envelopes (with `record` and `record_hash`)."""
        if not os.path.exists(path):
            return []
        out: list[dict] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out

    @staticmethod
    def detect_regressions(path: str = DEFAULT_PATH) -> list[dict]:
        """For each (phase_id, attempt_id) series, return a list of
        regression findings: prior CERTIFIED, current NOT_CERTIFIED or
        QUALIFIED_PARTIAL.

        A regression is a finding, not an action. The escalation
        policy (certification/governance/escalation_policy.py) should
        be invoked on this signal; humans decide what to do.
        """
        envelopes = CertificationGovernanceRegistry.read_all(path)
        # Group by (phase_id, attempt_id) preserving the chain order
        by_key: dict[tuple[str, str], list[dict]] = {}
        for env in envelopes:
            body = env.get("record", {})
            key = (body.get("phase_id", "?"), body.get("attempt_id", "?"))
            by_key.setdefault(key, []).append(body)
        regressions: list[dict] = []
        for (phase_id, attempt_id), records in by_key.items():
            # The most recent record (last in chain) is current. Find the
            # most recent prior CERTIFIED.
            current = records[-1]
            current_verdict = current.get("verdict")
            if current_verdict == "CERTIFIED":
                continue
            prior_certified = None
            for r in records[:-1]:
                if r.get("verdict") == "CERTIFIED":
                    prior_certified = r
            if prior_certified is None:
                continue
            regressions.append({
                "phase_id": phase_id,
                "attempt_id": attempt_id,
                "before": {
                    "recorded_at": prior_certified.get("recorded_at"),
                    "verdict": prior_certified.get("verdict"),
                    "verdict_reason": prior_certified.get("verdict_reason"),
                    "evidence_refs": list(prior_certified.get("evidence_refs", [])),
                    "metrics": dict(prior_certified.get("metrics", {})),
                },
                "after": {
                    "recorded_at": current.get("recorded_at"),
                    "verdict": current.get("verdict"),
                    "verdict_reason": current.get("verdict_reason"),
                    "evidence_refs": list(current.get("evidence_refs", [])),
                    "metrics": dict(current.get("metrics", {})),
                },
                "delta_metrics": {
                    k: current.get("metrics", {}).get(k, 0) - prior_certified.get("metrics", {}).get(k, 0)
                    for k in set(prior_certified.get("metrics", {})) | set(current.get("metrics", {}))
                    if isinstance(current.get("metrics", {}).get(k), (int, float))
                    and isinstance(prior_certified.get("metrics", {}).get(k), (int, float))
                },
            })
        return regressions

    def summary(self) -> dict:
        """A small audit summary for the post-wave report."""
        envelopes = CertificationGovernanceRegistry.read_all(self.path)
        by_phase: dict[str, int] = {}
        by_verdict: dict[str, int] = {}
        for env in envelopes:
            body = env.get("record", {})
            by_phase[body.get("phase_id", "?")] = by_phase.get(body.get("phase_id", "?"), 0) + 1
            by_verdict[body.get("verdict", "?")] = by_verdict.get(body.get("verdict", "?"), 0) + 1
        return {
            "path": self.path,
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "record_count": self._count,
            "tail_hash": self._prev,
            "chain_verified": self.verify(self.path),
            "by_phase": by_phase,
            "by_verdict": by_verdict,
        }
