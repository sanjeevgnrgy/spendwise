"""Signing in: sending the browser to the provider, and turning its answer into a session (accounts, application).

The use case behind GET /auth/login and GET /auth/callback, built by module.py and called by api.py, which only
deals with HTTP (cookies, redirects). The provider is the IdentityProvider port; the ID token is sealed with the
Sealer port. Calls to the provider happen outside any database transaction (D164): the attempt is stored, then the
browser leaves; on its return the attempt is taken, the provider asked, and only then the session written.
"""

import hmac
import logging
from dataclasses import dataclass

from app.core.cqrs import MessageBus
from app.core.identity import IdentityError, IdentityProvider, InvalidTokenError, VerifiedLogin
from app.core.sealing import Sealer
from app.modules.accounts.application.config import SignInConfig
from app.modules.accounts.commands.end_session import EndSession
from app.modules.accounts.commands.sign_in import SignIn
from app.modules.accounts.commands.start_login import StartLogin
from app.modules.accounts.commands.take_login_attempt import TakeLoginAttempt
from app.modules.accounts.domain.keys import hash_key, new_handle, new_key, new_verifier
from app.modules.accounts.domain.return_paths import safe_return_path
from app.modules.accounts.domain.rules import AccountDisabledError, may_sign_in, profile_of
from app.modules.accounts.models import LoginAttemptView, LoginOptionRead
from app.modules.accounts.values import SignInFailure

logger = logging.getLogger(__name__)

# OAuth 2.0's error code when the person cancelled or the provider refused them (RFC 6749, 4.1.2.1).
ACCESS_DENIED = "access_denied"


class SignInFailedError(Exception):
    """A sign-in that didn't complete, and why (the code the sign-in page is sent, never the details)."""

    def __init__(self, reason: SignInFailure) -> None:
        """A failure for `reason`."""
        super().__init__(reason.value)
        self.reason = reason


@dataclass(frozen=True)
class Started:
    """A sign-in on its way: where to send the browser, and the login cookie's key that ties it to this browser."""

    authorization_url: str
    login_key: str


@dataclass(frozen=True)
class Finished:
    """A completed sign-in: the new session cookie's key, and the web app's page to go back to."""

    session_key: str
    return_to: str


@dataclass(frozen=True)
class SignInFlow:
    """Signs people in through the provider. Needs the bus, the provider, the sealer and the addresses."""

    bus: MessageBus
    identity: IdentityProvider
    sealer: Sealer
    config: SignInConfig

    def options(self) -> list[LoginOptionRead]:
        """The sign-in page's buttons, as the provider is configured; empty for just the provider's own page."""
        return [LoginOptionRead(key=option.key, label=option.label) for option in self.identity.login_options()]

    def begin(self, option: str | None, return_to: str | None, current_key: str | None) -> Started:
        """Store a new attempt and say where the browser goes. A session this browser already has is ended: a sign-in
        always starts a new one. Raises IdentityError if the provider can't be used (nothing is stored then)."""
        if current_key:
            self.bus.execute(EndSession(key_hash=hash_key(current_key)))
        known = {choice.key for choice in self.identity.login_options()}
        login_key, state, nonce, verifier = new_key(), new_key(), new_key(), new_verifier()
        url = self.identity.authorization_url(
            self.config.redirect_uri, state, nonce, verifier, option if option in known else None
        )
        self.bus.execute(
            StartLogin(
                key_hash=hash_key(login_key),
                state=state,
                nonce=nonce,
                code_verifier=verifier,
                return_to=safe_return_path(return_to),
            )
        )
        return Started(authorization_url=url, login_key=login_key)

    def finish(self, login_key: str | None, state: str | None, code: str | None, error: str | None) -> Finished:
        """Check the provider's answer against the attempt this browser started, and start a session.

        Raises SignInFailedError with the reason the sign-in page shows: the attempt is gone (EXPIRED), the state
        doesn't match or a check failed (REJECTED), the person cancelled (CANCELLED), may not sign in (NOT_ALLOWED),
        or the provider failed (UNAVAILABLE).
        """
        attempt = self.bus.execute(TakeLoginAttempt(key_hash=hash_key(login_key))) if login_key else None
        if attempt is None:
            raise SignInFailedError(SignInFailure.EXPIRED)
        # The state ties the answer to the request this browser made: a mismatch is someone else's answer.
        if not state or not hmac.compare_digest(state.encode(), attempt.state.encode()):
            raise SignInFailedError(SignInFailure.REJECTED)
        if error:
            # %r: the value comes from the URL, so a line break in it can't fake another log line.
            logger.info("sign-in ended at the provider: %r", error)
            raise SignInFailedError(SignInFailure.CANCELLED if error == ACCESS_DENIED else SignInFailure.UNAVAILABLE)
        if not code:
            raise SignInFailedError(SignInFailure.REJECTED)
        login = self._verified(code, attempt)
        if not may_sign_in(login.roles, self.config.required_role):
            logger.info("sign-in refused: the required role is missing")
            raise SignInFailedError(SignInFailure.NOT_ALLOWED)
        return Finished(session_key=self._start_session(login), return_to=attempt.return_to)

    def _verified(self, code: str, attempt: LoginAttemptView) -> VerifiedLogin:
        """Ask the provider who signed in. Raises SignInFailedError (REJECTED or UNAVAILABLE); details are logged."""
        try:
            return self.identity.complete_login(code, self.config.redirect_uri, attempt.code_verifier, attempt.nonce)
        except InvalidTokenError as failure:
            logger.warning("sign-in rejected: %s", failure)
            raise SignInFailedError(SignInFailure.REJECTED) from None
        except IdentityError as failure:
            logger.warning("sign-in failed at the provider: %s", failure)
            raise SignInFailedError(SignInFailure.UNAVAILABLE) from None

    def _start_session(self, login: VerifiedLogin) -> str:
        """Record the user and a new session; return the session cookie's key. Raises SignInFailedError
        (NOT_ALLOWED) if the account is switched off."""
        profile = profile_of(login)
        session_key = new_key()
        try:
            session_id = self.bus.execute(
                SignIn(
                    issuer=login.issuer,
                    subject=login.subject,
                    name=profile.name,
                    email=profile.email,
                    email_verified=profile.email_verified,
                    avatar_url=profile.avatar_url,
                    key_hash=hash_key(session_key),
                    handle=new_handle(),
                    provider_session_id=login.session_id,
                    sealed_id_token=self.sealer.seal(login.id_token),
                )
            )
        except AccountDisabledError as failure:
            logger.info("sign-in refused: %s", failure)
            raise SignInFailedError(SignInFailure.NOT_ALLOWED) from None
        logger.info("signed in: session %d", session_id)
        return session_key
