"""Evidence integrity: a tamper-evident hash chain for adversarial evidence.

Constitutional basis:
  * "Evidence Before Confidence" -- the evidence behind a score must be trustworthy.
  * "Maintain audit trails" / "Support reproducibility".
  * "Detect anomalies" -- deletion/duplication/reordering/modification/staleness.

Invariant: a perfect detection score is worthless if the evidence producing it
can be altered without detection. This module makes alteration detectable.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

GENESIS_HASH = "0" * 64


class ViolationClass(str, Enum):
    MODIFICATION = "modification"
    DELETION = "deletion"
    DUPLICATION = "duplication"
    REORDERING = "reordering"
    STALE = "stale"


@dataclass(frozen=True)
class Violation:
    cls: ViolationClass
    index: Optional[int]
    detail: str


@dataclass(frozen=True)
class VerificationResult:
    valid: bool
    violations: Tuple[Violation, ...]
    head_hash: str


def canonicalize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): canonicalize(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obj, (list, tuple)):
        return [canonicalize(v) for v in obj]
    return obj


def canonical_json(obj: Any) -> str:
    return json.dumps(
        canonicalize(obj), sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, default=str,
    )


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def content_hash(event_type: str, sequence: int, epoch: int,
                 payload: Dict[str, Any]) -> str:
    return sha256_hex(canonical_json(
        {"t": event_type, "s": sequence, "e": epoch, "p": payload}
    ))


def chain_hash(prev: str, content: str) -> str:
    return sha256_hex(f"{prev}|{content}")


@dataclass(frozen=True)
class EvidenceEvent:
    event_type: str
    sequence: int
    epoch: int
    payload: Dict[str, Any]
    content_hash: str
    prev_chain_hash: str
    chain_hash: str

    @classmethod
    def create(cls, event_type: str, sequence: int, epoch: int,
               payload: Dict[str, Any], prev_chain_hash: str) -> "EvidenceEvent":
        ch = content_hash(event_type, sequence, epoch, payload)
        link = chain_hash(prev_chain_hash, ch)
        return cls(event_type, sequence, epoch, payload, ch, prev_chain_hash, link)


@dataclass(frozen=True)
class EvidenceChain:
    events: Tuple[EvidenceEvent, ...]

    def head_hash(self) -> str:
        return self.events[-1].chain_hash if self.events else GENESIS_HASH

    def __len__(self) -> int:
        return len(self.events)


class EvidenceChainBuilder:
    def __init__(self, epoch: int = 0):
        self.epoch = epoch
        self._events: List[EvidenceEvent] = []
        self._head = GENESIS_HASH

    def append(self, event_type: str, payload: Dict[str, Any]) -> EvidenceEvent:
        seq = len(self._events)
        ev = EvidenceEvent.create(event_type, seq, self.epoch, payload, self._head)
        self._events.append(ev)
        self._head = ev.chain_hash
        return ev

    def build(self) -> EvidenceChain:
        return EvidenceChain(tuple(self._events))


@dataclass(frozen=True)
class Anchor:
    """A separately-preserved snapshot of chain state; prevents long-range
    re-forging after a middle deletion."""
    epoch: int
    length: int
    head_hash: str

    @classmethod
    def of(cls, epoch: int, chain: EvidenceChain) -> "Anchor":
        return cls(epoch, len(chain), chain.head_hash())


def verify_chain(chain: EvidenceChain,
                 anchor: Optional[Anchor] = None,
                 latest_epoch: int = 0) -> VerificationResult:
    violations: List[Violation] = []
    expected_prev = GENESIS_HASH
    seen_content: set = set()

    for i, ev in enumerate(chain.events):
        if ev.sequence != i:
            if ev.sequence > i:
                violations.append(Violation(
                    ViolationClass.DELETION, i,
                    f"expected seq {i}, found {ev.sequence} (gap => deletion)"))
            else:
                violations.append(Violation(
                    ViolationClass.REORDERING, i,
                    f"expected seq {i}, found {ev.sequence}"))

        if ev.content_hash in seen_content:
            violations.append(Violation(ViolationClass.DUPLICATION, i, "duplicate content_hash"))
        seen_content.add(ev.content_hash)

        if content_hash(ev.event_type, ev.sequence, ev.epoch, ev.payload) != ev.content_hash:
            violations.append(Violation(ViolationClass.MODIFICATION, i, "content_hash mismatch"))

        if ev.prev_chain_hash != expected_prev:
            violations.append(Violation(ViolationClass.REORDERING, i, "broken prev_chain_hash link"))

        if chain_hash(ev.prev_chain_hash, ev.content_hash) != ev.chain_hash:
            violations.append(Violation(ViolationClass.MODIFICATION, i, "chain_hash mismatch"))

        if ev.epoch < latest_epoch:
            violations.append(Violation(
                ViolationClass.STALE, i, f"epoch {ev.epoch} < latest accepted {latest_epoch}"))

        expected_prev = ev.chain_hash

    if anchor is not None:
        n = len(chain)
        if n < anchor.length:
            violations.append(Violation(
                ViolationClass.DELETION, None,
                f"chain length {n} < anchored length {anchor.length}"))
        elif anchor.length > 0:
            anchored_head = chain.events[anchor.length - 1].chain_hash
            if anchored_head != anchor.head_hash:
                violations.append(Violation(
                    ViolationClass.MODIFICATION, None, "anchored prefix head mismatch"))

    return VerificationResult(valid=not violations, violations=tuple(violations),
                              head_hash=chain.head_hash())
