"""G5 — storage independence static scan.

Ensures the constitutional layer (ISR core, ports, reqgraph, genesis) does
not import any storage or infrastructure technology.
"""

import os
import re
import sys

REPO_ROOT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."
)

FORBIDDEN_IMPORTS = [
    "sqlalchemy",
    "asyncpg",
    "psycopg",
    "psycopg2",
    "neo4j",
    "pymongo",
    "redis",
    "elasticsearch",
    "boto3",
    "botocore",
    "kubernetes",
    "pulumi",
    "terraform",
    "aio_pika",
    "kafka",
    "eventstore",
]

SCAN_DIRS = [
    "isr/core",
    "isr/ports",
    "isr/schema",
    "reqgraph/core",
    "genesis",
]

IMPORT_RE = re.compile(
    r"^\s*(?:import|from)\s+(" + "|".join(re.escape(t) for t in FORBIDDEN_IMPORTS) + r")\b",
    re.MULTILINE,
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
                violations.append(f"{rel}: imports '{match.group(1)}'")

if violations:
    print(
        "G5 FAIL — constitutional layer depends on storage/infra tech:",
        file=sys.stderr,
    )
    for v in violations:
        print(f"  {v}", file=sys.stderr)
    sys.exit(1)

print("G5 PASS — ISR/reqgraph/genesis core is storage-independent")
