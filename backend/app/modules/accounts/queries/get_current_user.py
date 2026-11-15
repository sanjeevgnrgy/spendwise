"""GetCurrentUser: the signed-in person's profile. The query and its handler; it changes nothing.

A slice of the accounts module's read side. GET /auth/user asks it for the person the request's session belongs to;
module.py registers the handler.
"""

from app.core.cqrs import Context, Query
from app.core.errors import AuthenticationError
from app.modules.accounts.models import CurrentUser
from app.modules.accounts.persistence.tables import AppUser
from app.modules.accounts.values import UserId


# Asked by GET /auth/user with the user id of the request's session (web/auth.py's Principal).
class GetCurrentUser(Query[CurrentUser]):
    """The person's profile. Raises AuthenticationError if they're gone (the session can't stand for anyone)."""

    user_id: UserId


def get_current_user(ctx: Context, query: GetCurrentUser) -> CurrentUser:
    """The user's profile as last refreshed at sign-in."""
    user = ctx.session.get(AppUser, query.user_id)
    if user is None:
        raise AuthenticationError(f"user {query.user_id} doesn't exist")
    return CurrentUser.model_validate(user)
