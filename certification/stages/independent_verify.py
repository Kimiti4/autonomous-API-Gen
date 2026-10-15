"""Independent verifier — checks on-disk candidate identity and plan conformance.

Runs in a separate process. It re-reads all expected generated files, recomputes
the canonical repository digest, validates the path-set digest, reconstructs
the typed plan, and invokes the registered backend's independent conformance
checker. Missing files, unsafe paths, malformed metadata, or any failed check
produce a nonzero exit status.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 4:
        print(json.dumps({"error": "usage: independent_verify.py REPO_DIR PLAN_HASH PLAN_PATH"}))
        sys.exit(2)

    repo_dir, expected_plan_hash, plan_path = sys.argv[1:]
    repo_root = os.path.realpath(repo_dir)

    try:
        with open(plan_path, encoding="utf-8") as f:
            plan_record = json.load(f)
        expected_paths = plan_record.get("expected_paths")
        expected_candidate_hash = plan_record.get("candidate_hash")
        backend_name = plan_record.get("backend_name")
        plan_payload = plan_record.get("plan")

        if not isinstance(expected_paths, list) or not expected_paths:
            raise ValueError("expected_paths must be a non-empty list")
        if any(not isinstance(p, str) or not p for p in expected_paths):
            raise ValueError("expected_paths contains a non-string or empty path")
        if expected_paths != sorted(set(expected_paths)):
            raise ValueError("expected_paths must be sorted and unique")
        if not isinstance(expected_candidate_hash, str) or not expected_candidate_hash:
            raise ValueError("candidate_hash is missing")
        if not isinstance(backend_name, str) or not backend_name:
            raise ValueError("backend_name is missing")
        if not isinstance(plan_payload, dict):
            raise ValueError("typed compilation plan is missing")

        files: dict[str, str] = {}
        missing_paths: list[str] = []
        for relative_path in expected_paths:
            if os.path.isabs(relative_path):
                raise ValueError(f"absolute generated path is forbidden: {relative_path!r}")
            full_path = os.path.realpath(os.path.join(repo_root, relative_path))
            if os.path.commonpath((repo_root, full_path)) != repo_root:
                raise ValueError(f"generated path escapes candidate workspace: {relative_path!r}")
            if not os.path.isfile(full_path):
                missing_paths.append(relative_path)
                continue
            with open(full_path, encoding="utf-8") as fh:
                files[relative_path] = fh.read()

        from compiler.core.repository import build_repository
        from compiler.core.plan import CompilationPlan
        from compiler.composition import build_backend_registry

        generated_repo = build_repository(files)
        plan_hash_computed = hashlib.sha256(
            json.dumps(expected_paths).encode("utf-8")
        ).hexdigest()
        plan_match = plan_hash_computed == expected_plan_hash
        files_complete = not missing_paths and len(files) == len(expected_paths)
        candidate_match = (
            generated_repo.content_hash == expected_candidate_hash
        )

        typed_plan = CompilationPlan.model_validate(plan_payload)
        backend = build_backend_registry().get(backend_name)
        conformance = backend.conformance(typed_plan, generated_repo)
        conformance_passed = getattr(conformance, "passed", False) is True

        result = {
            "independent": True,
            "repo_hash": generated_repo.content_hash,
            "candidate_hash_expected": expected_candidate_hash,
            "candidate_hash_computed": generated_repo.content_hash,
            "candidate_match": candidate_match,
            "plan_match": plan_match,
            "files_found": len(files),
            "files_expected": len(expected_paths),
            "missing_paths": missing_paths,
            "files_complete": files_complete,
            "backend_name": backend_name,
            "conformance_passed": conformance_passed,
            "conformance_findings": list(getattr(conformance, "findings", ()) or ()),
        }
        print(json.dumps(result, sort_keys=True))
        sys.exit(0 if plan_match and files_complete and candidate_match and conformance_passed else 1)
    except Exception as exc:
        print(json.dumps({
            "independent": True,
            "passed": False,
            "error": f"{type(exc).__name__}: {exc}",
        }, sort_keys=True))
        sys.exit(1)


if __name__ == "__main__":
    main()
