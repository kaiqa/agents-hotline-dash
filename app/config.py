"""Application configuration using Pydantic Settings."""
from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_env: str = Field(default="production", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=5687, alias="APP_PORT")
    debug: bool = Field(default=False, alias="DEBUG")
    login_username: str = Field(default="", alias="LOGIN_USERNAME")
    login_password: str = Field(default="", alias="LOGIN_PASSWORD")
    session_secret: str = Field(default="", alias="SESSION_SECRET")
    session_cookie_secure: bool = Field(default=False, alias="SESSION_COOKIE_SECURE")
    agents_api_username: str = Field(default="", alias="AGENTS_API_USERNAME")
    agents_api_password: str = Field(default="", alias="AGENTS_API_PASSWORD")

    # Database
    db_host: str = Field(default="mysql", alias="DB_HOST")
    db_port: int = Field(default=3306, alias="DB_PORT")
    db_user: str = Field(default="agents_hotline_user", alias="DB_USER")
    db_password: str = Field(default="agents_hotline_password", alias="DB_PASSWORD")
    db_name: str = Field(default="agents_hotline_db", alias="DB_NAME")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    # Webhook Configuration (defaults, can be overridden via Settings API)
    webhook_host: str = Field(default="0.0.0.0", alias="WEBHOOK_HOST")
    webhook_port: int = Field(default=5687, alias="WEBHOOK_PORT")
    webhook_path: str = Field(default="/webhook/agents", alias="WEBHOOK_PATH")
    training_webhook_path: str = Field(default="/webhook/training", alias="TRAINING_WEBHOOK_PATH")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:5687"],
        alias="CORS_ORIGINS"
    )

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def sync_database_url(self) -> str:
        """Get synchronous database URL for SQLAlchemy."""
        if self.database_url:
            return self.database_url.replace("mysql+pymysql", "mysql+pymysql")
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def async_database_url(self) -> str:
        """Get asynchronous database URL for SQLAlchemy async."""
        if self.database_url:
            return self.database_url.replace("mysql+pymysql", "mysql+aiomysql")
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def webhook_url(self) -> str:
        """Get full webhook URL for agents."""
        # For display purposes, use configured host/port
        host = self.webhook_host
        if host == "0.0.0.0":
            host = "localhost"
        return f"http://{host}:{self.webhook_port}{self.webhook_path}"

    @property
    def training_webhook_url(self) -> str:
        """Get full training webhook URL."""
        # For display purposes, use configured host/port
        host = self.webhook_host
        if host == "0.0.0.0":
            host = "localhost"
        return f"http://{host}:{self.webhook_port}{self.training_webhook_path}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()