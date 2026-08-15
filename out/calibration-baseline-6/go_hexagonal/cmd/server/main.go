package main

import (
    "log"
    "net/http"
    "github.com/tiannara/reservation_system/internal/api"
    "github.com/tiannara/reservation_system/internal/application"
    "github.com/tiannara/reservation_system/internal/infrastructure"
)


func main() {
    svc := application.NewReservationService(infrastructure.NewReservationRepository())
    handler := api.NewReservationHandler(svc)
    mux := http.NewServeMux()
    mux.HandleFunc("/reservations", handler.Create)
    mux.HandleFunc("/reservations/list", handler.List)
    mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(http.StatusOK)
        w.Write([]byte(`{"status":"ok"}`))
    })
    mux.HandleFunc("/readiness", func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(http.StatusOK)
        w.Write([]byte(`{"status":"ready"}`))
    })
    log.Println("listening on :8080")
    log.Fatal(http.ListenAndServe(":8080", mux))
}
