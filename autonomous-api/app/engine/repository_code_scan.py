"""Evidence-first repository/codebase health scanning for ESAP.

The scanner identifies candidate bugs and code-quality ("jagged code") findings.
It does not mutate source. Findings must enter the existing governed repair path.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Iterable


@dataclass(frozen=True)
class CodeFinding:
    finding_id: str
    category: str
    severity: str
    path: str
    line: int
    rule: str
    message: str
    evidence: tuple[str, ...]
    repairable: bool

    @property
    def digest(self) -> str:
        raw = "|".join((
            self.finding_id, self.category, self.severity, self.path,
            str(self.line), self.rule, self.message, *self.evidence,
        ))
        return sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class RepositoryScan:
    root: str
    findings: tuple[CodeFinding, ...]
    files_scanned: int
    digest: str


def scan_repository(files: Iterable[tuple[str, str]], *, root: str = ".") -> RepositoryScan:
    """Scan supplied source files deterministically; never executes them."""
    findings: list[CodeFinding] = []
    count = 0
    for path, source in sorted(files, key=lambda x: x[0]):
        count += 1
        lines = source.splitlines()
        for number, line in enumerate(lines, 1):
            stripped = line.strip()
            if "TODO" in stripped or "FIXME" in stripped:
                findings.append(_finding(path, number, "code-smell", "low", "unfinished-marker", stripped, True))
            if re.search(r"except\\s*:\\s*$", stripped):
                findings.append(_finding(path, number, "bug-risk", "high", "bare-except", stripped, True))
            if re.search(r"except Exception\\s*:", stripped):
                findings.append(_finding(path, number, "bug-risk", "medium", "broad-exception", stripped, True))
            if "pass  # stub" in stripped.lower():
                findings.append(_finding(path, number, "code-smell", "high", "stub-pass", stripped, True))
    canonical = "\n".join(f"{f.digest}" for f in findings)
    digest = sha256((root + "|" + str(count) + "|" + canonical).encode()).hexdigest()
    return RepositoryScan(root, tuple(findings), count, digest)


def _finding(path, line, category, severity, rule, message, repairable):
    finding_id = sha256(f"{path}:{line}:{rule}:{message}".encode()).hexdigest()[:20]
    return CodeFinding(
        finding_id, category, severity, path, line, rule, message,
        (f"{path}:{line}", message), repairable,
    )
