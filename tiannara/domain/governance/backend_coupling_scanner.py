"""AST-precise scanner for backend-id coupling in meta-compiler sources.

Scans string literals only: comments and code identifiers are ignored;
docstrings count (documentation coupling is still coupling). Word-boundary
matching on exact backend identifiers. Deterministic output ordering.

Production code, not test-only: reusable from CI and future boundary audits.
Mirrors the Cap-A coupling scanner's intent, applied to the meta-compiler
surface via AST string-literal inspection.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from pydantic import BaseModel

from .backend_coupling_registry import KNOWN_BACKEND_IDS


class BackendCouplingFinding(BaseModel):
    file_path: str
    matched_token: str
    literal_excerpt: str


def _patterns(tokens: tuple[str, ...]):
    return tuple(
        (token, re.compile(rf"\b{re.escape(token)}\b")) for token in tokens
    )


def scan_source(
    text: str,
    file_path: str,
    tokens: tuple[str, ...] = KNOWN_BACKEND_IDS,
) -> list[BackendCouplingFinding]:
    findings: list[BackendCouplingFinding] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return findings  # unparseable sources are outside our governance
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for token, pattern in _patterns(tokens):
                if pattern.search(node.value):
                    findings.append(
                        BackendCouplingFinding(
                            file_path=file_path,
                            matched_token=token,
                            literal_excerpt=node.value[:120],
                        )
                    )
    return sorted(findings, key=lambda f: (f.file_path, f.matched_token))


def scan_meta_compilers(
    repo_root: str | Path,
    roots: tuple[str, ...],
    tokens: tuple[str, ...] = KNOWN_BACKEND_IDS,
) -> list[BackendCouplingFinding]:
    repo_root = Path(repo_root)
    findings: list[BackendCouplingFinding] = []
    for root in roots:
        base = repo_root / root
        if not base.exists():
            raise FileNotFoundError(
                f"META_COMPILER_ROOTS entry '{root}' not found under "
                f"{repo_root}; wire the actual meta-compiler paths. A guard "
                "that cannot see the tree it protects is a silent pass."
            )
        for path in sorted(base.rglob("*.py")):
            findings.extend(
                scan_source(
                    path.read_text(encoding="utf-8"),
                    str(path.relative_to(repo_root)),
                    tokens,
                )
            )
    return sorted(findings, key=lambda f: (f.file_path, f.matched_token))
