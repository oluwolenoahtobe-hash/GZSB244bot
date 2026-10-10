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
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1", alias="OPENAI_BASE_URL"
    )
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    max_file_size_mb: int = Field(default=20, alias="MAX_FILE_SIZE_MB")
    max_document_chars: int = Field(default=120_000, alias="MAX_DOCUMENT_CHARS")

    llm_request_timeout: int = 120
    llm_max_retries: int = 3

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings instance."""
    return Settings()  # type: ignore[call-arg]
