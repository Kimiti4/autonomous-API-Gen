from __future__ import annotations

from typing import Optional

from constitutional_architecture.compiler.pass_interface import CompilerPass


class PassRegistry:
    def __init__(self) -> None:
        self._passes: dict[str, CompilerPass] = {}
        self._execution_order: list[str] = []

    def register(self, pass_instance: CompilerPass, index: int | None = None) -> None:
        pid = pass_instance.identifier
        self._passes[pid] = pass_instance
        if index is not None:
            self._execution_order.insert(index, pid)
        elif pid not in self._execution_order:
            self._execution_order.append(pid)

    def get(self, identifier: str) -> Optional[CompilerPass]:
        return self._passes.get(identifier)

    def resolve_dependencies(self) -> list[str]:
        resolved: list[str] = []
        visited: set[str] = set()

        def visit(pid: str) -> None:
            if pid in resolved:
                return
            if pid in visited:
                return
            visited.add(pid)
            pass_inst = self._passes.get(pid)
            if pass_inst:
                for dep in pass_inst.dependencies:
                    if dep in self._passes:
                        visit(dep)
            if pid not in resolved:
                resolved.append(pid)

        for pid in self._execution_order:
            visit(pid)

        return resolved

    @property
    def resolved_order(self) -> list[str]:
        return self.resolve_dependencies()

    @property
    def identifiers(self) -> list[str]:
        return list(self._passes.keys())

    @property
    def count(self) -> int:
        return len(self._passes)
