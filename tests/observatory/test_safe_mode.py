"""Safe-mode enforcement tests: only safe_mode_disable passes while enabled."""
from __future__ import annotations

import asyncio
import os
import tempfile
import unittest

from observatory.backend.bus import AsyncEventBus
from observatory.backend.domain import (
    Actor, CommandRequest, new_governance_event)
from observatory.backend.gateway import ObservatoryGateway
from observatory.backend.governance import AuthorizationError
from observatory.backend.store import SqliteEventStore

OPERATOR = Actor(id="op-1", role="operator", clearance="operator")


def _gateway(testcase: unittest.TestCase) -> ObservatoryGateway:
    tmp = tempfile.TemporaryDirectory()
    testcase.addCleanup(tmp.cleanup)
    store = SqliteEventStore(os.path.join(tmp.name, "obs.sqlite3"))
    store.init()
    testcase.addCleanup(store.close)
    return ObservatoryGateway(store=store, bus=AsyncEventBus())


class SafeMode(unittest.TestCase):
    def _enable_safe_mode(self, gateway: ObservatoryGateway) -> None:
        async def scenario():
            await gateway.observe(new_governance_event(
                source="test", type="safe_mode_enabled",
                subject_id="GOVERNANCE"))
        asyncio.run(scenario())

    def test_commands_blocked_in_safe_mode(self):
        gateway = _gateway(self)
        self._enable_safe_mode(gateway)

        async def scenario():
            with self.assertRaises(AuthorizationError):
                await gateway.request_command(
                    CommandRequest(action="request_implementation",
                                   params={"target_id": "EV-1"}),
                    OPERATOR)

        asyncio.run(scenario())

    def test_safe_mode_disable_passes(self):
        gateway = _gateway(self)
        self._enable_safe_mode(gateway)

        async def scenario():
            result = await gateway.request_command(
                CommandRequest(action="safe_mode_disable", params={}),
                OPERATOR)
            return result

        result = asyncio.run(scenario())
        self.assertEqual(result["status"], "pending")

    def test_rejection_audited(self):
        gateway = _gateway(self)
        self._enable_safe_mode(gateway)

        async def scenario():
            try:
                await gateway.request_command(
                    CommandRequest(action="request_implementation",
                                   params={"target_id": "EV-1"}),
                    OPERATOR)
            except AuthorizationError:
                pass
            governance = await gateway.governance()
            return governance

        governance = asyncio.run(scenario())
        self.assertEqual(governance["command_activity"]["rejected"], 1)

    def test_normal_operation_unaffected(self):
        gateway = _gateway(self)

        async def scenario():
            result = await gateway.request_command(
                CommandRequest(action="safe_mode_enable", params={}),
                OPERATOR)
            return result

        result = asyncio.run(scenario())
        self.assertEqual(result["status"], "pending")


if __name__ == "__main__":
    unittest.main()
