package domain


type ReservationRepository interface {
    Get(id string) (*Reservation, error)
    List() ([]*Reservation, error)
    Create(entity *Reservation) (*Reservation, error)
    Delete(id string) error
}
