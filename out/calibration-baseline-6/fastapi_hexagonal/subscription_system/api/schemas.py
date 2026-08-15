from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class SubscriptionCreate(BaseModel):
    name: Optional[str] = None

class SubscriptionLedgerCreate(BaseModel):
    reference_id: str
