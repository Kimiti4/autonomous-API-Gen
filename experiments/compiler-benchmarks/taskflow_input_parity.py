"""Fail-closed preflight for proposed cross-compiler TaskFlow input parity.

This module validates a parity *declaration*, not truth of its claims. It does
not resolve semantics, authenticate reviewer evidence, run either compiler, or
qualify a compiler pair. Independent evidence is required for those steps.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tiannara.domain.models.semantic_resolution import TASKFLOW_MANDATORY_FIELDS

SCHEMA = "tiannara.compiler-benchmark.taskflow-input-parity.v1"
REQUIRED_TOP_LEVEL_HASHES = ("problem_sha256", "acceptance_sha256", "resolution_record_sha256")


def evaluate_input_parity(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return a fail-closed parity assessment for two compiler input declarations.

    Expected manifest shape:
      source_hashes: {problem_sha256, acceptance_sha256, resolution_record_sha256}
      compilers: [{compiler_id, implementation_id, fields: {field_path:
        {status: "RESOLVED", semantic_value_sha256: "...", consumer_binding: "..."}}}]

    A matching digest is only a claim until its source and downstream consumer
    are independently inspected. Therefore this function never returns a
    qualified status.
    """
    blockers: list[str] = []
    sources = manifest.get("source_hashes")
    if not isinstance(sources, dict):
        sources = {}
        blockers.append("source_hashes must be an object")
    for key in REQUIRED_TOP_LEVEL_HASHES:
        value = sources.get(key)
        if not isinstance(value, str) or not value.strip():
            blockers.append(f"missing canonical input hash: {key}")

    compilers = manifest.get("compilers")
    if not isinstance(compilers, list) or len(compilers) != 2:
        compilers = []
        blockers.append("exactly two compiler input declarations are required")
    ids = []
    for index, compiler in enumerate(compilers):
        if not isinstance(compiler, dict):
            blockers.append(f"compiler declaration {index} must be an object")
            continue
        compiler_id = compiler.get("compiler_id")
        implementation_id = compiler.get("implementation_id")
        if not isinstance(compiler_id, str) or not compiler_id.strip():
            blockers.append(f"compiler declaration {index} is missing compiler_id")
        else:
            ids.append(compiler_id)
        if not isinstance(implementation_id, str) or not implementation_id.strip():
            blockers.append(f"compiler declaration {index} is missing implementation_id")
        fields = compiler.get("fields")
        if not isinstance(fields, dict):
            fields = {}
        actual = set(fields)
        required = set(TASKFLOW_MANDATORY_FIELDS)
        for path in sorted(required - actual):
            blockers.append(f"{compiler_id or index} missing mandatory field: {path}")
        for path in sorted(actual - required):
            blockers.append(f"{compiler_id or index} declares unknown field: {path}")
        for path in TASKFLOW_MANDATORY_FIELDS:
            entry = fields.get(path)
            if not isinstance(entry, dict):
                continue
            if entry.get("status") != "RESOLVED":
                blockers.append(f"{compiler_id or index} field is not resolved: {path}")
            digest = entry.get("semantic_value_sha256")
            if not isinstance(digest, str) or not digest.strip():
                blockers.append(f"{compiler_id or index} field lacks semantic value digest: {path}")
            binding = entry.get("consumer_binding")
            if not isinstance(binding, str) or not binding.strip():
                blockers.append(f"{compiler_id or index} field lacks downstream consumer binding: {path}")

    if len(ids) == 2 and ids[0] == ids[1]:
        blockers.append("compiler_id values must be distinct")
    if len(compilers) == 2 and all(isinstance(c, dict) for c in compilers):
        left, right = compilers
        if left.get("implementation_id") == right.get("implementation_id"):
            blockers.append("implementation_id values must identify distinct implementations")
        left_fields = left.get("fields") if isinstance(left.get("fields"), dict) else {}
        right_fields = right.get("fields") if isinstance(right.get("fields"), dict) else {}
        for path in TASKFLOW_MANDATORY_FIELDS:
            a, b = left_fields.get(path), right_fields.get(path)
            if isinstance(a, dict) and isinstance(b, dict):
                if a.get("semantic_value_sha256") != b.get("semantic_value_sha256"):
                    blockers.append(f"semantic value digest mismatch: {path}")

    if blockers:
        status = "BLOCKED"
    else:
        status = "PARITY_CLAIMS_MATCHED_REQUIRES_INDEPENDENT_VERIFICATION"
    return {
        "schema": SCHEMA,
        "assessment_kind": "declaration_preflight_not_qualification",
        "status": status,
        "source_hashes": {key: sources.get(key) for key in REQUIRED_TOP_LEVEL_HASHES},
        "mandatory_fields": len(TASKFLOW_MANDATORY_FIELDS),
        "compiler_ids": ids,
        "blockers": blockers,
        "generation_authorized": False,
        "compiler_pair_qualified": False,
        "limitations": [
            "This checker does not authenticate source hashes or semantic-value digests.",
            "This checker does not establish that a named consumer actually uses a field.",
            "Trusted semantic review, evidence-envelope verification, independent consumer audit, isolated workspaces, and live acceptance evidence remain separate gates.",
        ],
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSON input-parity declaration")
    args = parser.parse_args()
    try:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "BLOCKED", "blockers": [str(exc)], "generation_authorized": False, "compiler_pair_qualified": False}, indent=2))
        return 2
    report = evaluate_input_parity(payload)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] != "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())