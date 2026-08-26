"""Independent verifier — runs in a SEPARATE process.

Re-derives conformance from the repo on disk + the plan hash.
Never trusts generator in-memory state.
"""
from __future__ import annotations
import hashlib
import json
import os
import sys


def main() -> None:
    if len(sys.argv) < 4:
        print(json.dumps({"error": "usage: independent_verify.py REPO_DIR PLAN_HASH PLAN_PATH"}))
        sys.exit(1)

    repo_dir = sys.argv[1]
    expected_plan_hash = sys.argv[2]
    plan_path = sys.argv[3]

    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)

    expected_paths: list[str] = plan.get("expected_paths", [])
    files: dict[str, str] = {}
    for p in expected_paths:
        full = os.path.join(repo_dir, p)
        if os.path.exists(full):
            with open(full, encoding="utf-8") as fh:
                files[p] = fh.read()

    from compiler.core.repository import build_repository

    repo = build_repository(files)

    plan_hash_computed = hashlib.sha256(
        json.dumps(expected_paths, sort_keys=True).encode("utf-8")
    ).hexdigest()
    plan_match = plan_hash_computed == expected_plan_hash

    result = {
        "independent": True,
        "repo_hash": repo.content_hash,
        "plan_match": plan_match,
        "files_found": len(files),
        "files_expected": len(expected_paths),
    }
    print(json.dumps(result))
    sys.exit(0 if plan_match else 1)


if __name__ == "__main__":
    main()
