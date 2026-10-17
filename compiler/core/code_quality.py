"""Deterministic, repository-bound quality inspection for generated software.

This inspector is a static evidence layer, not a claim that code is "senior-level"
or production-ready. It reports reproducible defects and explicit analysis limits.
Language-specific build, type, security, accessibility, and runtime checks remain
separate verification stages.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
from enum import Enum
from pathlib import PurePosixPath
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field

from compiler.core.repository import GeneratedRepository


class QualitySeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    BLOCKER = "blocker"


_BLOCKING = frozenset({QualitySeverity.ERROR, QualitySeverity.BLOCKER})
_SOURCE_SUFFIXES = frozenset({
    ".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte",
    ".go", ".rs", ".java", ".kt", ".cs", ".rb", ".php", ".swift", ".sql",
})
_LANGUAGE_BY_SUFFIX = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".mjs": "javascript", ".cjs": "javascript", ".ts": "typescript",
    ".tsx": "typescript", ".vue": "vue", ".svelte": "svelte",
    ".go": "go", ".rs": "rust", ".java": "java", ".kt": "kotlin",
    ".cs": "csharp", ".rb": "ruby", ".php": "php", ".swift": "swift",
    ".sql": "sql",
}
_PLACEHOLDER = re.compile(r"\b(TODO|FIXME|XXX|NotImplementedError)\b")
_PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
_AWS_ACCESS_KEY = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_GITHUB_TOKEN = re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b")
_ASSERT_TRUE = re.compile(r"\bassert\s+True\b")


class QualityFinding(BaseModel):
    """One stable, machine-readable quality finding."""
    model_config = ConfigDict(frozen=True)

    rule_id: str
    severity: QualitySeverity
    message: str
    path: str = ""
    line: int | None = None


class CodeQualityReport(BaseModel):
    """Inspection outcome cryptographically bound to exact repository contents."""
    model_config = ConfigDict(frozen=True)

    repository_hash: str
    declared_repository_hash: str
    passed: bool
    file_count: int
    source_file_count: int
    analyzed_languages: list[str] = Field(default_factory=list)
    unparsed_languages: list[str] = Field(default_factory=list)
    findings: list[QualityFinding] = Field(default_factory=list)

    @property
    def blocking_findings(self) -> list[QualityFinding]:
        return [finding for finding in self.findings if finding.severity in _BLOCKING]


def _canonical_hash(files: dict[str, str]) -> str:
    canonical = json.dumps(
        {path: content for path, content in sorted(files.items())},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _safe_path(path: str) -> bool:
    if not path or "\\" in path:
        return False
    candidate = PurePosixPath(path)
    return not candidate.is_absolute() and all(part not in {"", ".", ".."} for part in path.split("/"))


class _FunctionComplexityVisitor(ast.NodeVisitor):
    """Approximate cyclomatic complexity without counting nested functions."""

    def __init__(self) -> None:
        self.complexity = 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.complexity += max(0, len(node.values) - 1)
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        self.complexity += max(0, len(node.cases) - 1)
        self.generic_visit(node)


class _PythonRiskVisitor(ast.NodeVisitor):
    def __init__(self, path: str, findings: list[QualityFinding]) -> None:
        self.path = path
        self.findings = findings

    def visit_Call(self, node: ast.Call) -> None:
        name = node.func.id if isinstance(node.func, ast.Name) else ""
        if name in {"eval", "exec"}:
            self.findings.append(QualityFinding(
                rule_id="QRY-PY-SEC-001",
                severity=QualitySeverity.ERROR,
                path=self.path,
                line=node.lineno,
                message=f"Dynamic {name}() execution requires explicit security review.",
            ))
        if isinstance(node.func, ast.Attribute) and node.func.attr in {"system", "popen"}:
            owner = node.func.value
            if isinstance(owner, ast.Name) and owner.id == "os":
                self.findings.append(QualityFinding(
                    rule_id="QRY-PY-SEC-002",
                    severity=QualitySeverity.WARNING,
                    path=self.path,
                    line=node.lineno,
                    message=f"os.{node.func.attr}() invokes a shell/process and needs input-safety review.",
                ))
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self.findings.append(QualityFinding(
                rule_id="QRY-PY-QUAL-001",
                severity=QualitySeverity.WARNING,
                path=self.path,
                line=node.lineno,
                message="Bare except catches BaseException; catch a specific exception type.",
            ))
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.findings.append(QualityFinding(
                rule_id="QRY-PY-QUAL-002",
                severity=QualitySeverity.WARNING,
                path=self.path,
                line=node.lineno,
                message="Exception is silently swallowed by an empty handler.",
            ))
        self.generic_visit(node)

    def _visit_function_defaults(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        defaults = list(node.args.defaults) + [d for d in node.args.kw_defaults if d is not None]
        for default in defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.findings.append(QualityFinding(
                    rule_id="QRY-PY-QUAL-003",
                    severity=QualitySeverity.ERROR,
                    path=self.path,
                    line=default.lineno,
                    message=f"Mutable default argument in {node.name}() can leak state across calls.",
                ))

        function_lines = (node.end_lineno or node.lineno) - node.lineno + 1
        if function_lines > 150:
            severity = QualitySeverity.ERROR
        elif function_lines > 80:
            severity = QualitySeverity.WARNING
        else:
            severity = None
        if severity:
            self.findings.append(QualityFinding(
                rule_id="QRY-PY-QUAL-004",
                severity=severity,
                path=self.path,
                line=node.lineno,
                message=f"Function {node.name} spans {function_lines} lines; split responsibilities into cohesive units.",
            ))

        complexity = _FunctionComplexityVisitor()
        for statement in node.body:
            complexity.visit(statement)
        if complexity.complexity > 25:
            severity = QualitySeverity.ERROR
        elif complexity.complexity > 15:
            severity = QualitySeverity.WARNING
        else:
            severity = None
        if severity:
            self.findings.append(QualityFinding(
                rule_id="QRY-PY-QUAL-005",
                severity=severity,
                path=self.path,
                line=node.lineno,
                message=f"Function {node.name} has estimated cyclomatic complexity {complexity.complexity}; decompose decision paths.",
            ))

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function_defaults(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function_defaults(node)


class CodeQualityInspector:
    """Inspect generated files without assuming a specific application domain.

    Errors and blockers fail the report. Warnings remain visible but do not
    silently become proof of correctness. Unsupported languages are disclosed.
    """

    def inspect(
        self,
        repository: GeneratedRepository | Mapping[str, str],
        *,
        declared_content_hash: str | None = None,
        require_complete_language_analysis: bool = False,
    ) -> CodeQualityReport:
        """Inspect either a canonical repository or any compiler's file mapping.

        A GeneratedRepository must carry its own correct hash. For compiler
        outputs that expose only a file mapping, the inspector computes the
        binding hash from the exact supplied mapping; callers may additionally
        supply a generator-declared hash to cross-check it.
        """
        findings: list[QualityFinding] = []
        if isinstance(repository, GeneratedRepository):
            files = repository.files
            declared_hash = repository.content_hash
            if declared_hash and declared_hash != _canonical_hash(files):
                findings.append(QualityFinding(
                    rule_id="QRY-INT-001",
                    severity=QualitySeverity.BLOCKER,
                    message="Repository content hash does not match the supplied file contents.",
                ))
            if not declared_hash:
                findings.append(QualityFinding(
                    rule_id="QRY-INT-002",
                    severity=QualitySeverity.BLOCKER,
                    message="Repository is missing its content hash; quality evidence cannot be bound to an identity.",
                ))
        else:
            files = dict(repository)
            declared_hash = declared_content_hash or _canonical_hash(files)
            if declared_content_hash and declared_content_hash != _canonical_hash(files):
                findings.append(QualityFinding(
                    rule_id="QRY-INT-001",
                    severity=QualitySeverity.BLOCKER,
                    message="Declared compiler-output hash does not match the supplied file contents.",
                ))
        actual_hash = _canonical_hash(files)

        seen_casefolded: dict[str, str] = {}
        source_files = 0
        languages: set[str] = set()
        analyzable_languages: set[str] = set()

        for path, content in sorted(files.items()):
            if not _safe_path(path):
                findings.append(QualityFinding(
                    rule_id="QRY-ART-001",
                    severity=QualitySeverity.BLOCKER,
                    path=path,
                    message="Artifact path is absolute, traverses directories, or uses a non-portable separator.",
                ))
            normalized = path.casefold()
            previous = seen_casefolded.get(normalized)
            if previous is not None and previous != path:
                findings.append(QualityFinding(
                    rule_id="QRY-ART-002",
                    severity=QualitySeverity.ERROR,
                    path=path,
                    message=f"Artifact path collides case-insensitively with {previous!r}.",
                ))
            seen_casefolded[normalized] = path

            # Scan every artifact, including config and workflow files, for secrets.
            for match in _PRIVATE_KEY.finditer(content):
                findings.append(QualityFinding(
                    rule_id="QRY-SEC-001",
                    severity=QualitySeverity.BLOCKER,
                    path=path,
                    line=content.count("\n", 0, match.start()) + 1,
                    message="Private-key material appears in generated artifacts; remove and rotate the exposed key.",
                ))
            for pattern, rule_id, label in (
                (_AWS_ACCESS_KEY, "QRY-SEC-002", "AWS access-key identifier"),
                (_GITHUB_TOKEN, "QRY-SEC-003", "GitHub token"),
            ):
                for match in pattern.finditer(content):
                    findings.append(QualityFinding(
                        rule_id=rule_id,
                        severity=QualitySeverity.BLOCKER,
                        path=path,
                        line=content.count("\n", 0, match.start()) + 1,
                        message=f"Possible hard-coded {label} detected.",
                    ))

            suffix = PurePosixPath(path).suffix.lower()
            if suffix not in _SOURCE_SUFFIXES:
                continue
            long_lines = [index for index, line in enumerate(content.splitlines(), start=1) if len(line) > 120]
            for line_number in long_lines:
                findings.append(QualityFinding(
                    rule_id="QRY-QUAL-006",
                    severity=QualitySeverity.WARNING,
                    path=path,
                    line=line_number,
                    message="Line exceeds 120 characters; consider extracting or reformatting for readability.",
                ))

            source_files += 1
            language = _LANGUAGE_BY_SUFFIX[suffix]
            languages.add(language)

            if not content.strip():
                findings.append(QualityFinding(
                    rule_id="QRY-ART-003",
                    severity=QualitySeverity.ERROR,
                    path=path,
                    message="Source artifact is empty.",
                ))
                continue

            for match in _PLACEHOLDER.finditer(content):
                findings.append(QualityFinding(
                    rule_id="QRY-QUAL-001",
                    severity=QualitySeverity.WARNING if match.group(1) != "NotImplementedError" else QualitySeverity.ERROR,
                    path=path,
                    line=content.count("\n", 0, match.start()) + 1,
                    message=f"Unresolved implementation marker {match.group(1)!r} remains in a source artifact.",
                ))

            if suffix == ".py":
                analyzable_languages.add("python")
                try:
                    tree = ast.parse(content, filename=path)
                except SyntaxError as exc:
                    findings.append(QualityFinding(
                        rule_id="QRY-SYNTAX-PY-001",
                        severity=QualitySeverity.ERROR,
                        path=path,
                        line=exc.lineno,
                        message=f"Python syntax error: {exc.msg}.",
                    ))
                else:
                    _PythonRiskVisitor(path, findings).visit(tree)

            if "test" in path.casefold() and _ASSERT_TRUE.search(content):
                for match in _ASSERT_TRUE.finditer(content):
                    findings.append(QualityFinding(
                        rule_id="QRY-TEST-001",
                        severity=QualitySeverity.ERROR,
                        path=path,
                        line=content.count("\n", 0, match.start()) + 1,
                        message="Test contains 'assert True', which does not verify application behavior.",
                    ))

        unparsed = languages - analyzable_languages
        if require_complete_language_analysis and unparsed:
            findings.append(QualityFinding(
                rule_id="QRY-COVERAGE-001",
                severity=QualitySeverity.BLOCKER,
                message="No language-specific parser was run for: " + ", ".join(sorted(unparsed)),
            ))

        findings.sort(key=lambda f: (f.path, f.line or 0, f.rule_id, f.message))
        return CodeQualityReport(
            repository_hash=actual_hash,
            declared_repository_hash=declared_hash,
            passed=not any(f.severity in _BLOCKING for f in findings),
            file_count=len(files),
            source_file_count=source_files,
            analyzed_languages=sorted(analyzable_languages),
            unparsed_languages=sorted(unparsed),
            findings=findings,
        )
