"""UnconfiguredIdentityProvider: the IdentityProvider port when sign-in isn't set up (infrastructure, adapter).

The composition root uses it when an OIDC_* setting or SESSION_ENCRYPTION_KEYS is missing. Sign-in then fails
closed: nobody can sign in, so every protected route answers 401, instead of the API running without sign-in. The
reason (which settings are missing, by name only) goes to the server log when a sign-in is tried.
"""

from collections.abc import Sequence

from app.core.identity import IdentityError, InvalidTokenError, LoginOption, LogoutNotice, VerifiedLogin


class UnconfiguredIdentityProvider:
    """Refuses every sign-in, saying which settings are missing."""

    def __init__(self, missing: Sequence[str]) -> None:
        """A provider that can't be used because the settings named in `missing` aren't set."""
        self.issuer: str | None = None
        self._reason = f"Sign-in isn't configured: set {', '.join(missing)} in .env"

    def login_options(self) -> list[LoginOption]:
        """No buttons: there's nothing to sign in with."""
        return []

    def authorization_url(
        self, redirect_uri: str, state: str, nonce: str, code_verifier: str, option: str | None
    ) -> str:
        """Raises IdentityError: there's no provider to send anyone to."""
        raise IdentityError(self._reason)

    def complete_login(self, code: str, redirect_uri: str, code_verifier: str, nonce: str) -> VerifiedLogin:
        """Raises IdentityError: there's no provider to ask."""
        raise IdentityError(self._reason)

    def end_session_url(self, id_token: str | None, post_logout_redirect_uri: str) -> str | None:
        """None: there's no provider session to end."""
        return None

    def read_logout_token(self, logout_token: str) -> LogoutNotice:
        """Raises InvalidTokenError: with no provider, no logout token can be trusted."""
        raise InvalidTokenError(self._reason)
