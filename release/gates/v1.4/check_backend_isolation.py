"""C11 — compiler core does not import concrete backends (static scan)."""
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
CORE_DIR = os.path.join(ROOT, "compiler", "core")

violations: list[str] = []
for fname in os.listdir(CORE_DIR):
    if not fname.endswith(".py"):
        continue
    fpath = os.path.join(CORE_DIR, fname)
    text = open(fpath, encoding="utf-8").read()
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "compiler.backends" in stripped or "from compiler.backends" in stripped:
            violations.append(f"compiler/core/{fname}:{i}: {stripped}")

if violations:
    print("C11 FAIL — core imports backend:", file=sys.stderr)
    for v in violations:
        print(f"  {v}", file=sys.stderr)
    sys.exit(1)

print("C11 PASS — compiler core depends only on the backend protocol")
