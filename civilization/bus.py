"""
Communication bus for engineering organizations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .utils import deterministic_id, utcnow


class CommunicationMessage(BaseModel):
    """Message published on the civilization communication bus."""

    id: str

    topic: str

    organization_id: Optional[str] = None
    task_id: Optional[str] = None
    sender_agent_id: Optional[str] = None

    payload: Dict[str, Any] = Field(default_factory=dict)

    created_at: str


class InMemoryCommunicationBus:
    """In-memory communication bus."""

    def __init__(self) -> None:
        self.messages: List[CommunicationMessage] = []

    def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        organization_id: Optional[str] = None,
        task_id: Optional[str] = None,
        sender_agent_id: Optional[str] = None,
    ) -> CommunicationMessage:
        created_at = utcnow().isoformat()

        message_id = deterministic_id(
            "communication_message",
            {
                "topic": topic,
                "organization_id": organization_id,
                "task_id": task_id,
                "sender_agent_id": sender_agent_id,
                "created_at": created_at,
                "message_count": len(self.messages),
            },
        )

        message = CommunicationMessage(
            id=message_id,
            topic=topic,
            organization_id=organization_id,
            task_id=task_id,
            sender_agent_id=sender_agent_id,
            payload=payload,
            created_at=created_at,
        )

        self.messages.append(message)

        return message

    def list_messages(
        self,
        topic: Optional[str] = None,
        task_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[CommunicationMessage]:
        results: List[CommunicationMessage] = []

        for message in reversed(self.messages):
            if topic and message.topic != topic:
                continue

            if task_id and message.task_id != task_id:
                continue

            if organization_id and message.organization_id != organization_id:
                continue

            results.append(message)

            if len(results) >= limit:
                break

        return results
