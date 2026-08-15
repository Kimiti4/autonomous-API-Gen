from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class PaymentCreate(BaseModel):
    payload: Optional[dict] = None
    owner_id: str
    active: Optional[bool] = None
    name: str
    price: float
    quantity: Optional[int] = None
    occurred_at: datetime
    status: Literal['active', 'pending', 'closed']
    attachment: bytes

class PaymentLedgerCreate(BaseModel):
    reference_id: str
