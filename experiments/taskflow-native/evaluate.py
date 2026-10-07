"""Deterministic gates for the blind TaskFlow ESAP-native generation trial.

This evaluator never reads the reference implementation. It validates only the
trial contract, problem specification, acceptance manifest, generated ISR and
evidence manifest supplied by the generator.
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
    hits = [token for token in tokens if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", text)]
    if hits:
        raise AssertionError(f"technology coupling in {path}: {sorted(set(hits))}")


def main() -> int:
    contract = load("TRIAL_CONTRACT.json")
    acceptance = json.loads(
        (ROOT / "golden-projects/taskflow/ACCEPTANCE.json").read_text(encoding="utf-8")
    )

    assert contract["mode"] == "blind-generation"
    assert not any("golden-projects/taskflow/app" in x for x in contract["generator_inputs"])
    assert set(contract["forbidden_inputs"]) == set(FORBIDDEN)

    problem = (TRIAL / "PROBLEM.md").read_text(encoding="utf-8").lower()
    assert "implementation technology is intentionally unspecified" in problem

    # Acceptance remains an oracle/constraint set, not implementation input.
    assert acceptance["completion_policy"] == "required-scope-only"

    generated_isr = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if generated_isr is None:
        print("CONTRACT_ONLY: provider execution has not supplied a generated ISR.")
        return 0

    payload = json.loads(generated_isr.read_text(encoding="utf-8"))
    assert_technology_neutral(payload, str(generated_isr))
    print("PASS: generated ISR is technology-neutral and satisfies blind-trial boundary.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
