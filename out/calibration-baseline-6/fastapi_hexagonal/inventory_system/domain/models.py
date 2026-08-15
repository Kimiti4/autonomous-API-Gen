from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Inventory(BaseModel):
    id: str
    quantity: Optional[int] = None
    name: str
