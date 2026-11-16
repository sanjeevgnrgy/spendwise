"""HTTP routes for the signed-in person's own account: their sessions (the browsers they're signed in on) and their
personal access tokens, for the web app's Settings page (D192). Each route only translates HTTP into messages.

The accounts module's second REST adapter (api.py has the sign-in routes, which need no session). The composition
root mounts this router with the others, behind the X-CSRF and session checks. Every route acts for the signed-in
person: a session or token id that isn't theirs is a 404, like one that doesn't exist (D190). A route's docstring
would become its OpenAPI text, so notes are `#` comments.
"""

from fastapi import APIRouter, Response

from app.core.cqrs import MessageBus
from app.core.identity import IdentityProvider
from app.modules.accounts.application.access_tokens import AccessTokens
from app.modules.accounts.commands.revoke_access_token import RevokeAccessToken
from app.modules.accounts.commands.sign_out_other_sessions import SignOutOtherSessions
from app.modules.accounts.commands.sign_out_session import SignOutSession
from app.modules.accounts.models import AccessTokenRead, CreatedAccessToken, NewAccessToken, SessionRead
from app.modules.accounts.queries.list_access_tokens import ListAccessTokens
from app.modules.accounts.queries.list_sessions import ListSessions
from app.web.auth import CurrentUserDep
from app.web.dependencies import IdPath

TAG = "account"
ACCOUNT_PATH = "/account"
# A new token is in the answer: no browser or proxy may keep a copy.
NO_STORE = "no-store"
CACHE_CONTROL = "Cache-Control"


def create_account_router(bus: MessageBus, identity: IdentityProvider, tokens: AccessTokens) -> APIRouter:
    """The account routes, around the bus, the provider (whose sessions still work: its issuer) and the tokens."""
    router = APIRouter(prefix=ACCOUNT_PATH, tags=[TAG])

    # GET /api/v1/account/sessions: the signed-in person's live sessions, most recently used first; `current` marks
    # the browser asking.
    @router.get("/sessions")
    def list_sessions(principal: CurrentUserDep) -> list[SessionRead]:
        found = bus.ask(ListSessions(owner_id=principal.user_id, issuer=identity.issuer))
        return [item.model_copy(update={"current": item.id == principal.session_id}) for item in found]

    # DELETE /api/v1/account/sessions/{session_id}: sign that browser out (its cookie stops working at once). 404 if
    # it isn't the person's live session. Signing out this browser is better done with the sign-out link (it also
    # signs out at the provider), but works here too: the next request answers 401.
    @router.delete("/sessions/{session_id}", status_code=204)
    def sign_out_session(session_id: IdPath, principal: CurrentUserDep) -> None:
        bus.execute(SignOutSession(owner_id=principal.user_id, session_id=session_id))

    # POST /api/v1/account/sessions/sign-out-others: sign out every other browser, keeping this one.
    @router.post("/sessions/sign-out-others", status_code=204)
    def sign_out_other_sessions(principal: CurrentUserDep) -> None:
        bus.execute(SignOutOtherSessions(owner_id=principal.user_id, keep_session_id=principal.session_id))

    # GET /api/v1/account/tokens: the signed-in person's access tokens, newest first (never the tokens themselves).
    @router.get("/tokens")
    def list_tokens(principal: CurrentUserDep) -> list[AccessTokenRead]:
        return bus.ask(ListAccessTokens(owner_id=principal.user_id))

    # POST /api/v1/account/tokens: make a token for MCP clients. 201 with the token itself, the only time it's sent
    # (and never cached); 422 past the most tokens allowed.
    @router.post("/tokens", status_code=201)
    def create_token(body: NewAccessToken, principal: CurrentUserDep, response: Response) -> CreatedAccessToken:
        response.headers[CACHE_CONTROL] = NO_STORE
        return tokens.create(principal.user_id, body)

    # DELETE /api/v1/account/tokens/{token_id}: revoke a token (it stops working at once). 404 if it isn't theirs.
    @router.delete("/tokens/{token_id}", status_code=204)
    def revoke_token(token_id: IdPath, principal: CurrentUserDep) -> None:
        bus.execute(RevokeAccessToken(owner_id=principal.user_id, token_id=token_id))

    return router
