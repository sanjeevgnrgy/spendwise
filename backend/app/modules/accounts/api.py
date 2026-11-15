"""HTTP routes for signing in and out: they only translate HTTP (cookies, redirects) into the use cases.

The accounts module's REST adapter. module.create_router builds the router around the use cases, and the composition
root mounts it under /api/v1, without the session check the other modules' routes get. login, callback and logout are
browser navigations, answered with redirects; options and user are API calls (they need X-CSRF, D186);
backchannel-logout is the provider calling, server to server.
"""

import hmac
import logging
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import ForbiddenError
from app.core.i18n import translatable
from app.core.identity import IdentityError
from app.modules.accounts.application.sign_in import SignInFailedError, SignInFlow
from app.modules.accounts.application.sign_out import SignOutFlow
from app.modules.accounts.models import LoginOptionRead, SignedInUser
from app.modules.accounts.queries.get_current_user import GetCurrentUser
from app.modules.accounts.values import (
    AUTH_PATH,
    HANDLE_LENGTH,
    MAX_OPTION_LENGTH,
    MAX_URL_LENGTH,
    SIGN_IN_PAGE,
    SignInFailure,
    SignInParam,
)
from app.web.auth import CookiesDep, CurrentUserDep, optional_user, require_csrf
from app.web.dependencies import BusDep
from app.web.i18n import WebText

logger = logging.getLogger(__name__)

TAG = "auth"
# The sign-out route's name: /auth/user builds its link with url_for (the same as the function's name, so the
# OpenAPI operation keeps its id).
LOGOUT_ROUTE = "logout"
# Redirects that carry a sign-in's state must never be cached, by the browser or a proxy.
NO_STORE = {"Cache-Control": "no-store"}
# Bounds for what the provider sends back: far more than any real code or state, so a huge value is a 422.
MAX_CODE_LENGTH = 2048
MAX_STATE_LENGTH = 256
# A logout token is a signed JWT: a few kilobytes at most.
MAX_LOGOUT_TOKEN_LENGTH = 16_384


# The provider's back-channel logout request (application/x-www-form-urlencoded): the signed logout token. Other
# fields may come with it and are ignored, as the spec asks (Back-Channel Logout 1.0, 2.5).
class BackchannelLogoutForm(BaseModel):
    model_config = ConfigDict(extra="ignore")

    logout_token: str = Field(min_length=1, max_length=MAX_LOGOUT_TOKEN_LENGTH)


def _redirect(location: str) -> RedirectResponse:
    """A 302 to `location`, never cached."""
    return RedirectResponse(location, status_code=302, headers=NO_STORE)


def _sign_in_page(failure: SignInFailure) -> RedirectResponse:
    """Back to the web app's sign-in page, saying why the sign-in failed (a code, never the details)."""
    return _redirect(f"{SIGN_IN_PAGE}?{urlencode({SignInParam.ERROR.value: failure.value})}")


def create_router(sign_in: SignInFlow, sign_out: SignOutFlow) -> APIRouter:
    """The sign-in routes, around the use cases handed in. Plain `def` routes: they wait on the provider and the
    database, so FastAPI runs them in a worker thread."""
    router = APIRouter(prefix=AUTH_PATH, tags=[TAG])
    _add_sign_in_routes(router, sign_in)
    _add_session_routes(router, sign_out)
    return router


