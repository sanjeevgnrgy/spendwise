from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# This file is backend/app/core/config.py, so parents[2] is backend/ and its parent is the project folder.
# Absolute paths mean it works no matter which folder the app is started from.
BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_DIR / ".env",
        # Treat "KEY=" (empty) as not set, so the "is it missing?" checks are simple.
        env_ignore_empty=True,
        # .env may hold settings for other parts of the project; don't fail on them.
        extra="ignore",
    )

    # SecretStr keeps the key out of logs and error messages if settings get printed.
    gemini_api_key: SecretStr | None = None
    gemini_model: str | None = None
    # A local SQLite file by default; point DATABASE_URL at Postgres later without code changes.
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'spendwise.db').as_posix()}"


# Read once at startup. Real environment variables override values from .env.
settings = Settings()
