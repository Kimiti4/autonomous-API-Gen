package api

import (
    "encoding/json"
    "net/http"
    "github.com/tiannara/reservation_system/internal/application"
    "github.com/tiannara/reservation_system/internal/domain"
)


type ReservationHandler struct {
    service *application.ReservationService
}

func NewReservationHandler(svc *application.ReservationService) *ReservationHandler {
    return &ReservationHandler{service: svc}
}

func (h *ReservationHandler) List(w http.ResponseWriter, r *http.Request) {
    items, err := h.service.List()
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(items)
}

func (h *ReservationHandler) Create(w http.ResponseWriter, r *http.Request) {
    var in domain.Reservation
    if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }
    out, err := h.service.Create(&in)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(out)
}
