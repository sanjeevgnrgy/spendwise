"""How the API reports every error: RFC 9457 "problem details" (application/problem+json), in one shape.

Handlers raise core/errors.py's AppError subclasses without knowing anything about HTTP; this file turns them,
FastAPI's validation errors and its own 404/405 into problem responses. Validation errors (422) add
"errors": [{"location": "body", "field": "amount", "message": "..."}]. Anything else is a bug, and
UnexpectedErrorMiddleware answers it with a generic 500.

Web layer. main.py installs register_error_handlers and UnexpectedErrorMiddleware, the MCP HTTP endpoint
(modules/mcp/http.py) answers its 401 with problem_response, and the export script hands PROBLEM_JSON to the web app.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import AppError
from app.core.i18n import text
from app.web.dependencies import get_language, language_of
from app.web.i18n import WebText

logger = logging.getLogger(__name__)

PROBLEM_JSON = "application/problem+json"
# Problem "type" URIs identify the kind of error. RFC 9457 allows a non-resolvable URI: a stable name
# (there's no public documentation site to point them at yet).
PROBLEM_TYPE_PREFIX = "urn:spendwise:problem:"

# Problem types for errors that aren't AppErrors: FastAPI's validation errors, its own HTTP errors (404, 405),
# and the MCP endpoint's 401. (A bug's detail, all a client is ever told about it, is WebText.UNEXPECTED.)
VALIDATION_SLUG = "validation"
HTTP_SLUG = "http"
UNAUTHORIZED_SLUG = "unauthorized"


def problem_response(
    status: int, slug: str, title: str, detail: str, instance: str, headers: dict[str, str] | None = None, **extra: Any
) -> JSONResponse:
    """One problem-details response. Used here and by any other adapter (e.g. the MCP endpoint's 401).

    `slug` becomes the "type" URI (urn:spendwise:problem:<slug>), and `instance` is the request's path. Each
    `extra` keyword becomes one more member of the body (a validation error's "errors" list). `headers` are
    sent as given (Allow on a 405, WWW-Authenticate on a 401).
    """
    body = {
        "type": PROBLEM_TYPE_PREFIX + slug, "title": title, "status": status, "detail": detail, "instance": instance
    }
    return JSONResponse(status_code=status, content={**body, **extra}, media_type=PROBLEM_JSON, headers=headers)


class UnexpectedErrorMiddleware:
    """Turns an unexpected exception (a bug) into a 500 problem response.

    Added *inside* CORS (main.py), so even this response carries the CORS headers and the browser can
    read it. (FastAPI's catch-all handler runs outside every middleware, where CORS can't reach it.)
    A streaming response that has already started can't be replaced, so then the error is re-raised.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Wrap `app`, the rest of the middleware stack and the routes."""
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass the request on. If it raises before the response has started, answer with a 500 problem instead."""
        if scope["type"] != "http":
            # Startup/shutdown (lifespan) and websocket events pass straight through: only HTTP gets a 500 here.
            await self._app(scope, receive, send)
            return
        started = False

        async def tracking_send(message: Message) -> None:
            """Forward each message, noting when the response has started (its status and headers sent)."""
            nonlocal started
            started = started or message["type"] == "http.response.start"
            await send(message)

        try:
            await self._app(scope, receive, tracking_send)
        except Exception:
            if started:
                raise
            # A bug: the details go to the server log, never to the client (they can leak internals).
            logger.exception("unhandled error on %s %s", scope.get("method"), scope.get("path"))
            # In the request's language, read from the raw headers: a middleware has no Request to depend on.
            detail = text(language_of(Headers(scope=scope)), WebText.UNEXPECTED)
            response = problem_response(500, AppError.slug, AppError.title, detail, scope.get("path", ""))
            await response(scope, receive, send)


def register_error_handlers(app: FastAPI) -> None:
    """Install the handlers that turn errors into problem details. Called once, by main.create_app.

    - an AppError a handler raised -> its own status, type and title, with its message as the detail;
    - RequestValidationError (FastAPI refused the body, query or path) -> a 422 listing every problem;
    - Starlette's HTTPException (FastAPI's own 404 and 405, or one a route raises) -> its status and headers.

    Anything else is a bug, and UnexpectedErrorMiddleware turns it into a 500.
    """

    async def app_error(request: Request, exc: Exception) -> JSONResponse:
        """An AppError -> its problem response; the error's message, in the request's language, is the detail."""
        # FastAPI only calls this for an AppError; the fallback just narrows the type for the type checker.
        error = exc if isinstance(exc, AppError) else AppError()
        detail = error.message_in(get_language(request))
        return problem_response(error.status, error.slug, error.title, detail, request.url.path)

    async def invalid_request(request: Request, exc: Exception) -> JSONResponse:
        """A 422 with every invalid value under "errors", and a one-line summary of them as the detail."""
        assert isinstance(exc, RequestValidationError)
        errors = [
            # loc is ("body", "amount") or ("query", "month"): where the bad value was, then which one.
            {"location": str(e["loc"][0]), "field": ".".join(str(part) for part in e["loc"][1:]), "message": e["msg"]}
            for e in exc.errors()
        ]
        summary = "; ".join(f"{e['field'] or e['location']}: {e['message']}" for e in errors)
        return problem_response(422, VALIDATION_SLUG, "Invalid request", summary, request.url.path, errors=errors)

    async def http_error(request: Request, exc: Exception) -> JSONResponse:
        """An HTTP error as a problem; its short message ("Method Not Allowed") is both title and detail."""
        # FastAPI's own errors (404 for an unknown URL, 405 for a wrong method), in the same shape. Their
        # headers are kept: a 405 must say which methods are allowed (Allow), a 401 how to authenticate.
        assert isinstance(exc, HTTPException)
        detail = str(exc.detail)
        return problem_response(exc.status_code, HTTP_SLUG, detail, detail, request.url.path, headers=exc.headers)

    app.add_exception_handler(AppError, app_error)
    app.add_exception_handler(RequestValidationError, invalid_request)
    app.add_exception_handler(HTTPException, http_error)
