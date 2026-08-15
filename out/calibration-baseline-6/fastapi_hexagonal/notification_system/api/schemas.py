from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class NotificationCreate(BaseModel):
    name: Optional[str] = None
    quantity: int
    price: Optional[float] = None

class NotificationLedgerCreate(BaseModel):
    reference_id: str
