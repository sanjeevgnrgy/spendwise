"""GetSignOut: what signing a session out needs to know. The query and its handler; it changes nothing.

A slice of the accounts module's read side. The sign-out use case (application/sign_out.py) asks it before ending
the session, for the sealed ID token it names to the provider; module.py registers the handler.
"""

from app.core.cqrs import Context, Query
from app.modules.accounts.models import SignOutView
from app.modules.accounts.persistence.tables import UserSession
from app.modules.accounts.values import SessionId


# Asked by SignOutFlow.sign_out with the request's session.
class GetSignOut(Query[SignOutView]):
    """The session's sealed ID token (None if it has none or is gone)."""

    session_id: SessionId


def get_sign_out(ctx: Context, query: GetSignOut) -> SignOutView:
    """The sealed ID token kept with the session."""
    session = ctx.session.get(UserSession, query.session_id)
    return SignOutView(sealed_id_token=session.sealed_id_token if session else None)
