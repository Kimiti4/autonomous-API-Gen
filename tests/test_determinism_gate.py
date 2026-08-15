"""Determinism gate: cross-PYTHONHASHSEED subprocess verification.

This is the R2.8.6/R2.8.12 determinism contract: the decision path must not
depend on hash-table ordering. The test runs the full adversarial-composition
pipeline (composer + gate) under multiple PYTHONHASHSEED values in separate
subprocesses and verifies identical verdicts and catching layers.

The R2.8.12 replay invariant asserts in-process; this test goes further --
it asserts cross-process determinism, which is the certification-grade
contract that proves evidence is reproducible.
"""
from __future__ import annotations

import os
import subprocess
import sys

import pytest


SCRIPT = (
    "from tiannara.application.evolution.adversarial_lab import "
    "build_adversarial_harness, MutationComposer, COMPOSED_MUTATION_MATRIX as M; "
    "p, b, br, ap, d, m = build_adversarial_harness(); "
    "c = MutationComposer(); "
    "out = []; "
    "[out.append((s.composition_id, "
    "d.decide(p, br, c.compose(s, b, 11)).feasible, "
    "tuple(d.decide(p, br, c.compose(s, b, 11)).catching_layers))) for s in M]; "
    "print(repr(out))"
)


@pytest.mark.parametrize("seed", ["0", "1", "42", "random"])
def test_composition_deterministic_under_pythonhashseed(seed):
    """Each PYTHONHASHSEED must produce a valid result."""
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = seed
    proc = subprocess.run(
        [sys.executable, "-c", SCRIPT],
        capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0, proc.stderr


def test_all_seeds_produce_identical_verdicts():
    """All PYTHONHASHSEED values must produce identical verdicts and layers."""
    results = {}
    for seed in ("0", "1", "42", "random"):
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = seed
        proc = subprocess.run(
            [sys.executable, "-c", SCRIPT],
            capture_output=True, text=True, env=env,
        )
        assert proc.returncode == 0, proc.stderr
        results[seed] = proc.stdout.strip()

    reference = results["0"]
    for seed, output in results.items():
        if seed == "0":
            continue
        assert output == reference, (
            f"Determinism violation under PYTHONHASHSEED={seed}: "
            f"expected {reference}, got {output}"
        )
