from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str

    main_bot_token: str
    owner_telegram_id: int
    office_group_id: int = 0

    gemini_api_key: str = ""  # seeded into DB on first start; use DB table for runtime rotation

    muai_api_url: str = "http://bot:8000"
    muai_api_secret: str = ""

    log_level: str = "INFO"

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
