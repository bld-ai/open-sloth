"""
Configuration management using Pydantic Settings.
"""

from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    poll_interval: float = Field(1.0, env="POLL_INTERVAL")

    llm_provider: str = Field("openai", env="LLM_PROVIDER")
    llm_api_key: str = Field("", env="LLM_API_KEY")
    llm_model: str = Field("gpt-4-turbo", env="LLM_MODEL")
    llm_base_url: Optional[str] = Field(None, env="LLM_BASE_URL")

    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    openai_model: Optional[str] = Field(None, env="OPENAI_MODEL")

    google_sheet_id: Optional[str] = Field(None, env="GOOGLE_SHEET_ID")
    google_credentials_file: str = Field(
        "/app/credentials.json", env="GOOGLE_CREDENTIALS_FILE"
    )

    allowed_users_raw: str = Field("", env="ALLOWED_USERS")

    log_level: str = Field("INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def allowed_users(self) -> List[str]:
        """Parse comma-separated allowed users list."""
        if not self.allowed_users_raw.strip():
            return []
        return [u.strip() for u in self.allowed_users_raw.split(",") if u.strip()]

    def get_llm_api_key(self) -> str:
        """Get API key, with fallback to legacy OPENAI_API_KEY."""
        return self.llm_api_key or self.openai_api_key or ""

    def get_llm_model(self) -> str:
        """Get model, with fallback to legacy OPENAI_MODEL."""
        return self.llm_model or self.openai_model or "gpt-4-turbo"


settings = Settings()
