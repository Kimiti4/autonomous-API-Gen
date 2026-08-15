from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Subscription(BaseModel):
    id: str
    name: Optional[str] = None

class SubscriptionLedger(BaseModel):
    id: str
    reference_id: str
