from __future__ import annotations

import os

from pydantic import BaseModel

AUTH_REQUIRED: bool = True


class Settings(BaseModel):
    app_name: str = "Subscription System"
    api_key: str = ""
    log_level: str = "INFO"


def load_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "Subscription System"),
        api_key=os.getenv("API_KEY", ""),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
