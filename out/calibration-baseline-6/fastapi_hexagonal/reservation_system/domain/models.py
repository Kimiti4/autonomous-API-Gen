from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Reservation(BaseModel):
    id: str
    name: str
    quantity: Optional[int] = None
