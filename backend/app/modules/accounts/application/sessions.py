"""The session check every protected request goes through: which person a session cookie stands for, if any.

The accounts module's half of authentication (application). The composition root puts SessionGate.authenticate on
the app, and web/auth.py's require_user calls it with the cookie's key, so web/ needs no module. A live session that
was last renewed over RENEW_AFTER ago is renewed (sliding expiry) as it's used.
"""

from dataclasses import dataclass

from app.core.clock import Clock
from app.core.cqrs import MessageBus
from app.core.identity import IdentityProvider, Principal
from app.modules.accounts.commands.renew_session import RenewSession
from app.modules.accounts.domain.keys import hash_key
from app.modules.accounts.persistence.repository import utc
from app.modules.accounts.queries.get_session import GetSession
from app.modules.accounts.values import RENEW_AFTER


@dataclass(frozen=True)
class SessionGate:
    """Turns a session cookie's key into the person it belongs to. Needs the bus, the provider (whose sessions are
    accepted: its issuer) and the clock (when to renew)."""

    bus: MessageBus
    identity: IdentityProvider
    clock: Clock

    def authenticate(self, session_key: str) -> Principal | None:
        """The person and session `session_key` belongs to; None if it's no live session (GetSession's rules)."""
        session = self.bus.ask(GetSession(key_hash=hash_key(session_key), issuer=self.identity.issuer))
        if session is None:
            return None
        if self.clock.now() - utc(session.renewed_at) >= RENEW_AFTER:
            self.bus.execute(RenewSession(session_id=session.session_id))
        return Principal(user_id=session.user_id, session_id=session.session_id, session_handle=session.handle)
