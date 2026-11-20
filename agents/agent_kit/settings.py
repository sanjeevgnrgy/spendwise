"""What every agent's settings share: the .env they're read from, the host, and the rule for keys (agent kit).

Each agent has its own pydantic-settings class (receipt/settings.py, currency/settings.py) with its own key and port,
built on AGENT_SETTINGS_CONFIG and checking its key with long_enough. They're separate from the backend's settings
because each agent is its own service; they share only the names of the Gemini settings and of their own keys, so one
.env serves everything. docs/configuration.md lists every setting.
"""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict

# This file is agents/agent_kit/settings.py, so parents[2] is the project folder, where .env lives.
PROJECT_DIR = Path(__file__).resolve().parents[2]
# Every agent listens on this machine only (D197): nothing outside it can reach one, whatever the key.
HOST = "127.0.0.1"
# A shorter key is refused at startup: 32 characters of secrets.token_urlsafe are 192 random bits.
MIN_KEY_LENGTH = 32
SHORT_KEY = "{name} must be at least {min_length} characters"

# How every agent reads its settings: from the environment, else the project's .env; "KEY=" counts as unset.
AGENT_SETTINGS_CONFIG = SettingsConfigDict(
    env_file=PROJECT_DIR / ".env",
    env_ignore_empty=True,
    # .env holds the backend's and the other agents' settings too; don't fail on them.
    extra="ignore",
    # A rejected value is never repeated in the error: it may be a key.
    hide_input_in_errors=True,
)


def long_enough(key: SecretStr, name: str) -> SecretStr:
    """`key` if it's at least MIN_KEY_LENGTH characters. Raises ValueError naming the setting (never the key)."""
    if len(key.get_secret_value()) < MIN_KEY_LENGTH:
        raise ValueError(SHORT_KEY.format(name=name, min_length=MIN_KEY_LENGTH))
    return key


def agent_url(port: int) -> str:
    """Where an agent on `port` is reached: its Agent Card names this address."""
    return f"http://{HOST}:{port}"
