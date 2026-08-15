"""Deterministic replay: epistemic reconstruction of an evidence chain.

Constitutional basis: "Support reproducibility", "Determinism where
appropriate", "Truth has priority over confidence."

Determinism is a PREREQUISITE for replay, not a cosmetic property. The
`scan_for_nondeterminism` gate exists precisely to catch the class of bug
found in R2.8.6 (implicit datetime.now() in ISR provenance).
"""
from __future__ import annotations

import random as _random
from dataclasses import dataclass
from typing import Callable, List, Tuple

from .integrity import EvidenceChain, EvidenceChainBuilder


@dataclass(frozen=True)
class ReplaySpec:
    corpus_hash: str
    seed: int
    baseline_hash: str
    mutation_hash: str
    isr_hash: str
    environment_fingerprint: str


class DeterministicClock:
    def __init__(self, start: int = 0, step: int = 1):
        self._now = start
        self._step = step

    def now(self) -> int:
        t = self._now
        self._now += self._step
        return t


class DeterministicRNG:
    def __init__(self, seed: int):
        self._rng = _random.Random(seed)

    def random(self) -> float:
        return self._rng.random()

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def choice(self, seq):
        return self._rng.choice(seq)


Executor = Callable[[ReplaySpec, "DeterministicClock", "DeterministicRNG"], EvidenceChain]


@dataclass(frozen=True)
class ReplayVerdict:
    equivalent: bool
    internally_deterministic: bool
    produced_head: str
    recorded_head: str
    produced_length: int
    recorded_length: int
    notes: Tuple[str, ...]


def replay(spec: ReplaySpec, recorded_chain: EvidenceChain,
           executor: Executor, runs: int = 2) -> ReplayVerdict:
    """Run the executor repeatedly under identical deterministic inputs.

    A certifiable executor must produce an identical chain on every run AND
    match the recorded chain.
    """
    notes: List[str] = []
    heads: List[str] = []
    lengths: List[int] = []

    for _ in range(runs):
        clock = DeterministicClock()
        rng = DeterministicRNG(spec.seed)
        chain = executor(spec, clock, rng)
        heads.append(chain.head_hash())
        lengths.append(len(chain))

    internally_deterministic = len(set(heads)) == 1
    if not internally_deterministic:
        notes.append("executor is non-deterministic across identical runs")

    matches_recorded = (
        internally_deterministic
        and heads
        and heads[0] == recorded_chain.head_hash()
        and lengths[0] == len(recorded_chain)
    )
    if internally_deterministic and heads and heads[0] != recorded_chain.head_hash():
        notes.append("replayed head does not match recorded head")

    return ReplayVerdict(
        equivalent=matches_recorded,
        internally_deterministic=internally_deterministic,
        produced_head=heads[0] if heads else "",
        recorded_head=recorded_chain.head_hash(),
        produced_length=lengths[0] if lengths else 0,
        recorded_length=len(recorded_chain),
        notes=tuple(notes),
    )


NONDETERMINISM_PATTERNS = {
    "datetime.now(": "wall-clock timestamp",
    "datetime.utcnow(": "wall-clock timestamp",
    "time.time(": "wall-clock timestamp",
    "time.monotonic(": "monotonic wall clock",
    "uuid4(": "random UUID",
    "os.urandom(": "OS randomness",
    "random.random(": "unseeded global RNG",
    "random.randint(": "unseeded global RNG",
    "random.choice(": "unseeded global RNG",
    "random.shuffle(": "unseeded global RNG",
    "secrets.token(": "OS randomness",
    "uuid.uuid1(": "time-based UUID (wall-clock + node)",
    "uuid.uuid4(": "random UUID",
    "threading.current_thread(": "thread identity (may vary)",
}


def scan_for_nondeterminism(source: str) -> List[str]:
    findings: List[str] = []
    for pattern, label in NONDETERMINISM_PATTERNS.items():
        if pattern in source:
            findings.append(f"{pattern} -> {label}")
    return findings
