from __future__ import annotations

import time
from typing import Any

from constitutional_architecture.compiler.compiler_context import CompilerContext
from constitutional_architecture.compiler.pass_interface import CompilerPass
from constitutional_architecture.compiler.pass_registry import PassRegistry


class PassManager:
    def __init__(self, registry: PassRegistry) -> None:
        self._registry = registry
        self._executed: list[str] = []

    def execute_all(self, ctx: CompilerContext) -> bool:
        order = self._registry.resolved_order
        all_success = True

        for pass_id in order:
            pass_instance = self._registry.get(pass_id)
            if pass_instance is None:
                continue

            start = time.perf_counter()
            try:
                result = pass_instance.execute(ctx)
                elapsed_ms = (time.perf_counter() - start) * 1000
                ctx.record_pass_timing(pass_id, elapsed_ms)
                ctx.record_pass_metrics(pass_id, result.metrics)
                self._executed.append(pass_id)

                if not result.success:
                    all_success = False
                    ctx.diagnostics.error("COMP-PASS-001", f"Pass '{pass_id}' failed: {result.description}")

            except Exception as e:
                elapsed_ms = (time.perf_counter() - start) * 1000
                ctx.record_pass_timing(pass_id, elapsed_ms)
                ctx.diagnostics.error("COMP-PASS-002", f"Pass '{pass_id}' raised exception: {e}")
                all_success = False

        return all_success

    @property
    def executed_passes(self) -> list[str]:
        return list(self._executed)
