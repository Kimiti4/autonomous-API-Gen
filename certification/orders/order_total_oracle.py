"""Independent order-total oracle (ISR rule: line_price minus discount)."""
from __future__ import annotations

from decimal import Decimal


def order_total_from_line_and_discount(line_price: Decimal, discount: Decimal) -> Decimal:
    return (line_price - discount).quantize(Decimal("0.01"))
