"""CreateAccessToken: keep a new personal access token's hash for its owner. The command and its handler.

A slice of the accounts module's write side. The access-token use case (application/access_tokens.py) makes the
token, sends this with its hash, and shows the token to its owner once; the token itself is never stored (D191).
"""

from datetime import datetime

from pydantic import Field
from sqlmodel import func, select

from app.core.cqrs import Command, Context
from app.core.errors import BusinessRuleError
from app.core.i18n import translatable
from app.core.ids import UserId
from app.modules.accounts.i18n import AccountText
from app.modules.accounts.persistence.tables import AccessToken
from app.modules.accounts.values import KEY_HASH_LENGTH, MAX_ACCESS_TOKENS, MAX_TOKEN_NAME_LENGTH, TOKEN_HINT_LENGTH


# Sent by AccessTokens.create only. The owner is the signed-in person; the hash and hint come from the token it made.
class CreateAccessToken(Command[int]):
    """Keep a new token for `owner_id`. Returns its id. Raises BusinessRuleError past MAX_ACCESS_TOKENS."""

    owner_id: UserId
    name: str = Field(min_length=1, max_length=MAX_TOKEN_NAME_LENGTH)
    token_hash: str = Field(min_length=KEY_HASH_LENGTH, max_length=KEY_HASH_LENGTH)
    hint: str = Field(min_length=1, max_length=TOKEN_HINT_LENGTH)
    expires_at: datetime


def create_access_token(ctx: Context, command: CreateAccessToken) -> int:
    """Add the token's row and return its id.

    Raises BusinessRuleError if the owner already has MAX_ACCESS_TOKENS tokens that still work (expired ones don't
    count: they can be revoked from the list), so nobody piles up tokens they've forgotten.
    """
    now = ctx.clock.now()
    working = select(func.count()).where(AccessToken.user_id == command.owner_id, AccessToken.expires_at > now)
    if ctx.session.exec(working).one() >= MAX_ACCESS_TOKENS:
        raise BusinessRuleError(translatable(AccountText.TOO_MANY_TOKENS, max=MAX_ACCESS_TOKENS))
    row = AccessToken(
        user_id=command.owner_id,
        name=command.name,
        token_hash=command.token_hash,
        hint=command.hint,
        created_at=now,
        expires_at=command.expires_at,
    )
    ctx.session.add(row)
    # flush sends the INSERT inside the transaction, so the database assigns the id now.
    ctx.session.flush()
    assert row.id is not None
    return row.id
