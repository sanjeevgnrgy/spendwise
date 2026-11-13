"""Errors that services raise for expected problems, and how the API reports them.

Services raise these without knowing anything about HTTP. One place below turns them
into status codes, so routers don't need a try/except in every endpoint.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class NotFoundError(Exception):
    """The thing asked for doesn't exist. Reported as 404."""


class BusinessRuleError(Exception):
    """The request is well-formed but breaks a business rule. Reported as 422."""


class ExternalServiceError(Exception):
    """A service we depend on (like Gemini) failed or gave an unusable answer. Reported as 502."""


def register_error_handlers(app: FastAPI) -> None:
    async def not_found(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    async def rule_broken(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    async def bad_gateway(request: Request, exc: Exception) -> JSONResponse:
        # 502 means "a service we depend on failed", which is different from a bug here (500).
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    app.add_exception_handler(NotFoundError, not_found)
    app.add_exception_handler(BusinessRuleError, rule_broken)
    app.add_exception_handler(ExternalServiceError, bad_gateway)
