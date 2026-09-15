"""Observatory governance + gateway tests: authorization matrix, audit,
redaction, trace/explain, read purity, determinism.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
import unittest

from observatory.backend.bus import AsyncEventBus
from observatory.backend.domain import (
    Actor, CommandRequest, EpistemicStatus, EventCategory, new_event)
from observatory.backend.gateway import NotFoundError, ObservatoryGateway
from observatory.backend.governance import (
    AuthorizationError, GovernanceBoundary)
from observatory.backend.store import SqliteEventStore

OPERATOR = Actor(id="op-1", role="operator", clearance="operator")
OBSERVER = Actor(id="obs-1", role="observer", clearance="observer")
OPEN_AUTHORITY = {"implementation": "granted", "runtime": "granted",
                  "production": "none", "governance": "granted",
                  "evolution": "definition_only"}
CLOSED_AUTHORITY = {"implementation": "none", "runtime": "none",
                    "production": "none", "governance": "granted",
                    "evolution": "definition_only"}


def _event(**overrides):
    base = {"category": EventCategory.EVOLUTION, "source": "test",
            "type": "requirement_parsed",
            "subject_id": "EV-002", "payload": {"result": "success"}}
    base.update(overrides)
    return new_event(**base)


def _gateway(testcase: unittest.TestCase) -> ObservatoryGateway:
    tmp = tempfile.TemporaryDirectory()
    testcase.addCleanup(tmp.cleanup)
    store = SqliteEventStore(os.path.join(tmp.name, "obs.sqlite3"))
    store.init()
    testcase.addCleanup(store.close)
    return ObservatoryGateway(store=store, bus=AsyncEventBus())


class GovernanceMatrix(unittest.TestCase):
    def setUp(self):
        self.boundary = GovernanceBoundary()

    def test_reads_open_to_observers(self):
        self.boundary.authorize("trace", OBSERVER, OPEN_AUTHORITY)

    def test_unknown_action_rejected(self):
        with self.assertRaises(AuthorizationError):
            self.boundary.authorize("start_evolution", OPERATOR, OPEN_AUTHORITY)

    def test_command_needs_clearance(self):
        with self.assertRaises(AuthorizationError):
            self.boundary.authorize("request_implementation", OBSERVER,
                                    OPEN_AUTHORITY)

    def test_command_blocked_by_constitution(self):
        with self.assertRaises(AuthorizationError):
            self.boundary.authorize("request_implementation", OPERATOR,
                                    CLOSED_AUTHORITY)

    def test_command_allowed_when_granted(self):
        self.boundary.authorize("request_implementation", OPERATOR,
                                OPEN_AUTHORITY)

    def test_production_never_without_grant(self):
        with self.assertRaises(AuthorizationError):
            self.boundary.authorize("request_production_deploy", OPERATOR,
                                    OPEN_AUTHORITY)

    def test_definition_allowed(self):
        self.boundary.authorize("request_evolution_definition", OPERATOR,
                                CLOSED_AUTHORITY)


class GatewayBehavior(unittest.TestCase):
    def test_observe_and_trace(self):
        gateway = _gateway(self)

        async def scenario():
            await gateway.observe(_event())
            return await gateway.trace("EV-002")

        trace = asyncio.run(scenario())
        self.assertEqual(len(trace), 1)
        self.assertEqual(trace[0]["subject_id"], "EV-002")

    def test_trace_missing(self):
        gateway = _gateway(self)
        with self.assertRaises(NotFoundError):
            asyncio.run(gateway.trace("EV-nope"))

    def test_explain_evolution(self):
        gateway = _gateway(self)

        async def scenario():
            await gateway.observe(_event())
            return await gateway.explain("EV-002")

        explanation = asyncio.run(scenario())
        self.assertEqual(explanation["subject_id"], "EV-002")
        self.assertIn("decision", explanation)
        self.assertIn("unknowns", explanation)
        self.assertIn("authorization", explanation)

    async def _grant_implementation(self, gateway) -> None:
        from observatory.backend.domain import new_governance_event
        await gateway.observe(new_governance_event(
            source="test", type="authority_updated",
            subject_id="GOVERNANCE",
            payload={"authority": {"implementation": "granted"}}))

    def test_command_accepted_and_audited(self):
        gateway = _gateway(self)

        async def scenario():
            await self._grant_implementation(gateway)
            result = await gateway.request_command(
                CommandRequest(action="request_implementation",
                               params={"target_id": "EV-002"}),
                OPERATOR)
            governance = await gateway.governance()
            return result, governance

        result, governance = asyncio.run(scenario())
        self.assertEqual(result["status"], "pending")
        self.assertTrue(result["request_id"].startswith("REQ-"))
        self.assertEqual(governance["command_activity"]["requested"], 1)

    def test_command_rejected_and_audited(self):
        gateway = _gateway(self)

        async def scenario():
            with self.assertRaises(AuthorizationError):
                await gateway.request_command(
                    CommandRequest(action="request_implementation",
                                   params={"target_id": "EV-002"}),
                    OBSERVER)
            return await gateway.governance()

        governance = asyncio.run(scenario())
        self.assertEqual(governance["command_activity"]["rejected"], 1)

    def test_duplicate_request_idempotent_shape(self):
        gateway = _gateway(self)

        async def scenario():
            await self._grant_implementation(gateway)
            first = await gateway.request_command(
                CommandRequest(action="request_implementation",
                               params={"target_id": "EV-002"}),
                OPERATOR)
            second = await gateway.request_command(
                CommandRequest(action="request_implementation",
                               params={"target_id": "EV-002"}),
                OPERATOR)
            return first, second

        first, second = asyncio.run(scenario())
        for result in (first, second):
            self.assertEqual(result["status"], "pending")
            self.assertTrue(result["request_id"].startswith("REQ-"))

    def test_secret_redaction(self):
        gateway = _gateway(self)
        redacted = gateway._redact(
            {"api_token": "supersecret-value", "name": "x"})
        self.assertEqual(redacted["api_token"], "[REDACTED]")
        self.assertEqual(redacted["name"], "x")

    def test_reads_do_not_write(self):
        gateway = _gateway(self)

        async def scenario():
            await gateway.observe(_event())
            before = gateway.store.count_events()
            await gateway.dashboard()
            await gateway.overview()
            await gateway.runtime()
            await gateway.governance()
            await gateway.timeline()
            await gateway.health()
            await gateway.trace("EV-002")
            await gateway.explain("EV-002")
            return before, gateway.store.count_events()

        before, after = asyncio.run(scenario())
        self.assertEqual(before, after)

    def test_projection_determinism(self):
        gateway = _gateway(self)

        async def scenario():
            await gateway.observe(_event())
            first = await gateway.evolution("EV-002")
            second = await gateway.evolution("EV-002")
            return first, second

        first, second = asyncio.run(scenario())
        self.assertEqual(first["status"], second["status"])
        self.assertEqual(first["epistemic_state"], second["epistemic_state"])


if __name__ == "__main__":
    unittest.main()
