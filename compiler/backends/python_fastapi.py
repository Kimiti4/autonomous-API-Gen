"""PythonFastAPIBackend — reference Python/FastAPI backend (ADR-012)."""
from __future__ import annotations
from compiler.core.plan import CompilationPlan
from compiler.core.repository import GeneratedRepository, build_repository
from compiler.core.conformance import CHECKER, ConformanceReport


class PythonFastAPIBackend:
    name = "python-fastapi"
    language = "python"
    framework = "fastapi"
    version = "1.4.0"

    def element_paths(self, plan: CompilationPlan) -> dict[str, str]:
        p: dict[str, str] = {}
        for s in plan.services:
            n = s.name
            p[s.id] = f"app/application/{n}.py"
            for mp in s.data_models:
                p[mp.id] = f"app/domain/{mp.entity_name}.py"
            for ev in s.published_events + s.consumed_events:
                p[ev.id] = f"app/events/{ev.name}.py"
        for sp in plan.security:
            p[sp.policy_id] = "app/core/security.py"
        p.update({
            "infra:docker": "Dockerfile",
            "infra:k8s": "k8s/deployment.yaml",
            "infra:ci": ".github/workflows/ci.yml",
            "infra:readme": "README.md",
            "infra:main": "app/main.py",
            "infra:repositories": "app/infrastructure/repositories.py",
            "infra:docs": "docs/architecture.md",
        })
        return p

    def compile(self, plan: CompilationPlan) -> GeneratedRepository:
        f: dict[str, str] = {}
        for pid, path in self.element_paths(plan).items():
            f[path] = self._emit(pid, plan)
        return build_repository(f)

    def conformance(self, plan: CompilationPlan, repo: GeneratedRepository) -> ConformanceReport:
        return CHECKER.check(plan, self.element_paths(plan), repo)

    def _emit(self, pid: str, plan: CompilationPlan) -> str:
        if pid.startswith("infra:"):
            return {
                "infra:docker": "FROM python:3.12-slim\nCOPY . /app\n",
                "infra:k8s": "kind: Deployment\n",
                "infra:ci": "name: ci\non: [push]\n",
                "infra:readme": "# python-fastapi\n",
                "infra:main": "from fastapi import FastAPI\napp=FastAPI()\n",
                "infra:repositories": "# repository pattern\n",
                "infra:docs": "# ISR-derived\n",
            }[pid]
        if "domain" in pid:
            return "class Entity:\n    pass\n"
        if pid.startswith("event:") or pid.startswith("api:"):
            return "# handler\n"
        if pid.startswith("sec:"):
            return "# oauth2\n"
        return f"# service {pid}\n"
