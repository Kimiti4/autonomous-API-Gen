from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class InventoryCreate(BaseModel):
    quantity: Optional[int] = None
    name: str
