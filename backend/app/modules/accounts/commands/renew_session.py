"""RenewSession: push a used session's idle expiry forward, never past its absolute one. Command and handler.

A slice of the accounts module's write side. The session check (application/sessions.py) sends it when a session in
use was last renewed more than RENEW_AFTER ago, so a busy session isn't written on every request.
"""

from app.core.cqrs import Command, Context
from app.modules.accounts.persistence.repository import utc
from app.modules.accounts.persistence.tables import UserSession
from app.modules.accounts.values import SESSION_IDLE, SessionId


# Sent by SessionGate.authenticate for a live session.
class RenewSession(Command[None]):
    """Extends the session's idle expiry to SESSION_IDLE from now, capped by its absolute expiry."""

    session_id: SessionId


def renew_session(ctx: Context, command: RenewSession) -> None:
    """Stamp the session as renewed now; nothing happens if it has gone in the meantime."""
    session = ctx.session.get(UserSession, command.session_id)
    if session is None:
        return
    now = ctx.clock.now()
    session.renewed_at = now
    session.expires_at = min(now + SESSION_IDLE, utc(session.absolute_expires_at))
    ctx.session.add(session)
