"""What every MCP tool shares: argument types, annotations, the error rules and the contract check.

Part of the mcp adapter. The tools in this folder (one file each) build themselves from these pieces, so a
rule (how errors reach the client, what "not given" means) is written once. Nothing outside the mcp module
uses this file.
"""

import inspect
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Annotated, Any

from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field, ValidationError
from sqlalchemy.exc import OperationalError

from app.core.ids import RecordId
from app.core.errors import AuthenticationError, BusinessRuleError, NotFoundError
from app.modules import expenses
from app.modules.mcp.contracts import ToolName

BUSY = "The database is busy right now; try again in a moment."
# SQLite's own names for "another connection holds the lock": worth a retry, unlike other database errors.
_LOCK_ERRORS = ("SQLITE_BUSY", "SQLITE_LOCKED")

# MCP tool annotations: hints telling clients what a tool does to data. The assistant uses
# read_only_hint to know when the pages must refresh; other clients (e.g. Claude Desktop) may use
# them to decide when to ask the user first. Hints only: a client should trust them from its own servers.
READS_ONLY = ToolAnnotations(read_only_hint=True)
ADDS_DATA = ToolAnnotations(read_only_hint=False, destructive_hint=False)
CHANGES_DATA = ToolAnnotations(read_only_hint=False, destructive_hint=True)  # overwrites or removes

# The payment methods as the tools' argument descriptions list them ("cash, upi, ..."), from the
# expenses module's enum, so a new method shows up in the descriptions by itself.
PAYMENT_METHODS = ", ".join(expenses.PaymentMethod)
# Every tool that names one expense takes its id with this type: the same id rules as the REST API
# (a whole number from 1 up), and a description that points the model at list_expenses to find it.
ExpenseIdArg = Annotated[RecordId, Field(description=f"The expense's id (see {ToolName.LIST_EXPENSES}).")]

# Optional text arguments are plain `str`, with "" meaning "not given". Models often fill unused
# optional strings with "", and the SDK reads non-`str` arguments as JSON first (so the text "null"
# would quietly become None, and "[1, 2]" a list).


def given(value: str) -> str | None:
    """An optional text argument's value, or None if it wasn't given ("" or only spaces)."""
    return value.strip() or None


def is_lock_error(exc: OperationalError) -> bool:
    """Whether a database error means "another connection holds the lock" (SQLITE_BUSY or SQLITE_LOCKED).

    Only these are worth a retry. The driver names the SQLite error on the original exception; any other
    database error returns False.
    """
    return getattr(exc.orig, "sqlite_errorname", None) in _LOCK_ERRORS


@contextmanager
def tool_errors() -> Iterator[None]:
    """Report expected problems to the client as tool errors.

    The SDK hides the text of unexpected exceptions from clients (it could leak internals) and only
    passes on a ToolError's message. Our expected errors (unknown category, amount <= 0, bad date,
    missing expense, no signed-in caller) are safe and useful to show, so they become ToolErrors. A locked database becomes
    ToolError(BUSY); every other exception passes through unchanged.
    """
    try:
        yield
    except (AuthenticationError, BusinessRuleError, NotFoundError, ValidationError) as exc:
        raise ToolError(str(exc)) from exc
    except OperationalError as exc:
        # "Database is locked" (another process, e.g. the stdio server, is writing) is worth a retry. Any
        # other database error (say, a missing table) is a real problem, and must not pass for "busy".
        if is_lock_error(exc):
            raise ToolError(BUSY) from exc
        raise


def require_arguments(tool: Callable[..., Any], *names: str) -> None:
    """Raise RuntimeError unless the tool function has a parameter for each of these argument names.

    The contract (contracts.py) names arguments other code relies on: the assistant sends them. Each
    registrar checks its tool when the server is built, so a renamed parameter fails at start-up, not at
    the first call.
    """
    missing = set(names) - set(inspect.signature(tool).parameters)
    if missing:
        raise RuntimeError(f"MCP tool {tool.__name__} lacks the arguments its contract names: {sorted(missing)}")
