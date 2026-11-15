"""The addresses and the access rule the sign-in use cases need (accounts module, application).

Built once by the composition root (bootstrap.py) from PUBLIC_URL, the API prefix and OIDC_REQUIRED_ROLE, and passed
to the use cases, so they read no settings themselves.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SignInConfig:
    """Where the provider sends people back, where signing out ends, and the role sign-in requires (if any)."""

    # <PUBLIC_URL>/api/v1/auth/callback: registered at the provider exactly as this.
    redirect_uri: str
    # <PUBLIC_URL>/sign-in: where the provider sends people after signing them out (registered there too).
    signed_out_url: str
    # The role a person must have (OIDC_REQUIRED_ROLE); None lets in everyone the provider lets sign in.
    required_role: str | None = None
