"""Deterministic gates for the blind TaskFlow ESAP-native generation trial.

This evaluator never reads the reference implementation. It validates only the
trial contract, problem specification, acceptance manifest, generated ISR and
evidence supplied by the generator.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
TRIAL = ROOT / "experiments" / "taskflow-native"
FORBIDDEN = (
    "golden-projects/taskflow/app",
    "golden-projects/taskflow/ARCHITECTURE.md",
)


def load(name: str):
    return json.loads((TRIAL / name).read_text(encoding="utf-8"))


def assert_technology_neutral(value, path="root"):
    tokens = (
        "fastapi", "django", "flask", "next.js", "nextjs", "react",
        "postgres", "postgresql", "mysql", "sqlite", "redis", "docker",
        "kubernetes", "aws", "azure", "gcp", "render", "vercel",
    )
    text = json.dumps(value, sort_keys=True).lower()
    hits = [
        token for token in tokens
        if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", text)
    ]
    if hits:
        raise AssertionError(
            f"technology coupling in {path}: {sorted(set(hits))}"
        )


def assert_multi_backend_contract() -> None:
    matrix = load("MULTI_BACKEND_TRIAL.json")
    targets = {target["id"] for target in matrix["required_targets"]}
    assert targets == {"python-fastapi", "go-stdlib"}
    assert matrix["authority"] == "generated_isr"
    assert "other_target_source_code" in matrix["target_independence"]["forbidden_cross_target_inputs"]
    required = set(matrix["success_requires"])
    assert "both_targets_generated_by_live_esap_pipeline" in required
    assert "both_targets_runtime_verified" in required
    assert "both_targets_trace_back_to_same_isr" in required
    assert "no_recorded_replay_used_as_generation_evidence" in required


def main() -> int:
    contract = load("TRIAL_CONTRACT.json")
    acceptance = json.loads(
        (ROOT / "golden-projects/taskflow/ACCEPTANCE.json").read_text(
            encoding="utf-8"
        )
    )
    assert_multi_backend_contract()

    assert contract["mode"] == "blind-generation"
    assert not any(
        "golden-projects/taskflow/app" in x
        for x in contract["generator_inputs"]
    )
    assert set(contract["forbidden_inputs"]) == set(FORBIDDEN)

    problem = (TRIAL / "PROBLEM.md").read_text(encoding="utf-8").lower()
    assert "implementation technology is intentionally unspecified" in problem
    assert acceptance["completion_policy"] == "required-scope-only"

    generated_isr = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if generated_isr is None:
        print("BLOCKED: provider execution has not supplied a generated ISR; blind-generation certification cannot PASS.")
        return 2

    payload = json.loads(generated_isr.read_text(encoding="utf-8"))
    assert_technology_neutral(payload, str(generated_isr))
    print(
        "PASS: generated ISR is technology-neutral and satisfies "
        "the blind-trial boundary."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
