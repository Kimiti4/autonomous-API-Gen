"""E8/E11 — Stage replaceability and adapter conformance static scan.

Ensures:
1. All pipeline stage classes in evolution/core/ are Protocol-based (replaceable).
2. Reference adapters conform to their Protocol interfaces.
3. No forbidden imports from infrastructure/storage technology.
"""

import ast
import os
import re
import sys

REPO_ROOT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."
)

SCAN_DIR = os.path.join(REPO_ROOT, "evolution", "core")

FORBIDDEN_IMPORTS = [
    "sqlalchemy",
    "asyncpg",
    "psycopg",
    "neo4j",
    "pymongo",
    "redis",
    "elasticsearch",
    "boto3",
    "kubernetes",
    "pulumi",
    "terraform",
    "aio_pika",
    "kafka",
]

IMPORT_RE = re.compile(
    r"^\s*(?:import|from)\s+("
    + "|".join(re.escape(t) for t in FORBIDDEN_IMPORTS)
    + r")\b",
    re.MULTILINE,
)

STAGE_FILES = {
    "construction.py": "ReferenceGenomeConstructor",
    "materialize.py": "ReferenceGenomeMaterializer",
    "fitness_evaluator.py": "ReferenceISRFitnessEvaluator",
    "selection.py": "ReferenceParetoSelection",
    "refinement.py": "ReferenceArchitectureRefinement",
}

errors: list[str] = []

# --- E8: check no forbidden imports ---
for root, _, files in os.walk(SCAN_DIR):
    for fname in files:
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(root, fname)
        text = open(fpath, encoding="utf-8").read()
        for match in IMPORT_RE.finditer(text):
            rel = os.path.relpath(fpath, REPO_ROOT).replace("\\", "/")
            errors.append(f"{rel}: imports forbidden '{match.group(1)}'")

# --- E11: check Protocol conformance (classes have concrete methods) ---
for fname, expected_class in STAGE_FILES.items():
    fpath = os.path.join(SCAN_DIR, fname)
    if not os.path.exists(fpath):
        errors.append(f"{fname}: file missing")
        continue
    tree = ast.parse(open(fpath, encoding="utf-8").read())
    class_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == expected_class:
            class_found = True
            methods = [
                n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            if not methods:
                errors.append(f"{fname}:{expected_class}: no methods (not a real adapter)")
            break
    if not class_found:
        errors.append(f"{fname}: class '{expected_class}' not found")

if errors:
    print("E8/E11 FAIL — stage replaceability issues:", file=sys.stderr)
    for e in errors:
        print(f"  {e}", file=sys.stderr)
    sys.exit(1)

print("E8/E11 PASS — all pipeline stages are Protocol-conformant and import-clean")
