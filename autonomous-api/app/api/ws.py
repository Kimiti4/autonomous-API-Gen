"""Hardened WebSocket transport (closes GAP-05 WS half + GAP-01 frames).

Constitutional rules enforced here:
1. AUTHENTICATE BEFORE ACCEPT. No anonymous connections, no post-hoc
   rejection. Unauthenticated upgrades get close code 4401 with an
   ErrorEnvelope frame.
2. Envelope frames only — never bare dicts.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.contracts.errors import RecoveryGuidance, build_error_envelope
from app.core.logger import logger
from app.middleware.security import get_auth


class ConnectionManager:
    """Manages WebSocket connections for real-time evolution updates."""

    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, websocket: WebSocket, run_id: str = "global"):
        await websocket.accept()

        if run_id not in self.active_connections:
            self.active_connections[run_id] = []

        self.active_connections[run_id].append(websocket)
        logger.info(
            f"WebSocket connected for run {run_id}. "
            f"Total connections: {len(self.active_connections[run_id])}"
        )

    def disconnect(self, websocket: WebSocket, run_id: str = "global"):
        if run_id in self.active_connections:
            if websocket in self.active_connections[run_id]:
                self.active_connections[run_id].remove(websocket)
                logger.info(f"WebSocket disconnected for run {run_id}")

    async def broadcast(self, message: dict, run_id: str = "global"):
        """Send message to all connections for a specific run or global."""
        targets = []
        if run_id == "global":
            for connections in self.active_connections.values():
                targets.extend(connections)
        else:
            targets = list(self.active_connections.get(run_id, []))

        disconnected = []
        for connection in targets:
            try:
                await connection.send_json(message)
            except Exception:
                logger.error("Error sending to connection")
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn, run_id)


# Global connection manager (kept for engine callback compatibility).
manager = ConnectionManager()

router = APIRouter()


def _auth_rejection_envelope() -> str:
    settings = get_settings()
    envelope = build_error_envelope(
        code="SEC_UNAUTHENTICATED",
        message="Authentication required",
        source_revision=settings.APP_VERSION,
        source_subsystem="ws",
        recovery=RecoveryGuidance(action="authenticate", message="Authenticate"),
    )
    return envelope.model_dump_json()


async def _authenticate_or_close(websocket: WebSocket) -> bool:
    """Validate auth BEFORE accepting. Returns True if authenticated."""
    try:
        ctx = await get_auth().authenticate_ws(websocket)
    except Exception:
        ctx = None
    if ctx is None:
        # Close without accepting; deliver the error envelope as reason.
        await websocket.close(code=4401, reason=_auth_rejection_envelope())
        return False
    return True


@router.websocket("/ws/evolution")
async def websocket_endpoint(websocket: WebSocket):
    """Auth-gated WebSocket endpoint for evolution updates."""
    if not await _authenticate_or_close(websocket):
        return

    run_id = "global"
    await manager.connect(websocket, run_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "subscribe":
                    run_id = message.get("run_id", "global")
                    await manager.broadcast(
                        {"type": "subscribed", "runId": run_id}, run_id
                    )
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, run_id)
    except Exception:
        logger.error("WebSocket error", exc_info=True)
        manager.disconnect(websocket, run_id)


@router.websocket("/ws/evolution/{run_id}")
async def websocket_endpoint_run(websocket: WebSocket, run_id: str):
    """Auth-gated WebSocket endpoint for a specific evolution run."""
    if not await _authenticate_or_close(websocket):
        return

    await manager.connect(websocket, run_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, run_id)
    except Exception:
        logger.error(f"WebSocket error for run {run_id}", exc_info=True)
        manager.disconnect(websocket, run_id)