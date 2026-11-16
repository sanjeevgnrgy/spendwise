"""Errors that handlers raise for expected problems: not found, a broken business rule, a failed outside service.

Handlers raise these without knowing anything about HTTP. Each kind carries the status, problem type (`slug`) and
title it becomes; web/problems.py turns every error into an RFC 9457 "problem details" response
(application/problem+json), so all errors have one shape:

    {"type": "urn:spendwise:problem:not-found", "title": "Not found", "status": 404,
     "detail": "Expense 14 not found", "instance": "/api/v1/expenses/14"}

Core layer: it imports no framework. Handlers and use cases in every module raise the AppError subclasses (core/llm's
LlmError is an ExternalServiceError); web/problems.py reports them, in the request's language.
"""

from typing import ClassVar

from app.core.i18n import Language, Translatable


class AppError(Exception):
    """An expected problem. Subclasses say which HTTP status and problem type it becomes.

    Raise one with a Translatable (a catalogued text and its values) when a person may read it: it becomes the
    problem's "detail", written in the reader's language (web/problems.py: the request's). A plain string is never
    shown to a person (D180): it's an outside service's own words or a note for developers, which can carry internals,
    so it goes to the server log and the person gets a generic text for the kind of error. str(error) is the English
    text, for logs and for MCP clients. `slug` is the end of the problem's "type" URI (and a run error's code), and
    `title` a short summary that's the same for every error of the kind. AppError itself stands for an internal error
    (500): UnexpectedErrorMiddleware reports a bug with its slug and title.
    """

    status: ClassVar[int] = 500
    slug: ClassVar[str] = "internal"
    title: ClassVar[str] = "Internal error"

    def __init__(self, message: str | Translatable = "") -> None:
        """An error with `message` as its detail (the English text is also the exception's own message)."""
        super().__init__(str(message))
        self.text = message

    def message_in(self, language: Language) -> str | None:
        """The detail for a person, in `language`; None if the message isn't written for people (a plain string)."""
        return self.text.in_language(language) if isinstance(self.text, Translatable) else None


class NotFoundError(AppError):
    """The thing asked for doesn't exist."""

    status = 404
    slug = "not-found"
    title = "Not found"


class BusinessRuleError(AppError):
    """The request is well-formed but breaks a business rule."""

    status = 422
    slug = "business-rule"
    title = "Business rule broken"


class ExternalServiceError(AppError):
    """A service we depend on (the model, a remote MCP server) failed or gave an unusable answer."""

    # 502 means "a service we depend on failed", which is different from a bug here (500).
    status = 502
    slug = "external-service"
    title = "A service we depend on failed"


class AuthenticationError(AppError):
    """The request needs a signed-in person, and has no live session (none, expired, revoked or unknown)."""

    status = 401
    slug = "unauthorized"
    title = "Sign-in required"


class ForbiddenError(AppError):
    """The request is refused whoever sends it: it didn't come from the app itself (D186), or isn't allowed."""

    status = 403
    slug = "forbidden"
    title = "Forbidden"

class TooManyRequestsError(AppError):
    """The person has used up an allowance (the model-backed routes' rate limit, D194): try again later."""

    status = 429
    slug = "too-many-requests"
    title = "Too many requests"

    def __init__(self, message: str | Translatable, retry_after_seconds: int) -> None:
        """A refusal with `message` as its detail, and how many seconds until it's worth trying again."""
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
