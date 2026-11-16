"""Settings and fixed values the whole backend reads (infrastructure).

Values that differ between machines (the Gemini key and model, the database URL, the MCP token and URL, the uploads
folder, the sign-in provider and its keys) come from the environment or .env, into the one `settings` object, read
once at startup. Values that are part of the design (the API prefix and version, the MCP path) are constants instead:
they change in code, together with the contract, never per machine. Read by db.py (the default engine), the
composition root (which hands the Gemini key and model to the Gemini adapter, the MCP URL and token to the tools, the
uploads folder to the file store, and the OIDC_* settings, PUBLIC_URL and the session keys to sign-in), main.py (the
constants), the migrations and the export script. docs/configuration.md lists every setting.
"""

from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.infrastructure.identity.options import OidcLoginOption

# This file is backend/app/infrastructure/config.py, so parents[2] is backend/ and its parent is the project folder.
# Absolute paths mean it works no matter which folder the app is started from.
BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent

# Every REST route lives under this prefix. A breaking change to the API gets /api/v2, so existing
# clients keep working while they move over.
API_PREFIX = "/api/v1"
# The version shown in the OpenAPI document. It describes the API contract, so it changes with it.
API_VERSION = "1.0.0"
# Where MCP clients reach the MCP server over HTTP (each request with a personal access token, D191).
MCP_PATH = "/mcp"


# Every setting that can differ between machines. pydantic-settings fills each field from the environment
# variable of the same name, in any letter case (GEMINI_MODEL -> gemini_model), or else from .env. A value
# of the wrong type stops the app at startup with a validation error, instead of failing later on first use.
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
    # How many requests each person may make per minute, and per day, to the routes that call the language model
    # (POST /agent, /chat, /parse and receipt reading): each one spends Gemini quota (D194). Counted in memory, per
    # server process.
    model_requests_per_minute: int = Field(default=10, ge=1)
    model_requests_per_day: int = Field(default=300, ge=1)
    # A local SQLite file by default; point DATABASE_URL at Postgres later without code changes.
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'spendwise.db').as_posix()}"
    # The folder uploaded files (receipts) are kept in, by random names. Git-ignored: it's your data, like the
    # database.
    uploads_dir: Path = BACKEND_DIR / "uploads"

    # Sign-in (Phase 22): the OpenID Connect provider people sign in with (D185). Any provider that implements the
    # standard works; these are its issuer URL and this app's registration there (a confidential "web" client).
    # Until the issuer, client id and secret and SESSION_ENCRYPTION_KEYS are all set, nobody can sign in, and
    # every route but /health and the sign-in routes answers 401.
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: SecretStr | None = None
    # The scopes every sign-in asks for, space-separated. Add a provider's own when it needs one for roles.
    oidc_scopes: str = "openid profile email"
    # The sign-in page's buttons, a JSON list (identity/options.py). Empty: one button, the provider's own page.
    oidc_login_options: list[OidcLoginOption] = []
    # Where the tokens list the person's roles, and the role they must have to sign in. Both unset: anyone the
    # provider lets sign in may (then limit who that is at the provider: docs/identity_provider.md).
    oidc_role_claim: str | None = None
    oidc_required_role: str | None = None
    # The address people open the web app at (scheme, host and port: no path). The provider sends them back to
    # <PUBLIC_URL>/api/v1/auth/callback, which must be registered there exactly; the browser reaches the API here too
    # (one origin, D184).
    public_url: str = "http://localhost:5173"
    # Keys that seal the ID token each session keeps (Fernet, a JSON list, newest first). Make one with:
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    session_encryption_keys: list[SecretStr] = []
    # The session cookie's Secure flag (and its __Host- prefix). Leave it on: browsers accept Secure cookies on
    # http://localhost; turn it off only for a browser that doesn't.
    cookie_secure: bool = True

    # A pydantic validator: it runs as the settings are read.
    @field_validator("public_url")
    @classmethod
    def _origin_only(cls, value: str) -> str:
        """PUBLIC_URL as an origin: http(s), a host, no path. Raises ValueError otherwise."""
        parts = urlsplit(value.rstrip("/"))
        if parts.scheme not in ("http", "https") or not parts.netloc or parts.path or parts.query or parts.fragment:
            raise ValueError("PUBLIC_URL must be an origin such as https://spendwise.example (no path)")
        return f"{parts.scheme}://{parts.netloc}"

    def missing_for_sign_in(self) -> list[str]:
        """The names of the settings sign-in still needs; empty when it can work."""
        needed = {
            "OIDC_ISSUER": self.oidc_issuer,
            "OIDC_CLIENT_ID": self.oidc_client_id,
            "OIDC_CLIENT_SECRET": self.oidc_client_secret,
            "SESSION_ENCRYPTION_KEYS": self.session_encryption_keys or None,
        }
        return [name for name, value in needed.items() if value is None]


# Read once at startup. Real environment variables override values from .env.
settings = Settings()
