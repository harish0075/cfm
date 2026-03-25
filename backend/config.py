"""
Application configuration loaded from environment variables.
Uses pydantic-settings to validate and type-check all config values.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings sourced from .env file or environment variables."""

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cfm_v1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


# Singleton settings instance used across the application
settings = Settings()
