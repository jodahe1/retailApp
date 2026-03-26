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

    cors_allowed_origins: List[str] = Field(default_factory=lambda: ["*"])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
