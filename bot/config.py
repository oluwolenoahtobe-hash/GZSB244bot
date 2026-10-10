"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed runtime settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    max_file_size_mb: int = Field(default=20, alias="MAX_FILE_SIZE_MB")

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings instance."""
    return Settings()  # type: ignore[call-arg]
