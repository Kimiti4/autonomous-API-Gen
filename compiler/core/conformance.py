"""ConformanceReport and backend-agnostic ConformanceChecker (ADR-012)."""
from __future__ import annotations
import ast
from pydantic import BaseModel, ConfigDict, Field
from compiler.core.plan import CompilationPlan
from compiler.core.repository import GeneratedRepository


class ConformanceReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    passed: bool
    missing: list[str] = Field(default_factory=list)


def plan_element_ids(plan: CompilationPlan) -> list[str]:
    """The full set of plan elements every backend must materialise."""
    ids: list[str] = []
    for s in plan.services:
        ids.append(s.id)
        for mp in s.data_models:
            ids.append(mp.id)
        for ev in s.published_events + s.consumed_events:
            ids.append(ev.id)
    for sp in plan.security:
        ids.append(sp.policy_id)
    ids += [
        "infra:docker", "infra:k8s", "infra:ci", "infra:readme",
        "infra:main", "infra:repositories", "infra:docs",
    ]
    return ids


_COMMENT_PREFIXES = ("#", "//", "--", ";", "<!--")


def hollow_finding(path: str, content: str) -> str | None:
    """Content floor: a present-but-hollow file is a conformance finding.

    Path presence alone certified stubs. A file counts as materialised only
    when it has real (non-comment) content, Python sources parse, and text
    bodies carry a minimal amount of substance. Returns a finding string or
    None when the content is substantive.
    """
    stripped = content.strip()
    if not stripped:
        return f"hollow:{path}:empty"
    code_lines: list[str] = []
    for line in stripped.splitlines():
        s = line.strip()
        if not s or s.startswith(_COMMENT_PREFIXES):
            continue
        code_lines.append(s)
    if not code_lines:
        return f"hollow:{path}:comment-only"
    if path.endswith(".py"):
        try:
            ast.parse(stripped)
        except SyntaxError as exc:
            return f"syntax:{path}:{exc.msg}"
    body = "\n".join(code_lines)
    if len(body) < 40:
        return f"hollow:{path}:too-sparse"
    return None


class ConformanceChecker:
    """Backend-agnostic: verifies every plan element is (a) mapped to a path by
    the backend's own layout, (b) present in the generated repository, and
    (c) carries substantive content (never a comment/placeholder stub).
    It never assumes a language or directory convention."""

    def check(
        self,
        plan: CompilationPlan,
        element_paths: dict[str, str],
        repo: GeneratedRepository,
    ) -> ConformanceReport:
        missing: list[str] = []
        for eid in plan_element_ids(plan):
            path = element_paths.get(eid)
            if not path:
                missing.append(f"unmapped:{eid}")
            elif path not in repo.files:
                missing.append(path)
            else:
                finding = hollow_finding(path, repo.files[path])
                if finding is not None:
                    missing.append(finding)
        return ConformanceReport(passed=not missing, missing=missing)


CHECKER = ConformanceChecker()
