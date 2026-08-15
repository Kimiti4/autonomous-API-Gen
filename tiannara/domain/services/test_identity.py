"""R2.7 -- content-based test identity for regression classification.

Backend-agnostic surface, kept here (domain services) so the Evolution Engine
never inspects raw pytest output directly:

  * ``parse_pytest_verbose``  -- normalize a backend's verbose test output into
    ``TestExecution`` records (name + outcome). This is the *name* layer of
    identity: it catches deletion and rename.
  * ``hash_test_body``        -- SHA-256 over the AST dump of a test function
    read from the materialized tree. This is the *content* layer: same name with
    a different body is ``CONTENT_GUTTING`` (an assertion removed while the
    test still green-lights green).
"""
from __future__ import annotations

import ast
import copy
import hashlib
import re
from pathlib import Path

from tiannara.domain.models.evidence import TestExecution, TestOutcome

#: pytest ``-v`` per-test lines look like:
#:   tests/test_x.py::test_name PASSED [ 50%]
#:   tests/test_x.py::TestFoo::test_name FAILED [100%]
#: Node ids are space-free, so the first whitespace run separates node id from
#: status. Summary / collection / progress lines never match (no bare status token).
_TEST_LINE = re.compile(
    r"^(?P<nodeid>\S+)\s+"
    r"(?P<status>PASSED|FAILED|ERROR|SKIPPED|XPASS|XFAIL)"
    r"(?:\s+\[\s*\d+%\])?\s*$"
)

#: pytest verbose statuses that aren't part of the four-outome enum collapse into:
_XPASS_AS = TestOutcome.FAILED      # expected-fail but unexpectedly passed: a regression
_XFAIL_AS = TestOutcome.SKIPPED     # expected-fail (still) -> treated as skipped

_OUTCOME_FOR = {
    "PASSED": TestOutcome.PASSED,
    "FAILED": TestOutcome.FAILED,
    "ERROR": TestOutcome.ERROR,
    "SKIPPED": TestOutcome.SKIPPED,
}


def parse_outcome(status_token: str) -> TestOutcome | None:
    if status_token in _OUTCOME_FOR:
        return _OUTCOME_FOR[status_token]
    if status_token == "XPASS":
        return _XPASS_AS
    if status_token == "XFAIL":
        return _XFAIL_AS
    return None


def parse_pytest_verbose(
    logs: str,
    tree_root: str | Path | None = None,
    attempt: int = 0,
) -> list[TestExecution]:
    """Parse pytest ``-v`` stdout into normalized ``TestExecution`` records.

    ``tree_root`` (the materialized bundle path) enables the *content* identity
    layer: each record's ``content_hash`` is pinned to the test body read from
    that tree, so a renamed-but-gutted test is still caught.
    """
    executions: list[TestExecution] = []
    for line in logs.splitlines():
        m = _TEST_LINE.match(line)
        if not m:
            continue
        nodeid = m.group("nodeid")
        outcome = parse_outcome(m.group("status"))
        if outcome is None:
            continue
        content_hash = hash_test_body(tree_root, nodeid) if tree_root else ""
        executions.append(
            TestExecution(
                test_id=nodeid,
                outcome=outcome,
                content_hash=content_hash,
                attempt=attempt,
                flaky=False,
            )
        )
    return executions


def _find_chain(root: ast.AST, chain: list[str]) -> ast.AST | None:
    """Descend a node-id name chain (``TestFoo`` -> ``test_x``) through the AST."""
    node: ast.AST | None = root
    for name in chain:
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
            return None
        nxt: ast.AST | None = None
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if getattr(child, "name", None) == name:
                    nxt = child
                    break
        node = nxt
        if node is None:
            return None
    return node


def hash_test_body(tree_root: str | Path | None, nodeid: str) -> str:
    """SHA-256 over the AST dump of the test identified by ``nodeid``.

    AST-dumping (not raw source) normalizes whitespace/comments so a
    formatting-only change does not look like a body change, while any change
    to names, arguments, or assertions mutates the hash. Empty when the body
    can't be resolved (e.g. no tree pinned) -- the name layer still applies.
    """
    if not tree_root:
        return ""
    parts = nodeid.split("::")
    if len(parts) < 2:
        return ""
    rel_file = parts[0]
    chain = parts[1:]
    path = Path(tree_root) / rel_file
    if not path.exists():
        return ""
    try:
        tree = ast.parse(path.read_text("utf-8", "replace"))
    except SyntaxError:
        return ""
    node = _find_chain(tree, chain)
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return ""
    return sha256_ast(node)


def sha256_ast(node: ast.AST) -> str:
    """Stable hash of an AST subtree's body+assertions, excluding the name.

    The function *name* is the identity layer (a rename surfaces as REMOVED_TEST +
    NEW_PASS through the name comparator); the body+assertion content is the
    *content* layer. Blanking ``name`` means an identical body under a renamed
    function hashes identically, while any change to assertions or argument
    structure mutates the hash (gutting / deception).
    """
    n = copy.deepcopy(node)
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
        n.name = ""
    dumped = ast.dump(n, annotate_fields=False, include_attributes=False)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()
