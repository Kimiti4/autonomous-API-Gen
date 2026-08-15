"""
Phase 7/12: Compiler Backends.

Compilers are the ONLY place where framework-specific syntax exists.
They implement a strict IFrontendCompiler interface.
The core engine remains technology-agnostic — frameworks are confined here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from constitutional_architecture.isr.profiles.frontend_model import FrontendISRProfile


@dataclass(frozen=True)
class CompiledArtifact:
    format: str
    content: str
    dependencies: tuple[str, ...] = ()


class IFrontendCompiler(ABC):
    @abstractmethod
    def compile_tokens(self, profile: FrontendISRProfile) -> CompiledArtifact:
        ...

    @abstractmethod
    def compile_component(self, profile: FrontendISRProfile, component_id: str) -> CompiledArtifact:
        ...


class TailwindCompiler(IFrontendCompiler):
    def compile_tokens(self, profile: FrontendISRProfile) -> CompiledArtifact:
        tokens = profile.design_system.tokens
        theme: dict[str, Any] = {"extend": {}}

        if "color" in tokens:
            colors = {}
            for tid, token in tokens["color"].items():
                base = token.base_value
                if isinstance(base, str) and base.startswith("hsl("):
                    colors[tid] = base
                else:
                    colors[tid] = base
            theme["extend"]["colors"] = colors

        if "spacing" in tokens:
            spacing = {}
            for tid, token in tokens["spacing"].items():
                val = token.base_value
                spacing[tid.replace("space-", "")] = val
            theme["extend"]["spacing"] = spacing

        if "typography" in tokens:
            fonts = {}
            for tid, token in tokens["typography"].items():
                val = token.base_value
                if isinstance(val, (int, float)):
                    fonts[tid.replace("text-", "")] = f"{val}px"
                else:
                    fonts[tid.replace("text-", "")] = str(val)
            theme["extend"]["fontSize"] = fonts

        content = f"module.exports = {{\n  theme: {_format_json(theme, 2)}\n}};"
        return CompiledArtifact(
            format="tailwind-config",
            content=content,
            dependencies=("tailwindcss",),
        )

    def compile_component(self, profile: FrontendISRProfile, component_id: str) -> CompiledArtifact:
        comp = None
        for c in profile.components:
            if c.id == component_id:
                comp = c
                break
        if not comp:
            return CompiledArtifact(
                format="error",
                content=f"Component '{component_id}' not found in profile",
            )
        lines: list[str] = []
        lines.append(f"<!-- {comp.name} (evolved by FEE) -->")
        lines.append(f"<div class=\"{comp.id}\">")
        lines.append(f"  <!-- purpose: {comp.purpose} -->")
        for state in comp.states:
            lines.append(f"  <!-- state: {state} -->")
        if comp.allowed_children:
            lines.append(f"  <!-- slots: {', '.join(comp.allowed_children)} -->")
        lines.append("</div>")
        return CompiledArtifact(
            format="html-skeleton",
            content="\n".join(lines),
            dependencies=(),
        )


def _format_json(obj: Any, indent: int = 0) -> str:
    prefix = " " * indent
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        items = [f'{prefix}  "{k}": {_format_json(v, indent + 2)}' for k, v in obj.items()]
        return "{\n" + ",\n".join(items) + f"\n{prefix}}}"
    elif isinstance(obj, str):
        return f'"{obj}"'
    elif isinstance(obj, bool):
        return "true" if obj else "false"
    elif obj is None:
        return "null"
    else:
        return str(obj)
