"""
Sandboxing framework for plugin execution.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from .models import SandboxPolicyISR


class SandboxViolation(Exception):
    """Raised when a plugin violates its sandbox policy."""


PluginEntrypoint = Callable[["PluginExecutionContext"], Any]


class PluginExecutionContext:
    """
    Restricted execution context passed to a plugin entrypoint.

    In a production system, this context would be enforced using process
    isolation, WASM, gVisor, seccomp, or another hard isolation mechanism.
    """

    def __init__(
        self,
        plugin_id: str,
        policy: SandboxPolicyISR,
    ) -> None:
        self.plugin_id = plugin_id
        self.policy = policy

        self.network_calls = 0
        self.isr_mutations = 0
        self.file_reads = 0
        self.file_writes = 0

    def mutate_isr(
        self,
        target: str,
        payload: Dict[str, Any],
    ) -> bool:
        """Attempt to mutate the ISR."""
        if not self.policy.allow_isr_mutation:
            raise SandboxViolation(
                f"Plugin {self.plugin_id} attempted ISR mutation without permission."
            )

        self.isr_mutations += 1

        return True

    def fetch_network(self, url: str) -> str:
        """Attempt to access the network."""
        if not self.policy.allow_network_access:
            raise SandboxViolation(
                f"Plugin {self.plugin_id} attempted network access without permission."
            )

        self.network_calls += 1

        return f"mock_response_from:{url}"

    def read_file(self, path: str) -> str:
        """Attempt to read from the file system."""
        if not self.policy.allow_file_system_access:
            raise SandboxViolation(
                f"Plugin {self.plugin_id} attempted file read without permission."
            )

        self.file_reads += 1

        return f"mock_file_content:{path}"

    def write_file(self, path: str, content: str) -> bool:
        """Attempt to write to the file system."""
        if not self.policy.allow_file_system_access:
            raise SandboxViolation(
                f"Plugin {self.plugin_id} attempted file write without permission."
            )

        self.file_writes += 1

        return True


class SandboxExecutor:
    """Executes plugin entrypoints inside a policy-enforced sandbox."""

    def execute(
        self,
        entrypoint: PluginEntrypoint,
        context: PluginExecutionContext,
    ) -> Any:
        """
        Execute a plugin entrypoint.

        Timeout and memory limits should be enforced by the underlying
        isolation runtime in production.
        """
        return entrypoint(context)
