#!/usr/bin/env python3
"""Static scan: no module in certification/, evolution/, or compiler/ writes to
generated-repo files as remediation.

This enforces the no-direct-repair rule: generated code failures flow to
ISR/genome evolution, never to AI code patching.
"""
from __future__ import annotations
import ast
import os
import sys

SCAN_DIRS = ["certification", "evolution", "compiler"]

FORBIDDEN_PATTERNS = [
    "open(",
    "write(",
    "writelines(",
    "Path(",
    "shutil.copy",
    "shutil.move",
]

WRITE_MODES = {"w", "wb", "w+", "wt", "a", "ab", "a+", "at"}


def _scan_file(path: str) -> list[str]:
    violations: list[str] = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception:
        return violations

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return violations

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "open":
            for arg in node.args[1:]:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if arg.value in WRITE_MODES or any(m in arg.value for m in WRITE_MODES):
                        violations.append(f"{path}:{node.lineno}: open() with write mode '{arg.value}'")
        if isinstance(func, ast.Attribute) and func.attr in ("write", "writelines"):
            violations.append(f"{path}:{node.lineno}: {func.attr}() call")


def run_scan() -> list[str]:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    violations: list[str] = []
    for scan_dir in SCAN_DIRS:
        dirpath = os.path.join(root, scan_dir)
        if not os.path.isdir(dirpath):
            continue
        for dirpathwalk, _, filenames in os.walk(dirpath):
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                full = os.path.join(dirpathwalk, fn)
                violations.extend(_scan_file(full))
    return violations


def main() -> int:
    violations = run_scan()
    if violations:
        print(f"VIOLATIONS: {len(violations)} found")
        for v in violations:
            print(f"  {v}")
        return 1
    print("OK: no write-as-remediation patterns found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
