"""ConformanceReport and backend-agnostic ConformanceChecker (ADR-012)."""
from __future__ import annotations
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


class ConformanceChecker:
    """Backend-agnostic: verifies every plan element is (a) mapped to a path by
    the backend's own layout and (b) present in the generated repository.
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
        return ConformanceReport(passed=not missing, missing=missing)


CHECKER = ConformanceChecker()
