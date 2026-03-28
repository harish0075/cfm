"""
Application configuration loaded from environment variables.
Uses pydantic-settings to validate and type-check all config values.

Loads `.env` from the backend directory first, then the repo root (`../.env`),
so a single root-level `.env` works when uvicorn is run from `backend/`.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    """Application settings sourced from .env file or environment variables."""

    model_config = SettingsConfigDict(
        env_file=(
            _BACKEND_DIR / ".env",
            _REPO_ROOT / ".env",
        ),
        env_file_encoding="utf-8",
        extra="allow",
    )

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cfm_v1"

    # JWT configuration
    SECRET_KEY: str = "cfm-v1-super-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"

    # Microsoft 365 / Outlook — register app at Azure Portal; redirect = backend callback URL
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_REDIRECT_URI: str = "http://127.0.0.1:8000/mail/microsoft/callback"
    FRONTEND_BASE_URL: str = "http://localhost:5173"
    FRONTEND_OAUTH_ORIGINS: str = ""


# Singleton settings instance used across the application
settings = Settings()


def allowed_mail_oauth_origins() -> frozenset[str]:
    """Origins allowed for Microsoft OAuth return (must match the URL you use in the browser)."""
    extra = settings.FRONTEND_OAUTH_ORIGINS.strip()
    if extra:
        return frozenset(x.strip().rstrip("/") for x in extra.split(",") if x.strip())
    from urllib.parse import urlparse

    base = settings.FRONTEND_BASE_URL.rstrip("/")
    u = urlparse(base)
    host = (u.hostname or "").lower()
    scheme = u.scheme or "http"
    port = f":{u.port}" if u.port else ""
    hosts = {base}
    if host == "localhost":
        hosts.add(f"{scheme}://127.0.0.1{port}")
    elif host == "127.0.0.1":
        hosts.add(f"{scheme}://localhost{port}")
    return frozenset(hosts)
