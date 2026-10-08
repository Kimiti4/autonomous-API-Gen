"""Framework knowledge registry.

The registry contains only compact, provenance-bearing facts and capability
metadata. It is not an expert rule engine: reasoning must retrieve, compare,
test, and update these claims rather than dispatching on framework names.
"""
from __future__ import annotations
from .framework_knowledge import FrameworkKnowledgeClaim, FrameworkKnowledgePack

def default_framework_knowledge() -> tuple[FrameworkKnowledgePack, ...]:
    return (
        FrameworkKnowledgePack(
            framework_id="angular",
            language="typescript",
            versions=("current",),
            concepts=("components","dependency-injection","signals","routing","forms","ssr","ssg","hydration"),
            capabilities={"component_ui":"strong","dependency_injection":"strong","ssr":"supported","ssg":"supported","hydration":"supported"},
            constraints=("use documented injection contexts","respect Angular version-specific APIs"),
            anti_patterns=("treating Angular as an unstructured template renderer",),
            claims=(
                FrameworkKnowledgeClaim("angular-di","Angular provides dependency injection for application dependencies.","official_docs","https://angular.dev/guide/di/dependency-injection"),
                FrameworkKnowledgeClaim("angular-inject-context","inject() is supported only in an injection context.","official_api","https://angular.dev/api/core/inject"),
                FrameworkKnowledgeClaim("angular-platform","Angular provides components, Signals, DI, routing, forms, SSR and SSG capabilities.","official_docs","https://angular.dev/docs"),
            ),
        ),
    )

def framework_knowledge(framework_id: str) -> FrameworkKnowledgePack | None:
    return next((p for p in default_framework_knowledge() if p.framework_id == framework_id), None)
