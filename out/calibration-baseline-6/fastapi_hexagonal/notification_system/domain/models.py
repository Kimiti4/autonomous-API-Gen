from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Notification(BaseModel):
    id: str
    name: Optional[str] = None
    quantity: int
    price: Optional[float] = None

class NotificationLedger(BaseModel):
    id: str
    reference_id: str
