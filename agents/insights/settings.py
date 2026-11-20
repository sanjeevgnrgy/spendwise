"""The insights agent's settings, from the environment or the project's .env (infrastructure of the agent).

Read once by __main__.py. Built on the agent kit's shared configuration (agent_kit/settings.py: the .env, the host,
the key rule); only the insights agent's own key and port, and the Gemini settings it shares with the backend, are
here. docs/configuration.md lists every setting.
"""

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings

from agent_kit.settings import AGENT_SETTINGS_CONFIG, agent_url, long_enough

DEFAULT_PORT = 9002
KEY_SETTING = "INSIGHTS_AGENT_KEY"


# Each field is filled from the environment variable of the same name (any letter case), or else from .env.
class AgentSettings(BaseSettings):
    model_config = AGENT_SETTINGS_CONFIG

    # The same key and model as the backend (one Gemini account); checked on the first model call, as there.
    gemini_api_key: SecretStr | None = None
    gemini_model: str | None = None
    # The key a client must send as "Authorization: Bearer <key>" (D197). Required: without it the agent won't
    # start. Make one with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    insights_agent_key: SecretStr
    insights_agent_port: int = Field(default=DEFAULT_PORT, ge=1024, le=65535)

    # A pydantic validator: it runs as the settings are read.
    @field_validator("insights_agent_key")
    @classmethod
    def _long_enough(cls, value: SecretStr) -> SecretStr:
        """The key, if it's long enough. Raises ValueError (naming the setting, never the key) otherwise."""
        return long_enough(value, KEY_SETTING)

    @property
    def url(self) -> str:
        """Where clients reach the agent: its Agent Card names this address."""
        return agent_url(self.insights_agent_port)
