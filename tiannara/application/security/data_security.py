"""34.22 Data Security -- injection, exposure, isolation."""
from __future__ import annotations
import re
def is_sql_injection(payload: str) -> bool:
    return bool(re.search(r"('|\"|;|--|\bunion\b.*\bselect\b)", payload, re.I))
def is_exposure(data: dict, allowed_tenant: str) -> bool:
    return data.get("tenant") != allowed_tenant
