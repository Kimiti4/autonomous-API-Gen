"""I7 — Identity independence static scan.

Ensures the identity package does not import ISR, evolution, or genesis modules.
Identity is infrastructure/security; it must never enter the ISR or Evolution Engine.
"""

import os
import re
import sys

REPO_ROOT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."
)

SCAN_DIRS = ["identity"]

FORBIDDEN_IMPORTS = [
    "isr.",
    "evolution.",
    "genesis.",
    "reqgraph.",
]

IMPORT_RE = re.compile(
    r"^\s*(?:import|from)\s+(" + "|".join(re.escape(t) for t in FORBIDDEN_IMPORTS) + r")",
    re.MULTILINE,
)

FORBIDDEN_TERMS = [
    "postgres", "mysql", "redis", "kafka", "neo4j",
    "boto3", "kubernetes", "terraform",
]

TERM_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in FORBIDDEN_TERMS) + r")\b",
    re.IGNORECASE,
)

violations: list[str] = []

for subdir in SCAN_DIRS:
    base = os.path.join(REPO_ROOT, subdir)
    if not os.path.isdir(base):
        continue
    for root, _, files in os.walk(base):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            text = open(fpath, encoding="utf-8").read()
            for match in IMPORT_RE.finditer(text):
                rel = os.path.relpath(fpath, REPO_ROOT).replace("\\", "/")
                violations.append(f"{rel}: imports forbidden '{match.group(0).strip()}'")
            for match in TERM_RE.finditer(text):
                rel = os.path.relpath(fpath, REPO_ROOT).replace("\\", "/")
                violations.append(f"{rel}: contains forbidden term '{match.group()}'")

if violations:
    print("I7 FAIL — identity independence violated:", file=sys.stderr)
    for v in violations:
        print(f"  {v}", file=sys.stderr)
    sys.exit(1)

print("I7 PASS — identity package is independent of ISR/evolution/genesis")
