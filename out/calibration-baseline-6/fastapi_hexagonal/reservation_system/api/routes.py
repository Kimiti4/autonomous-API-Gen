from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response

from reservation_system.api.schemas import ReservationCreate
from reservation_system.application.services import ReservationService
from reservation_system.domain.models import Reservation


def build_reservation_router(service: ReservationService, auth_dependency) -> APIRouter:
    router = APIRouter(
        prefix="/reservations",
        tags=["reservations"],
        dependencies=[Depends(auth_dependency)],
    )

    @router.get("", response_model=List[Reservation])
    def list_reservation() -> List[Reservation]:
        return service.list()

    @router.post("", response_model=Reservation, status_code=201)
    def create_reservation(payload: ReservationCreate) -> Reservation:
        return service.create(**payload.model_dump())

    @router.get("/{reservation_id}", response_model=Reservation)
    def get_reservation(reservation_id: str) -> Reservation:
        entity = service.get(reservation_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Reservation not found")
        return entity

    @router.delete("/{reservation_id}", status_code=204)
    def delete_reservation(reservation_id: str) -> Response:
        deleted = service.delete(reservation_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Reservation not found")
        return Response(status_code=204)

    return router
