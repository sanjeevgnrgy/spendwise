"""Personal access tokens: making one for its owner, and turning one an MCP client sends into the person it acts for
(D191). Part of the accounts module's use cases (application/).

The account routes (account_api.py) create tokens with it; the composition root hands `resolve` to the MCP
endpoint (mcp/http.py) and the stdio server (backend/mcp_stdio.py). A token is shown to its owner once, as it's made:
only its SHA-256 is kept, so neither the database nor a log can give one away.
"""

from dataclasses import dataclass
from datetime import timedelta

from app.core.clock import Clock, as_utc
from app.core.cqrs import MessageBus
from app.modules.accounts.commands.create_access_token import CreateAccessToken
from app.modules.accounts.commands.touch_access_token import TouchAccessToken
from app.modules.accounts.domain.keys import hash_key, new_access_token
from app.modules.accounts.models import CreatedAccessToken, NewAccessToken
from app.modules.accounts.queries.find_token_owner import FindTokenOwner
from app.modules.accounts.queries.list_access_tokens import ListAccessTokens
from app.modules.accounts.values import (
    ACCESS_TOKEN_LENGTH,
    ACCESS_TOKEN_PREFIX,
    TOKEN_HINT_LENGTH,
    TOKEN_TOUCH_AFTER,
)


@dataclass(frozen=True)
class AccessTokens:
    """Makes and resolves personal access tokens. Needs the bus and the clock (expiry, last use)."""

    bus: MessageBus
    clock: Clock

    def create(self, owner_id: int, request: NewAccessToken) -> CreatedAccessToken:
        """A new token for `owner_id`, named and lasting as asked: its details and the token itself, which is never
        available again. Raises BusinessRuleError if they already have the most tokens allowed."""
        token = new_access_token()
        expires_at = self.clock.now() + timedelta(days=request.lifetime_days)
        token_id = self.bus.execute(
            CreateAccessToken(
                owner_id=owner_id,
                name=request.name,
                token_hash=hash_key(token),
                hint=token[-TOKEN_HINT_LENGTH:],
                expires_at=expires_at,
            )
        )
        made = next(item for item in self.bus.ask(ListAccessTokens(owner_id=owner_id)) if item.id == token_id)
        return CreatedAccessToken(**made.model_dump(), token=token)

    def resolve(self, token: str) -> int | None:
        """The user id `token` acts for, or None if it doesn't work (malformed, unknown, revoked, expired, or its
        owner switched off). Notes the token's use, at most once per TOKEN_TOUCH_AFTER."""
        # Anything that can't be a token isn't looked up at all.
        if len(token) != ACCESS_TOKEN_LENGTH or not token.startswith(ACCESS_TOKEN_PREFIX):
            return None
        owner = self.bus.ask(FindTokenOwner(token_hash=hash_key(token)))
        if owner is None:
            return None
        last_used = owner.last_used_at
        if last_used is None or self.clock.now() - as_utc(last_used) >= TOKEN_TOUCH_AFTER:
            self.bus.execute(TouchAccessToken(token_id=owner.token_id))
        return owner.user_id
