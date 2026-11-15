"""The sign-in page's buttons, as the OIDC adapter is configured with them: OIDC_LOGIN_OPTIONS (infrastructure).

Each option is one button ("Continue with Google") and what it adds to the authorization request so the provider
skips its own page and goes straight to that way of signing in. The way to ask that differs by provider, so it's
data, not code: one provider takes an extra scope naming the login option, another an extra parameter
(`kc_idp_hint=google`). docs/identity_provider.md has the values for each provider. Read by config.py (the
setting's type) and oidc.py (building the request).
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

# A button's key: what the web app sends back (?option=google). Short, lowercase, URL-safe.
OPTION_KEY_PATTERN = r"^[a-z0-9][a-z0-9-]{0,31}$"
MAX_LABEL_LENGTH = 40
# A scope is one token: no spaces (scopes are sent space-separated).
Scope = Annotated[str, StringConstraints(pattern=r"^\S{1,200}$")]

# The parameters the flow sets itself. An option may add others, but never replace these: one that changed
# redirect_uri, state or code_challenge would undo the checks they exist for.
RESERVED_PARAMETERS = frozenset(
    {
        "client_id",
        "code_challenge",
        "code_challenge_method",
        "nonce",
        "redirect_uri",
        "request",
        "request_uri",
        "response_mode",
        "response_type",
        "scope",
        "state",
    }
)


# One entry of OIDC_LOGIN_OPTIONS, e.g. {"key": "google", "label": "Google", "extra_scopes": ["urn:...:idp:id:123"]}.
# A wrong entry (a reserved parameter, a bad key) stops the app at startup, with the settings' validation error.
class OidcLoginOption(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str = Field(pattern=OPTION_KEY_PATTERN)
    # Shown on the button as it is: a provider's name, which isn't translated.
    label: str = Field(min_length=1, max_length=MAX_LABEL_LENGTH)
    extra_scopes: tuple[Scope, ...] = ()
    extra_params: dict[str, str] = Field(default_factory=dict)

    @field_validator("extra_params")
    @classmethod
    def _no_reserved_parameters(cls, params: dict[str, str]) -> dict[str, str]:
        """Refuse a parameter the flow sets itself (any letter case). Raises ValueError, naming them."""
        reserved = sorted(name for name in params if name.lower() in RESERVED_PARAMETERS)
        if reserved:
            raise ValueError(f"these parameters are set by the sign-in flow itself: {', '.join(reserved)}")
        return params
