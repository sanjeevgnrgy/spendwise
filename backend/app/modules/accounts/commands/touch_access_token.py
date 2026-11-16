"""TouchAccessToken: note that a token was just used. The command and its handler.

A slice of the accounts module's write side. AccessTokens.resolve sends it when a token works, at most once per
TOKEN_TOUCH_AFTER, so Settings can show when each token was last used without a write on every MCP request.
"""

from sqlalchemy import update
from sqlmodel import col

from app.core.cqrs import Command, Context
from app.modules.accounts.persistence.tables import AccessToken
from app.modules.accounts.values import TokenId


# Sent only by AccessTokens.resolve, for a token it has just found working (so it's someone's own).
class TouchAccessToken(Command[None]):
    token_id: TokenId


def touch_access_token(ctx: Context, command: TouchAccessToken) -> None:
    """Set the token's last use to the clock's now. A token revoked meanwhile is simply not found (nothing changes)."""
    statement = update(AccessToken).where(col(AccessToken.id) == command.token_id).values(last_used_at=ctx.clock.now())
    ctx.session.execute(statement)
