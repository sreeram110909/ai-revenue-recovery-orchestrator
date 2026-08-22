"""Application Configuration via Pydantic Settings.

Loads environment variables from .env file with sensible defaults.
Secrets (API keys, DB credentials) remain server-side only.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Central configuration for the AI Revenue Recovery Orchestrator.

    All values are loaded from environment variables or .env file.
    Secrets must never be committed to the repository.
    """

    # Server
    port: int = Field(default=8000, description="HTTP server port")
    host: str = Field(default="0.0.0.0", description="HTTP server bind address")
    environment: str = Field(default="development", description="Runtime environment")
    log_level: str = Field(default="INFO", description="Logging level")

    # Gemini AI (Bounded Diagnosis Only)
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key (server-side secret)")
    gemini_model: str = Field(default="gemini-2.5-flash", description="Gemini model for bounded diagnosis")

    # Razorpay Test Mode
    razorpay_key_id: Optional[str] = Field(default=None, description="Razorpay test key ID")
    razorpay_key_secret: Optional[str] = Field(default=None, description="Razorpay test key secret")
    razorpay_webhook_secret: Optional[str] = Field(default=None, description="Razorpay webhook verification secret")

    # Database
    # PostgreSQL is the intended production database.
    # When DATABASE_URL is empty, SQLite is used as a local-development/testing fallback.
    database_url: Optional[str] = Field(default=None, description="PostgreSQL connection string")

    # Demonstration Policy Defaults
    default_max_retries: int = Field(default=3, description="Demo: max automated retries per case")
    default_retry_cooldown_hours: int = Field(default=4, description="Demo: minimum hours between retries")
    default_automated_amount_limit: int = Field(default=15000, description="Demo: max amount for auto action (INR)")

    @property
    def effective_database_url(self) -> str:
        """Return PostgreSQL DATABASE_URL if set, otherwise SQLite fallback for local dev."""
        if self.database_url:
            return self.database_url
        return "sqlite:///./revenue_recovery.db"

    @property
    def is_sqlite_fallback(self) -> bool:
        """True when using SQLite fallback instead of PostgreSQL."""
        return not self.database_url

    @property
    def has_razorpay_credentials(self) -> bool:
        """True when valid Razorpay test-mode credentials are configured."""
        return bool(self.razorpay_key_id and self.razorpay_key_secret)

    @property
    def has_gemini_credentials(self) -> bool:
        """True when a Gemini API key is configured."""
        return bool(self.gemini_api_key)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


def get_settings() -> Settings:
    """Factory function for application settings (cacheable at startup)."""
    return Settings()
