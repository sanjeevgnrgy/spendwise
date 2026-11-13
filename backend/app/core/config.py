from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# This file is backend/app/core/config.py, so parents[2] is backend/ and its parent is the project folder.
# Absolute paths mean it works no matter which folder the app is started from.
BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent

# Every REST route lives under this prefix. A breaking change to the API gets /api/v2, so existing
# clients keep working while they move over.
API_PREFIX = "/api/v1"
# The version shown in the OpenAPI document. It describes the API contract, so it changes with it.
API_VERSION = "1.0.0"
# Where MCP clients reach the MCP server over HTTP, when it's enabled (see MCP_TOKEN).
MCP_PATH = "/mcp"


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
    # Where the assistant's expense tools run. Unset (the default): this app's own MCP server, called
    # in-process, with no network hop. Set it only when the MCP server runs as a separate service.
    mcp_url: str | None = None
    # A shared secret for MCP over HTTP. Unset: /mcp/ isn't served over HTTP at all (stdio still works).
    # Set: /mcp/ answers only requests with "Authorization: Bearer <token>", and the assistant sends it
    # to MCP_URL. Anyone who can reach an open MCP endpoint could change or delete expenses.
    mcp_token: SecretStr | None = None
    # Web pages allowed to call this API from a browser (CORS). Only the Vite dev server for now;
    # both spellings, because the browser treats localhost and 127.0.0.1 as different origins.
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    # A local SQLite file by default; point DATABASE_URL at Postgres later without code changes.
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'spendwise.db').as_posix()}"


# Read once at startup. Real environment variables override values from .env.
settings = Settings()
