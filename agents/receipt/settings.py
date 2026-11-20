"""The receipt agent's settings, from the environment or the project's .env (infrastructure of the agent).

Read once by the composition root (server.create_app) and __main__.py. The agent has its own settings, separate
from the monolith's (backend/app/infrastructure/config.py), because it's its own service: it shares only the names
of the Gemini settings, so one .env serves both. docs/configuration.md lists every setting.
"""

from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# This file is agents/receipt/settings.py, so parents[2] is the project folder, where .env lives.
PROJECT_DIR = Path(__file__).resolve().parents[2]
# The agent listens on this machine only (D197): nothing outside it can reach the agent, whatever the key.
HOST = "127.0.0.1"
DEFAULT_PORT = 9001
# A shorter key is refused at startup: 32 characters of secrets.token_urlsafe are 192 random bits.
MIN_KEY_LENGTH = 32


# Each field is filled from the environment variable of the same name (any letter case), or else from .env.
class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_DIR / ".env",
        env_ignore_empty=True,
        # .env holds the monolith's settings too; don't fail on them.
        extra="ignore",
        # A rejected value is never repeated in the error: it may be the key.
        hide_input_in_errors=True,
    )

    # The same key and model as the monolith (one Gemini account); checked on the first model call, as there.
    gemini_api_key: SecretStr | None = None
    gemini_model: str | None = None
    # The key a client must send as "Authorization: Bearer <key>" (D197). Required: without it the agent won't
    # start, so it never runs open. Make one with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    receipt_agent_key: SecretStr
    receipt_agent_port: int = Field(default=DEFAULT_PORT, ge=1024, le=65535)

    # A pydantic validator: it runs as the settings are read.
    @field_validator("receipt_agent_key")
    @classmethod
    def _long_enough(cls, value: SecretStr) -> SecretStr:
        """The key, if it's at least MIN_KEY_LENGTH characters. Raises ValueError (without the key) otherwise."""
        if len(value.get_secret_value()) < MIN_KEY_LENGTH:
            raise ValueError(f"RECEIPT_AGENT_KEY must be at least {MIN_KEY_LENGTH} characters")
        return value

    @property
    def url(self) -> str:
        """Where clients reach the agent: its Agent Card names this address."""
        return f"http://{HOST}:{self.receipt_agent_port}"
