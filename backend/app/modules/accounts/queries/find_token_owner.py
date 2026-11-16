"""FindTokenOwner: whose a personal access token is, if it still works. The query and its handler; it changes nothing.

A slice of the accounts module's read side, asked by AccessTokens.resolve for every MCP request (over HTTP, and on
every tool call of the stdio server), with the hash of the token the client sent (D191).
"""

from pydantic import Field
from sqlmodel import col, select

from app.core.cqrs import Context, Query
from app.modules.accounts.models import TokenOwner
from app.modules.accounts.persistence.tables import AccessToken, AppUser
from app.modules.accounts.values import KEY_HASH_LENGTH


class FindTokenOwner(Query[TokenOwner | None]):
    """The token's owner, if it works; None otherwise (unknown or revoked, expired, or its owner switched off)."""

    token_hash: str = Field(min_length=KEY_HASH_LENGTH, max_length=KEY_HASH_LENGTH)


def find_token_owner(ctx: Context, query: FindTokenOwner) -> TokenOwner | None:
    """The working token with that hash and its owner, or None. Looked up by the hash only (a unique index): the
    token itself is never stored, so a copy of the database can't be used to call the tools."""
    statement = (
        select(AccessToken)
        .join(AppUser, col(AppUser.id) == col(AccessToken.user_id))
        .where(
            col(AccessToken.token_hash) == query.token_hash,
            col(AccessToken.expires_at) > ctx.clock.now(),
            col(AppUser.is_active).is_(True),
        )
    )
    row = ctx.session.exec(statement).first()
    if row is None or row.id is None:
        return None
    return TokenOwner(token_id=row.id, user_id=row.user_id, last_used_at=row.last_used_at)
