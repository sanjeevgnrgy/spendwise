"""Signing out: ending a session here, and at the provider too (accounts module, application).

The use case behind GET /auth/logout (a person signs out) and POST /auth/backchannel-logout (the provider says a
session ended there). Built by module.py, called by api.py.
"""

import logging
from dataclasses import dataclass

from app.core.cqrs import MessageBus
from app.core.identity import IdentityProvider, Principal
from app.core.sealing import Sealer
from app.modules.accounts.application.config import SignInConfig
from app.modules.accounts.commands.end_session import EndSession
from app.modules.accounts.commands.revoke_sessions import RevokeSessions
from app.modules.accounts.queries.get_sign_out import GetSignOut
from app.modules.accounts.values import SIGN_IN_PAGE

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SignOutFlow:
    """Ends sessions. Needs the bus, the provider (its sign-out page, its logout tokens), the sealer and addresses."""

    bus: MessageBus
    identity: IdentityProvider
    sealer: Sealer
    config: SignInConfig

    def sign_out(self, principal: Principal) -> str:
        """End the request's session, and return where the browser goes: the provider's sign-out page (with the
        session's ID token as a hint, so it knows whose session to end), or the sign-in page if it has none.

        Signing out at the provider too means "Sign in" asks again, which matters on a shared computer.
        """
        sealed = self.bus.ask(GetSignOut(session_id=principal.session_id)).sealed_id_token
        self.bus.execute(EndSession(session_id=principal.session_id))
        logger.info("signed out: session %d", principal.session_id)
        id_token = self.sealer.unseal(sealed) if sealed else None
        return self.identity.end_session_url(id_token, self.config.signed_out_url) or SIGN_IN_PAGE

    def back_channel(self, logout_token: str) -> None:
        """End the sessions the provider's logout token names. Raises InvalidTokenError (the token fails a check) or
        IdentityError (the provider's keys can't be read)."""
        notice = self.identity.read_logout_token(logout_token)
        self.bus.execute(
            RevokeSessions(issuer=notice.issuer, subject=notice.subject, provider_session_id=notice.session_id)
        )
        logger.info("back-channel logout: sessions ended for a provider %s", "session" if notice.session_id else "user")
