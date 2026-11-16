"""What makes a session live, as WHERE conditions: shared by the session check (GetSession) and Settings' list of a
person's sessions (ListSessions), so both agree on which sessions still work.

Part of the accounts module's read side; it changes nothing.
"""

from datetime import datetime
from typing import Any

from sqlmodel import col

from app.modules.accounts.persistence.tables import AppUser, UserSession


def live_session_conditions(now: datetime, issuer: str) -> tuple[Any, ...]:
    """Not signed out, inside both expiries, signed in with today's provider (a switch of provider ends every older
    session), and its user switched on. The statement must join AppUser on the session's user."""
    return (
        col(UserSession.revoked_at).is_(None),
        col(UserSession.expires_at) > now,
        col(UserSession.absolute_expires_at) > now,
        col(UserSession.issuer) == issuer,
        col(AppUser.is_active).is_(True),
    )
