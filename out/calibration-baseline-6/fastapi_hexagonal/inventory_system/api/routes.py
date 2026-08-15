from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response

from inventory_system.api.schemas import InventoryCreate
from inventory_system.application.services import InventoryService
from inventory_system.domain.models import Inventory


def build_inventory_router(service: InventoryService, auth_dependency) -> APIRouter:
    router = APIRouter(
        prefix="/inventories",
        tags=["inventories"],
        dependencies=[Depends(auth_dependency)],
    )

    @router.get("", response_model=List[Inventory])
    def list_inventory() -> List[Inventory]:
        return service.list()

    @router.post("", response_model=Inventory, status_code=201)
    def create_inventory(payload: InventoryCreate) -> Inventory:
        return service.create(**payload.model_dump())

    @router.get("/{inventory_id}", response_model=Inventory)
    def get_inventory(inventory_id: str) -> Inventory:
        entity = service.get(inventory_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Inventory not found")
        return entity

    @router.delete("/{inventory_id}", status_code=204)
    def delete_inventory(inventory_id: str) -> Response:
        deleted = service.delete(inventory_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Inventory not found")
        return Response(status_code=204)

    return router
