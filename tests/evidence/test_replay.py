"""R2.8.10 -- Deterministic replay + static non-determinism gate tests."""
from datetime import datetime

import pytest

from tiannara.evidence import (
    DeterministicClock,
    DeterministicRNG,
    EvidenceChain,
    EvidenceChainBuilder,
    ReplaySpec,
    replay,
    scan_for_nondeterminism,
)

SPEC = ReplaySpec(
    corpus_hash="c", seed=7, baseline_hash="b", mutation_hash="m",
    isr_hash="i", environment_fingerprint="env",
)


def good_executor(spec, clock, rng):
    b = EvidenceChainBuilder(epoch=1)
    b.append("mutation", {"m": spec.mutation_hash, "ts": clock.now()})
    b.append("execution", {"draw": rng.random(), "ts": clock.now()})
    b.append("measurement", {"score": 1.0, "ts": clock.now()})
    return b.build()


def bad_executor(spec, clock, rng):
    b = EvidenceChainBuilder(epoch=1)
    b.append("mutation", {"m": spec.mutation_hash, "ts": datetime.now().isoformat()})
    b.append("measurement", {"score": 1.0, "ts": datetime.now().isoformat()})
    return b.build()


def _fresh():
    return DeterministicClock(), DeterministicRNG(SPEC.seed)


def test_deterministic_executor_replays_equivalently():
    recorded = good_executor(SPEC, *_fresh())
    verdict = replay(SPEC, recorded, good_executor, runs=3)
    assert verdict.internally_deterministic
    assert verdict.equivalent


def test_nondeterministic_executor_fails_replay():
    recorded = bad_executor(SPEC, *_fresh())
    verdict = replay(SPEC, recorded, bad_executor, runs=2)
    assert not verdict.internally_deterministic
    assert not verdict.equivalent
    assert any("non-deterministic" in n for n in verdict.notes)


def test_scanner_flags_datetime_now():
    src = "provenance = ISRProvenance(created_at=datetime.now().isoformat())"
    findings = scan_for_nondeterminism(src)
    assert any("datetime.now(" in f for f in findings)


def test_scanner_flags_uuid4():
    src = "import uuid; id = uuid.uuid4()"
    findings = scan_for_nondeterminism(src)
    assert any("uuid4(" in f for f in findings)


def test_scanner_flags_unseeded_random():
    src = "import random; x = random.random()"
    findings = scan_for_nondeterminism(src)
    assert any("random.random(" in f for f in findings)


def test_scanner_passes_clean_source():
    src = "ts = clock.now()\ndraw = rng.random()\nseed = DeterministicRNG(spec.seed)\n"
    assert scan_for_nondeterminism(src) == []


def test_cross_hash_seed_determinism():
    """The critical gate that an in-process double-run CANNOT catch.

    Runs the executor in separate subprocesses with distinct PYTHONHASHSEED
    values. If hash-ordering nondeterminism exists, the chain heads diverge.
    """
    import subprocess
    import sys

    script = """
from tiannara.evidence import (
    DeterministicClock, DeterministicRNG, EvidenceChainBuilder, ReplaySpec
)
import json, sys

spec = ReplaySpec(corpus_hash="c", seed=7, baseline_hash="b", mutation_hash="m",
                  isr_hash="i", environment_fingerprint="env")

class Item:
    __slots__ = ("key", "val")
    def __init__(self, k, v):
        self.key = k
        self.val = v

def executor(spec, clock, rng):
    items = {f"key_{i}": i for i in range(20)}
    b = EvidenceChainBuilder(epoch=1)
    b.append("mutation", {"seed": spec.seed, "keys": sorted(items.keys()), "draw": rng.random()})
    b.append("execution", {"items": {k: v for k, v in items.items()}, "ts": clock.now()})
    b.append("measurement", {"score": 1.0})
    return b.build()

clock = DeterministicClock()
rng = DeterministicRNG(spec.seed)
chain = executor(spec, clock, rng)
print(chain.head_hash())
"""
    hash_seeds = [0, 1, 2]
    results = []
    for seed_val in hash_seeds:
        env = dict(__import__("os").environ)
        env["PYTHONHASHSEED"] = str(seed_val)
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, env=env,
            timeout=30,
        )
        assert proc.returncode == 0, f"subprocess failed: {proc.stderr}"
        results.append(proc.stdout.strip())
    assert len(set(results)) == 1, (
        f"hash-seed nondeterminism detected: heads differ across seeds {results}"
    )
