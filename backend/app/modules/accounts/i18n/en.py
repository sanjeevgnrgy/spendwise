"""The accounts module's texts for people, in English: the keys (AccountText) and the source every other language
translates (hi.py). Part of the accounts module (i18n/); the catalog is registered by __init__.py. The texts about
signing in (401, 403) are the web layer's (web/i18n/), since every module's routes share them."""

from enum import StrEnum

from app.core.i18n import TextValue


class AccountText(StrEnum):
    """The accounts module's texts, by key."""

    TOKEN_NOT_FOUND = "errors.tokenNotFound"
    SESSION_NOT_FOUND = "errors.sessionNotFound"
    TOO_MANY_TOKENS = "errors.tooManyTokens"


EN: dict[AccountText, TextValue] = {
    # Also another person's token or session: it isn't theirs to see, so it's "not found" (D190).
    AccountText.TOKEN_NOT_FOUND: "Access token {token_id} not found",
    AccountText.SESSION_NOT_FOUND: "Session {session_id} not found",
    # {max} is MAX_ACCESS_TOKENS.
    AccountText.TOO_MANY_TOKENS: "You can have at most {max} access tokens. Revoke one you no longer use first.",
}
