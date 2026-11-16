"""RevokeAccessToken: delete one of a person's access tokens, so it stops working at once. Command and handler.

A slice of the accounts module's write side. DELETE /account/tokens/{id} (account_api.py) sends it for the signed-in
person. The owner and the id are matched in the same statement: nobody can revoke, or learn of, another's token.
"""

from sqlalchemy import delete
from sqlmodel import col

from app.core.cqrs import Command, Context
from app.core.errors import NotFoundError
from app.core.i18n import translatable
from app.core.ids import UserId
from app.modules.accounts.i18n import AccountText
from app.modules.accounts.persistence.tables import AccessToken
from app.modules.accounts.values import TokenId


# Raises NotFoundError if the owner has no such token (another person's counts as none, D190).
class RevokeAccessToken(Command[None]):
    owner_id: UserId
    token_id: TokenId


def revoke_access_token(ctx: Context, command: RevokeAccessToken) -> None:
    """Delete the owner's token. Raises NotFoundError if they have no token by that id."""
    statement = delete(AccessToken).where(
        col(AccessToken.id) == command.token_id, col(AccessToken.user_id) == command.owner_id
    )
    if ctx.session.execute(statement).rowcount == 0:
        raise NotFoundError(translatable(AccountText.TOKEN_NOT_FOUND, token_id=command.token_id))
