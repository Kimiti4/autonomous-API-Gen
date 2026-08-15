package infrastructure

import (
    "sync"
    "github.com/tiannara/reservation_system/internal/domain"
)


type memoryReservationRepository struct {
    mu    sync.Mutex
    store map[string]*domain.Reservation
}

func NewReservationRepository() domain.ReservationRepository {
    return &memoryReservationRepository{store: map[string]*domain.Reservation{}}
}

func (r *memoryReservationRepository) Get(id string) (*domain.Reservation, error) {
    r.mu.Lock()
    defer r.mu.Unlock()
    entity, ok := r.store[id]
    if !ok {
        return nil, nil
    }
    return entity, nil
}

func (r *memoryReservationRepository) List() ([]*domain.Reservation, error) {
    r.mu.Lock()
    defer r.mu.Unlock()
    out := make([]*domain.Reservation, 0, len(r.store))
    for _, v := range r.store {
        out = append(out, v)
    }
    return out, nil
}

func (r *memoryReservationRepository) Create(entity *domain.Reservation) (*domain.Reservation, error) {
    r.mu.Lock()
    defer r.mu.Unlock()
    r.store[entity.ID] = entity
    return entity, nil
}

func (r *memoryReservationRepository) Delete(id string) error {
    r.mu.Lock()
    defer r.mu.Unlock()
    delete(r.store, id)
    return nil
}
