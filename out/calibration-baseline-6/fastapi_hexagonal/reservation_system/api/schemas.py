from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ReservationCreate(BaseModel):
    name: str
    quantity: Optional[int] = None
