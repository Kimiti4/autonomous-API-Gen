"""CBC-1 independence scanner — certification package does not mutate ISR/compiler."""
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
CERT_DIR = os.path.join(ROOT, "certification")

FORBIDDEN = [
    "isr.core.graph.ISRGraph",
    "isr.core.revision.ISRRevision.create",
    "evolution.core.engine.EvolutionEngine",
]

violations: list[str] = []
for root, _, files in os.walk(CERT_DIR):
    for fname in files:
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(root, fname)
        text = open(fpath, encoding="utf-8").read()
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for term in FORBIDDEN:
                if term in stripped:
                    rel = os.path.relpath(fpath, ROOT).replace("\\", "/")
                    violations.append(f"{rel}:{i}: {stripped}")

if violations:
    print("CBC1-INDEP FAIL — certification mutates domain:", file=sys.stderr)
    for v in violations:
        print(f"  {v}", file=sys.stderr)
    sys.exit(1)

print("CBC1-INDEP PASS — certification package is pipeline-only")
