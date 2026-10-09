"""Evidence-first repository/codebase health scanning for ESAP.

The scanner identifies candidate bugs and code-quality ("jagged code") findings.
It does not mutate source. Findings must enter the existing governed repair path.
Static heuristics are evidence-bearing candidates, not proof of a runtime defect.
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


# These patterns intentionally flag review candidates, not automatic fixes.
# They cover a real baseline-vs-repaired regression in the JamiiLink benchmark.
_JSX_LABEL_WITHOUT_FOR = re.compile(
    r"<label\\b(?![^>]*\\bhtmlFor\\s*=)[^>]*>[^<]*</label>\\s*<input\\b",
    re.IGNORECASE | re.DOTALL,
)
_CONDITIONAL_E2E_INTERACTION = re.compile(
    r"if\\s*\\(\\s*await\\s+[A-Za-z_$][\\w$]*\\.isVisible\\(\\)\\s*\\)",
)
_PERMISSIVE_ROUTE_OUTCOME = re.compile(
    r"(?:landedOnFeed|registrationSucceeded)\\s*=\\s*[^;\\n]*"
    r"(?:includes\\(\\s*['\"]/(?:register|signup)['\"]\\s*\\))",
    re.IGNORECASE,
)


def scan_repository(files: Iterable[tuple[str, str]], *, root: str = ".") -> RepositoryScan:
    """Scan supplied source files deterministically; never execute source."""
    findings: list[CodeFinding] = []
    count = 0
    for path, source in sorted(files, key=lambda x: x[0]):
        count += 1
        for number, line in enumerate(source.splitlines(), 1):
            stripped = line.strip()
            if "TODO" in stripped or "FIXME" in stripped:
                findings.append(_finding(path, number, "code-smell", "low",
                                         "unfinished-marker", stripped, True))
            if re.search(r"except\\s*:\\s*$", stripped):
                findings.append(_finding(path, number, "bug-risk", "high",
                                         "bare-except", stripped, True))
            if re.search(r"except\\s+Exception\\s*:", stripped):
                findings.append(_finding(path, number, "bug-risk", "medium",
                                         "broad-exception", stripped, True))
            if "pass  # stub" in stripped.lower():
                findings.append(_finding(path, number, "code-smell", "high",
                                         "stub-pass", stripped, True))

        # Form labels followed by sibling inputs should have an explicit
        # htmlFor/id association. Wrapped-label patterns are not flagged.
        for match in _JSX_LABEL_WITHOUT_FOR.finditer(source):
            line = source.count("\\n", 0, match.start()) + 1
            evidence = source[match.start():match.end()].replace("\\n", " ")[:240]
            findings.append(_finding(
                path, line, "accessibility-risk", "medium",
                "unassociated-jsx-label",
                "label immediately precedes an input but has no htmlFor association",
                True, evidence,
            ))

        # A conditional isVisible guard can silently skip a required E2E action.
        for match in _CONDITIONAL_E2E_INTERACTION.finditer(source):
            line = source.count("\\n", 0, match.start()) + 1
            evidence = source[match.start():match.end()]
            findings.append(_finding(
                path, line, "test-integrity-risk", "high",
                "conditional-e2e-interaction",
                "E2E interaction is conditional and may be skipped instead of failing",
                True, evidence,
            ))

        # Treating the registration page itself as an acceptable destination
        # makes a failed journey look successful.
        for match in _PERMISSIVE_ROUTE_OUTCOME.finditer(source):
            line = source.count("\\n", 0, match.start()) + 1
            evidence = source[match.start():match.end()]
            findings.append(_finding(
                path, line, "test-integrity-risk", "high",
                "permissive-registration-outcome",
                "registration journey accepts the registration page as a successful outcome",
                True, evidence,
            ))

    findings.sort(key=lambda f: (f.path, f.line, f.rule, f.finding_id))
    canonical = "\\n".join(f.digest for f in findings)
    digest = sha256((root + "|" + str(count) + "|" + canonical).encode()).hexdigest()
    return RepositoryScan(root, tuple(findings), count, digest)


def _finding(path, line, category, severity, rule, message, repairable, evidence=None):
    finding_id = sha256(f"{path}:{line}:{rule}:{message}".encode()).hexdigest()[:20]
    return CodeFinding(
        finding_id, category, severity, path, line, rule, message,
        (f"{path}:{line}", evidence or message), repairable,
    )
