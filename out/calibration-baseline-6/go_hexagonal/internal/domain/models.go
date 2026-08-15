package domain

type Reservation struct {
    Name string `json:"name"`
    ID string `json:"id"`
    Quantity *int `json:"quantity,omitempty"`
}
