from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response

from order_system.api.schemas import OrderCreate
from order_system.application.services import OrderService
from order_system.domain.models import Order


def build_order_router(service: OrderService, auth_dependency) -> APIRouter:
    router = APIRouter(
        prefix="/orders",
        tags=["orders"],
        dependencies=[Depends(auth_dependency)],
    )

    @router.get("", response_model=List[Order])
    def list_order() -> List[Order]:
        return service.list()

    @router.post("", response_model=Order, status_code=201)
    def create_order(payload: OrderCreate) -> Order:
        return service.create(**payload.model_dump())

    @router.get("/{order_id}", response_model=Order)
    def get_order(order_id: str) -> Order:
        entity = service.get(order_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return entity

    @router.delete("/{order_id}", status_code=204)
    def delete_order(order_id: str) -> Response:
        deleted = service.delete(order_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Order not found")
        return Response(status_code=204)

    return router
