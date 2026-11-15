"""Who a request comes from, and whether the app itself sent it: the session cookie, the X-CSRF check (web layer).

The browser holds one cookie: a random key (HttpOnly, so scripts can't read it; SameSite=Strict, so it's only sent
on requests the app's own pages make). The key stands for a session kept on the server (D186). main.create_app
protects every module's routes with require_csrf and require_user; the accounts module's routes use the cookie
helpers and CurrentUserDep. The session check itself is the accounts module's, put on `app.state.authenticate` by
main.create_app, so this file imports no module.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends, Request, Response

from app.core.errors import AuthenticationError, ForbiddenError
from app.core.i18n import translatable
from app.core.identity import Principal
from app.web.i18n import WebText

# Every API call from the web app carries this header (D186). Another site can't add a header to a request without
# the browser asking the API first (a CORS preflight), which it refuses, so the header proves the app sent it.
CSRF_HEADER = "X-CSRF"
CSRF_VALUE = "1"
# The browser's own word on where a request comes from (Fetch Metadata). When it's there, only the app's own origin
# ("same-origin") or the person typing an address ("none") is accepted.
FETCH_SITE_HEADER = "Sec-Fetch-Site"
OWN_SITES = frozenset({"same-origin", "none"})

# The cookies' names. "__Host-" makes the browser insist on Secure, Path=/ and no Domain, so no other host (not even
# a subdomain) can set or read them; it's only usable with Secure, so it's dropped when cookies aren't Secure.
HOST_PREFIX = "__Host-"
SESSION_COOKIE = "spendwise-session"
LOGIN_COOKIE = "spendwise-login"
ROOT_PATH = "/"

# Turns a session cookie's key into the person it stands for, or None (the accounts module's SessionGate).
Authenticator = Callable[[str], Principal | None]
SameSite = Literal["strict", "lax"]


@dataclass(frozen=True)
class SessionCookies:
    """How the two cookies are written: the session's (SameSite=Strict) and the short-lived login one (Lax).

    The login cookie is Lax because it must come back on the provider's redirect to the callback, a navigation that
    starts on another site; Strict cookies aren't sent on those. Built once by the composition root.
    """

    secure: bool
    session_max_age: int
    login_max_age: int

    def _name(self, name: str) -> str:
        """`name`, with the __Host- prefix when the cookies are Secure."""
        return HOST_PREFIX + name if self.secure else name

    def read_session(self, request: Request) -> str | None:
        """The session cookie's key, if the request carries one."""
        return request.cookies.get(self._name(SESSION_COOKIE)) or None

    def read_login(self, request: Request) -> str | None:
        """The login cookie's key, if the request carries one."""
        return request.cookies.get(self._name(LOGIN_COOKIE)) or None

    def _set(self, response: Response, name: str, value: str, max_age: int, same_site: SameSite) -> None:
        """Write one HttpOnly cookie for the whole site."""
        response.set_cookie(
            self._name(name), value, max_age=max_age, path=ROOT_PATH, secure=self.secure, httponly=True,
            samesite=same_site,
        )

    def set_session(self, response: Response, key: str) -> None:
        """Give the browser its session key, kept for the session's whole lifetime (the server ends it sooner)."""
        self._set(response, SESSION_COOKIE, key, self.session_max_age, "strict")

    def set_login(self, response: Response, key: str) -> None:
        """Give the browser the key of the sign-in it's starting."""
        self._set(response, LOGIN_COOKIE, key, self.login_max_age, "lax")

    def clear_session(self, response: Response) -> None:
        """Tell the browser to forget its session key."""
        response.delete_cookie(
            self._name(SESSION_COOKIE), path=ROOT_PATH, secure=self.secure, httponly=True, samesite="strict"
        )

    def clear_login(self, response: Response) -> None:
        """Tell the browser to forget the login cookie (the sign-in it started is over)."""
        response.delete_cookie(
            self._name(LOGIN_COOKIE), path=ROOT_PATH, secure=self.secure, httponly=True, samesite="lax"
        )


def get_cookies(request: Request) -> SessionCookies:
    """The app's cookie settings, as main.create_app stored them."""
    return request.app.state.cookies


def optional_user(request: Request) -> Principal | None:
    """The person the request's session cookie stands for; None without a live session."""
    key = get_cookies(request).read_session(request)
    authenticate: Authenticator = request.app.state.authenticate
    return authenticate(key) if key else None


def require_user(request: Request) -> Principal:
    """The person the request comes from. Raises AuthenticationError (401) without a live session."""
    principal = optional_user(request)
    if principal is None:
        raise AuthenticationError(translatable(WebText.SIGN_IN_REQUIRED))
    return principal


def require_csrf(request: Request) -> None:
    """Refuse a request the app's own pages didn't send: no X-CSRF header, or the browser says it comes from
    another site. Raises ForbiddenError (403). Read from the headers, not declared, so it stays out of OpenAPI."""
    site = request.headers.get(FETCH_SITE_HEADER)
    if request.headers.get(CSRF_HEADER) != CSRF_VALUE or (site is not None and site not in OWN_SITES):
        raise ForbiddenError(translatable(WebText.NOT_FROM_APP))


# Annotated types, so a route parameter only needs `user: CurrentUserDep`.
CookiesDep = Annotated[SessionCookies, Depends(get_cookies)]
CurrentUserDep = Annotated[Principal, Depends(require_user)]
