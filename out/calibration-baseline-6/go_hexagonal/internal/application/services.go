package application

import "github.com/tiannara/reservation_system/internal/domain"


type ReservationService struct {
    repo domain.ReservationRepository
}

func NewReservationService(repo domain.ReservationRepository) *ReservationService {
    return &ReservationService{repo: repo}
}

func (svc *ReservationService) Create(entity *domain.Reservation) (*domain.Reservation, error) {
    return svc.repo.Create(entity)
}
func (svc *ReservationService) Get(id string) (*domain.Reservation, error) {
    return svc.repo.Get(id)
}
func (svc *ReservationService) List() ([]*domain.Reservation, error) {
    return svc.repo.List()
}
func (svc *ReservationService) Delete(id string) error {
    return svc.repo.Delete(id)
}
