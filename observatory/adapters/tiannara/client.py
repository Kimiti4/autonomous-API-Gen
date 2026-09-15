"""HTTP transport to the Observatory backend (async, bounded).

Error taxonomy: timeouts/transport/5xx are retryable; 409 integrity
conflicts and other 4xx are permanent. The client never fabricates
success and never blocks the caller beyond the configured timeout.
"""
from __future__ import annotations

from typing import Any, Dict, Protocol

import httpx

from .config import TiannaraAdapterSettings


class RetryableTransportError(Exception):
    pass


class PermanentTransportError(Exception):
    pass


class ObservatoryTransport(Protocol):
    async def send_event(self, event: Dict[str, Any]) -> None:
        ...

    async def send_events(self, events: list[Dict[str, Any]]) -> None:
        ...

    async def close(self) -> None:
        ...


class HttpObservatoryTransport:
    def __init__(self, settings: TiannaraAdapterSettings) -> None:
        self._settings = settings
        headers = {
            "Content-Type": "application/json",
            "X-Actor-Id": settings.actor_id,
            "X-Actor-Role": settings.actor_role,
            "X-Actor-Clearance": "system",
        }
        if settings.api_token:
            headers["X-Observatory-Token"] = settings.api_token
        self._client = httpx.AsyncClient(
            base_url=settings.observatory_base_url,
            timeout=settings.timeout_seconds, headers=headers)

    async def send_event(self, event: Dict[str, Any]) -> None:
        try:
            response = await self._client.post("/observatory/events",
                                               json=event)
        except httpx.TimeoutException as exc:
            raise RetryableTransportError(
                "observatory request timed out") from exc
        except httpx.TransportError as exc:
            raise RetryableTransportError(
                "observatory transport error") from exc
        if response.status_code in {200, 201, 202}:
            return
        if response.status_code == 409:
            raise PermanentTransportError(
                "observatory event integrity conflict: "
                f"{response.text[:200]}")
        if 400 <= response.status_code < 500:
            raise PermanentTransportError(
                f"observatory rejected event: {response.status_code} "
                f"{response.text[:200]}")
        raise RetryableTransportError(
            f"observatory returned retryable status: {response.status_code}")

    async def send_events(self, events: list[Dict[str, Any]]) -> None:
        if not events:
            return
        try:
            response = await self._client.post(
                "/observatory/events/batch", json={"events": events})
        except httpx.TimeoutException as exc:
            raise RetryableTransportError(
                "observatory batch request timed out") from exc
        except httpx.TransportError as exc:
            raise RetryableTransportError(
                "observatory batch transport error") from exc
        if response.status_code in {200, 201, 202}:
            return
        if response.status_code == 409:
            raise PermanentTransportError(
                "observatory batch integrity conflict: "
                f"{response.text[:200]}")
        if 400 <= response.status_code < 500:
            raise PermanentTransportError(
                f"observatory rejected batch: {response.status_code} "
                f"{response.text[:200]}")
        raise RetryableTransportError(
            f"observatory returned retryable batch status: "
            f"{response.status_code}")

    async def close(self) -> None:
        await self._client.aclose()
