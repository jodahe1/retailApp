from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Offline Retail Middle Platform API")
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    api_v1_prefix: str = Field(default="/api/v1")

    database_url: str = Field(
        default="postgresql+psycopg://retail_user:retail_pass@localhost:5432/retail_db"
    )
    db_echo: bool = Field(default=False)
    db_pool_pre_ping: bool = Field(default=True)
    db_pool_size: int = Field(default=10)
    db_max_overflow: int = Field(default=20)

    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    access_token_minutes: int = Field(default=30)
    refresh_token_minutes: int = Field(default=60 * 24 * 7)
    field_encryption_key: str = Field(
        default="3_tFs6M9_MUJCfM6AsQ3-WV7t9dVrn956xWxBY2NU4Q="
    )

    cors_allowed_origins: List[str] = Field(default_factory=lambda: ["*"])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
