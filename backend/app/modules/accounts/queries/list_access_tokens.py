"""ListAccessTokens: a person's access tokens, newest first. The query and its handler; it changes nothing.

A slice of the accounts module's read side, asked by GET /account/tokens (account_api.py) for the signed-in person,
and by AccessTokens.create to answer with the new one. Never the tokens themselves: only their hashes are stored.
"""

from sqlmodel import col, select

from app.core.clock import as_utc
from app.core.cqrs import Context, Query
from app.core.ids import UserId
from app.modules.accounts.models import AccessTokenRead
from app.modules.accounts.persistence.tables import AccessToken


# Only the owner's tokens (D190), expired ones included (they're marked by their expires_at, and can be revoked).
class ListAccessTokens(Query[list[AccessTokenRead]]):
    owner_id: UserId


def list_access_tokens(ctx: Context, query: ListAccessTokens) -> list[AccessTokenRead]:
    """The owner's tokens, newest first, each marked if it has expired by the clock's now."""
    now = ctx.clock.now()
    statement = (
        select(AccessToken)
        .where(AccessToken.user_id == query.owner_id)
        .order_by(col(AccessToken.created_at).desc(), col(AccessToken.id).desc())
    )
    return [
        AccessTokenRead.model_validate(row).model_copy(update={"expired": as_utc(row.expires_at) <= now})
        for row in ctx.session.exec(statement)
    ]
