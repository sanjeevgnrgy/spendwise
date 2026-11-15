"""Signing people in through an outside identity provider, independent of which one: the IdentityProvider port.

The provider (which one is configuration: docs/identity_provider.md) shows its own login page, perhaps with
Google or GitHub behind it, and proves who signed in.
SpendWise depends only on this port, never on a provider (D185): the composition root picks the adapter, today
infrastructure/identity's standard OpenID Connect one, configured from settings, so another provider is a change of
settings or, at most, one more adapter. The accounts module's sign-in use cases call it; a check passes a fake.

Core layer: plain types and a Protocol, no framework and no I/O.
"""

from dataclasses import dataclass, field
from typing import Protocol

from app.core.errors import AppError, ExternalServiceError


@dataclass(frozen=True)
class LoginOption:
    """A way to sign in that the sign-in page offers as its own button, e.g. "google" / "Google"."""

    key: str
    label: str


@dataclass(frozen=True)
class VerifiedLogin:
    """Who signed in, as the provider proved it: every check on its answer has passed.

    `issuer` and `subject` identify the person at that provider for good; the rest is their profile as it is now.
    `session_id` is the provider's own session (OIDC `sid`), to match a back-channel logout. `id_token` is the signed
    token itself, kept (sealed) with the session so signing out can name it to the provider.
    """

    issuer: str
    subject: str
    id_token: str
    session_id: str | None = None
    email: str | None = None
    email_verified: bool = False
    name: str | None = None
    picture: str | None = None
    roles: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class LogoutNotice:
    """The provider says a session ended there (back-channel logout): end ours for that `session_id` or `subject`."""

    issuer: str
    subject: str | None
    session_id: str | None


@dataclass(frozen=True)
class Principal:
    """The person a request comes from: their user id, and the session it runs in (its id and public handle)."""

    user_id: int
    session_id: int
    session_handle: str


class IdentityError(ExternalServiceError):
    """The identity provider couldn't be used: it isn't configured, can't be reached, or answered with an error."""


class InvalidTokenError(AppError):
    """A token from the provider failed a check (signature, issuer, audience, time, nonce...): it isn't trusted."""

    status = 400
    slug = "invalid-token"
    title = "Invalid token"


class IdentityProvider(Protocol):
    """An outside service that signs people in (OpenID Connect's authorization code flow, with PKCE)."""

    # The provider's issuer identifier (a URL), or None when sign-in isn't configured. Sessions remember it, so a
    # session from another provider (after a switch) is never accepted.
    issuer: str | None

    def login_options(self) -> list[LoginOption]:
        """The sign-in page's own buttons, in order; empty when it offers only the provider's page."""
        ...

    def authorization_url(
        self, redirect_uri: str, state: str, nonce: str, code_verifier: str, option: str | None
    ) -> str:
        """Where to send the browser to sign in. `option` (a LoginOption key) skips straight to that way of signing
        in. Raises IdentityError if the provider can't be used."""
        ...

    def complete_login(self, code: str, redirect_uri: str, code_verifier: str, nonce: str) -> VerifiedLogin:
        """Exchange the code the provider returned for who signed in, checking every token on the way.

        Raises InvalidTokenError if an answer fails a check, IdentityError if the provider can't be used.
        """
        ...

    def end_session_url(self, id_token: str | None, post_logout_redirect_uri: str) -> str | None:
        """Where to send the browser to sign out at the provider too; None if it offers no such page."""
        ...

    def read_logout_token(self, logout_token: str) -> LogoutNotice:
        """Check a back-channel logout token and say which session ended. Raises InvalidTokenError if it fails a
        check, IdentityError if the provider can't be used."""
        ...
