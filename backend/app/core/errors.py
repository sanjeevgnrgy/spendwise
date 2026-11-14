"""Errors that handlers raise for expected problems: not found, a broken business rule, a failed outside service.

Handlers raise these without knowing anything about HTTP. Each kind carries the status, problem type (`slug`) and
title it becomes; web/problems.py turns every error into an RFC 9457 "problem details" response
(application/problem+json), so all errors have one shape:

    {"type": "urn:spendwise:problem:not-found", "title": "Not found", "status": 404,
     "detail": "Expense 14 not found", "instance": "/api/v1/expenses/14"}

Core layer: it imports no framework. Handlers and use cases in every module raise the AppError subclasses (core/llm's
LlmError is an ExternalServiceError); web/problems.py reports them.
"""

from typing import ClassVar


class AppError(Exception):
    """An expected problem. Subclasses say which HTTP status and problem type it becomes.

    Raise one with a message written for the user: it becomes the problem's "detail". `slug` is the end of the
    problem's "type" URI, and `title` a short summary that's the same for every error of the kind. AppError
    itself stands for an internal error (500): UnexpectedErrorMiddleware reports a bug with its slug and title.
    """

    status: ClassVar[int] = 500
    slug: ClassVar[str] = "internal"
    title: ClassVar[str] = "Internal error"


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
