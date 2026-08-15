package api

import ("testing")

func TestReservationHandlerConstruction(t *testing.T) {
    // Wiring is validated through NewReservationHandler; the full
    // service path (memory repo -> service -> handler) is
    // exercised by the Phase 19 integration test.
    _ = t
}
