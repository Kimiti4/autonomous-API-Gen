#!/usr/bin/env python3
"""Static scan: no module in certification/, evolution/, or compiler/ patches
generated code as remediation.

This enforces the no-direct-repair rule: generated code failures flow to
ISR/genome evolution (classify_failure), never to AI code patching.

The scan is provenance-aware: evidence outputs (ledgers, aggregates, bundles),
temp-dir materialization of fresh candidates, and .write() on handles opened
from those targets are FORWARD artifact creation (allowed). Any other
write-mode open / .write()/.writelines() is a remediation violation.
"""
from __future__ import annotations
import ast
import os
import sys

SCAN_DIRS = ["certification", "evolution", "compiler"]

WRITE_MODES = {"w", "wb", "w+", "wt", "a", "ab", "a+", "at"}

ALLOWED_PATH_CALLS = ("ledger_path_for", "aggregate_path_for", "bundle_path_for", "portpool_path_for")
EVIDENCE_LITERAL_PREFIXES = ("release/evidence", "evidence/", ".tiannara/")
TEMP_FACTORY_CALLS = ("mkdtemp", "mkstemp", "TemporaryDirectory")


class _ModuleScan(ast.NodeVisitor):
    """Track variables/handles that are provably benign write targets."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.violations: list[str] = []
        self.benign_vars: set[str] = set()
        self.benign_attrs: set[str] = set()  # e.g. "self.path"
        self.param_bound_attrs: set[str] = set()  # self.attr = <plain param>
        self.benign_handles: set[str] = set()

    def _is_benign_target(self, node: ast.expr) -> bool:
        if self._is_benign_expr(node):
            return True
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            key = f"{node.value.id}.{node.attr}"
            return key in self.param_bound_attrs
        return False

    def _is_benign_expr(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value.startswith(EVIDENCE_LITERAL_PREFIXES)
        if isinstance(node, ast.Name):
            return node.id in self.benign_vars
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}" in self.benign_attrs
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name):
                if fn.id in ALLOWED_PATH_CALLS or fn.id in TEMP_FACTORY_CALLS:
                    return True
            if isinstance(fn, ast.Attribute) and fn.attr in TEMP_FACTORY_CALLS:
                return True
            return False
        return False

    def _assign_benign(self, targets: list[ast.expr], source: ast.expr) -> None:
        for t in targets:
            if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name):
                key = f"{t.value.id}.{t.attr}"
                if self._is_benign_expr(source):
                    self.benign_attrs.add(key)
                elif isinstance(source, ast.Name):
                    self.param_bound_attrs.add(key)
            elif isinstance(t, ast.Name):
                if self._is_benign_expr(source):
                    self.benign_vars.add(t.id)
                elif (isinstance(source, ast.Call)
                        and isinstance(source.func, ast.Attribute)
                        and source.func.attr == "join"
                        and any(self._is_benign_expr(a) for a in source.args)):
                    self.benign_vars.add(t.id)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Params whose default is an evidence literal are benign vars.
        nargs = len(node.args.args)
        defaults = node.args.defaults
        offset = nargs - len(defaults)
        for i, d in enumerate(defaults):
            if self._is_benign_expr(d):
                self.benign_vars.add(node.args.args[offset + i].arg)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self._assign_benign(list(node.targets), node.value)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            ctx = item.context_expr
            var = item.optional_vars
            if isinstance(var, ast.Name):
                if (isinstance(ctx, ast.Call)
                        and isinstance(ctx.func, ast.Name) and ctx.func.id == "open"):
                    mode = ""
                    for i, arg in enumerate(ctx.args):
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and i != 0:
                            mode = arg.value
                            break
                    if any(m in mode for m in WRITE_MODES) and var.id:
                        if self._is_benign_target(ctx.args[0]):
                            self.benign_handles.add(var.id)
                        else:
                            self.violations.append(
                                f"{self.path}:{node.lineno}: open() with write mode "
                                f"'{mode}' on non-evidence target"
                            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Name) and func.id == "open":
            # assign to a name: f = open(<benign>, "w")
            if node.args:
                if isinstance(node.args[0], (ast.Constant, ast.Name, ast.Call)):
                    mode = ""
                    for i, arg in enumerate(node.args):
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and i != 0:
                            mode = arg.value
                            break
                    if any(m in mode for m in WRITE_MODES) and not self._is_benign_target(node.args[0]):
                        self.violations.append(
                            f"{self.path}:{node.lineno}: open() with write mode "
                            f"'{mode}' on non-evidence target"
                        )
        # .write()/.writelines() on a handle
        if isinstance(func, ast.Attribute) and func.attr in ("write", "writelines"):
            value = func.value
            if isinstance(value, ast.Name) and value.id in self.benign_handles:
                return
            self.violations.append(
                f"{self.path}:{node.lineno}: {func.attr}() on non-evidence target"
            )


def _scan_file(path: str) -> list[str]:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception:
        return []
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return []
    scanner = _ModuleScan(path)
    scanner.visit(tree)
    seen: set[str] = set()
    unique: list[str] = []
    for v in scanner.violations:
        if v not in seen:
            seen.add(v)
            unique.append(v)
    return unique


def _repo_root() -> str:
    """Repo root = 4 dirname steps above this file
    (check_no_direct_repair.py → cbc1 → gates → release → root)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run_scan() -> list[str]:
    root = _repo_root()
    violations: list[str] = []
    for scan_dir in SCAN_DIRS:
        dirpath = os.path.join(root, scan_dir)
        if not os.path.isdir(dirpath):
            violations.append(f"{dirpath}: scan dir missing (root={root})")
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
    print("OK: no direct-repair write patterns found")
    return 0


if __name__ == "__main__":
    sys.exit(main())