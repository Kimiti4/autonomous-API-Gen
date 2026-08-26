"""Waves — Campaign B scale progression configuration.

Each wave is a self-contained measurement. B0 proves the Docker substrate
exists before any trials run. B1 is the 78-trial baseline directly
comparable to Campaign A. B2–B4 scale upward only after the previous
wave certifies.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from certification.corpus.corpus import Workload, _w, Category
from certification.stages.execution_mode import ExecutionMode


class WaveId(str, Enum):
    B0 = "B0"
    B1 = "B1"
    B2 = "B2"
    B3 = "B3"
    B4 = "B4"


@dataclass(frozen=True)
class Wave:
    id: str
    purpose: str
    scale_factor: int
    required_mode: ExecutionMode


WAVES: dict[str, Wave] = {
    WaveId.B0.value: Wave(
        id=WaveId.B0.value,
        purpose="docker substrate certification",
        scale_factor=0,
        required_mode=ExecutionMode.REAL_DOCKER,
    ),
    WaveId.B1.value: Wave(
        id=WaveId.B1.value,
        purpose="full corpus real execution (78 trials)",
        scale_factor=1,
        required_mode=ExecutionMode.REAL_DOCKER,
    ),
    WaveId.B2.value: Wave(
        id=WaveId.B2.value,
        purpose="hundreds",
        scale_factor=4,
        required_mode=ExecutionMode.REAL_DOCKER,
    ),
    WaveId.B3.value: Wave(
        id=WaveId.B3.value,
        purpose="1000+",
        scale_factor=12,
        required_mode=ExecutionMode.REAL_DOCKER,
    ),
    WaveId.B4.value: Wave(
        id=WaveId.B4.value,
        purpose="sustained scale",
        scale_factor=24,
        required_mode=ExecutionMode.REAL_DOCKER,
    ),
}


def expand_corpus(factor: int) -> list[Workload]:
    """Deterministically derive parameterized variants from the seed corpus.

    factor=1 returns the original 39. factor>1 creates TEMPLATE-class
    variants by rotating seeds and appending suffixed intents.
    """
    from certification.corpus.corpus import default_corpus
    base = default_corpus()
    if factor <= 1:
        return list(base)

    out: list[Workload] = list(base)
    for i in range(1, factor):
        for w in base:
            rotated = w.seeds[-i % len(w.seeds):] + w.seeds[:-i % len(w.seeds)] if len(w.seeds) > 1 else w.seeds
            variant = Workload(
                intent=f"{w.intent} variant-{i}",
                category=w.category,
                seeds=rotated,
            )
            out.append(variant)
    return out


def ledger_path_for(wave_id: str) -> str:
    return f"release/evidence/cbc1-b-{wave_id}-ledger.jsonl"


def aggregate_path_for(wave_id: str) -> str:
    return f"release/evidence/cbc1-b-{wave_id}-aggregate.json"