def _add_sign_in_routes(router: APIRouter, sign_in: SignInFlow) -> None:
    """The routes that start a session: the buttons, the way out to the provider, and the way back."""

    # GET /api/v1/auth/options: the sign-in page's buttons ([] when it should offer the provider's own page).
    @router.get("/options", dependencies=[Depends(require_csrf)])
    def login_options() -> list[LoginOptionRead]:
        return sign_in.options()

    # GET /api/v1/auth/login?option=google&return_to=/expenses: start signing in. A navigation, not an API call:
    # 302 to the provider, with a short-lived login cookie that ties the sign-in to this browser. If the provider
    # can't be used, 302 to the sign-in page with ?error=unavailable.
    @router.get("/login", response_class=RedirectResponse, status_code=302)
    def login(
        request: Request,
        cookies: CookiesDep,
        option: Annotated[str | None, Query(alias=SignInParam.OPTION.value, max_length=MAX_OPTION_LENGTH)] = None,
        return_to: Annotated[str | None, Query(alias=SignInParam.RETURN_TO.value, max_length=MAX_URL_LENGTH)] = None,
    ) -> RedirectResponse:
        current = cookies.read_session(request)
        try:
            started = sign_in.begin(option, return_to, current)
        except IdentityError as failure:
            logger.warning("sign-in can't start: %s", failure)
            return _sign_in_page(SignInFailure.UNAVAILABLE)
        response = _redirect(started.authorization_url)
        cookies.set_login(response, started.login_key)
        if current:
            cookies.clear_session(response)
        return response

    # GET /api/v1/auth/callback?code=...&state=...: where the provider sends the browser back (the registered
    # redirect URI). 302 to the page the sign-in started from, with the session cookie; or to the sign-in page with
    # ?error=<SignInFailure>. Either way the login cookie is cleared: each sign-in completes once.
    @router.get("/callback", response_class=RedirectResponse, status_code=302)
    def callback(
        request: Request,
        cookies: CookiesDep,
        code: Annotated[str | None, Query(max_length=MAX_CODE_LENGTH)] = None,
        state: Annotated[str | None, Query(max_length=MAX_STATE_LENGTH)] = None,
        error: Annotated[str | None, Query(max_length=MAX_STATE_LENGTH)] = None,
    ) -> RedirectResponse:
        try:
            finished = sign_in.finish(cookies.read_login(request), state, code, error)
        except SignInFailedError as failure:
            response = _sign_in_page(failure.reason)
        else:
            response = _redirect(finished.return_to)
            cookies.set_session(response, finished.session_key)
        cookies.clear_login(response)
        return response


def _add_session_routes(router: APIRouter, sign_out: SignOutFlow) -> None:
    """The routes about a session that exists: who it is, signing it out, and the provider ending it."""

    # GET /api/v1/auth/user: who is signed in, and their sign-out link. 401 when nobody is (the web app then shows
    # the sign-in page).
    @router.get("/user", dependencies=[Depends(require_csrf)])
    def current_user(principal: CurrentUserDep, bus: BusDep, request: Request) -> SignedInUser:
        user = bus.ask(GetCurrentUser(user_id=principal.user_id))
        query = urlencode({SignInParam.SESSION.value: principal.session_handle})
        logout_url = f"{request.url_for(LOGOUT_ROUTE).path}?{query}"
        return SignedInUser(**user.model_dump(), logout_url=logout_url)

    # GET /api/v1/auth/logout?sid=<handle>: sign this browser out, here and at the provider. A navigation: 302 to the
    # provider's sign-out page (or the sign-in page). The handle (from /auth/user's logout_url) must be this
    # session's, so a link on another site can't sign anyone out: 403 otherwise.
    @router.get("/logout", response_class=RedirectResponse, status_code=302, name=LOGOUT_ROUTE)
    def logout(
        request: Request,
        cookies: CookiesDep,
        sid: Annotated[str | None, Query(alias=SignInParam.SESSION.value, max_length=HANDLE_LENGTH)] = None,
    ) -> RedirectResponse:
        principal = optional_user(request)
        if principal is None:
            response = _redirect(SIGN_IN_PAGE)
        elif sid is None or not hmac.compare_digest(sid.encode(), principal.session_handle.encode()):
            raise ForbiddenError(translatable(WebText.NOT_FROM_APP))
        else:
            response = _redirect(sign_out.sign_out(principal))
        cookies.clear_session(response)
        return response

    # POST /api/v1/auth/backchannel-logout: the provider says a session ended there (OIDC Back-Channel Logout 1.0):
    # a form with a signed logout_token. 200 once the matching sessions have ended; 400 if the token fails a check.
    @router.post("/backchannel-logout")
    def backchannel_logout(form: Annotated[BackchannelLogoutForm, Form()]) -> Response:
        sign_out.back_channel(form.logout_token)
        return Response(headers=NO_STORE)
