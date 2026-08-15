from __future__ import annotations

import os

from pydantic import BaseModel

AUTH_REQUIRED: bool = False


class Settings(BaseModel):
    app_name: str = "Inventory System"
    api_key: str = ""
    log_level: str = "INFO"


def load_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "Inventory System"),
        api_key=os.getenv("API_KEY", ""),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
