"""Commands, queries, and the bus that runs them (CQRS).

- A **command** asks for a change ("create this expense") and returns at most an id.
- A **query** asks for data ("this month's summary") and changes nothing.

Each is a small frozen Pydantic model with exactly one handler. Callers know only the message types
(a module's contract) and the bus, never which function handles them or which tables they touch.

The bus is also the **unit of work**: the outermost message opens a database session, and a command's
session is committed when its handler returns and rolled back if it raises. Messages sent from inside
a handler (through ctx.bus) join that same session, so a command and the checks it makes are one
transaction; a nested command runs in a SAVEPOINT, so if it fails, only its own changes are undone.
Repositories never commit; only the bus does.

Core layer. Each module keeps every command and query with its handler in one slice file (commands/,
queries/), and its module.py registers them. The composition root (bootstrap.py) builds the one bus that
routes, the MCP server, the assistant and seed.py all send their messages through.
"""

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from app.core.clock import Clock

logger = logging.getLogger(__name__)

R = TypeVar("R")
# What the bus calls to open the session for one unit of work (infrastructure/db.session_factory makes one per engine).
SessionFactory = Callable[[], Session]
M = TypeVar("M", bound="Message")


# What every command and query has in common: an immutable, strictly checked Pydantic model.
class Message(BaseModel):
    # Frozen: a message is a fact about what was asked, so nobody changes it on the way.
    # extra="forbid": a misspelt field is an error, not a silently ignored value.
    model_config = ConfigDict(frozen=True, extra="forbid")


# Generic[R] carries the result type through the bus: bus.execute(CreateExpense(...)) is typed as the
# new expense's id, so callers get type-checked results without knowing the handler.
class Command(Message, Generic[R]):
    """A request to change data. R is what it returns: None, or the new item's id."""


# The bus enforces "no changes" for the whole query: a command sent while it runs is refused.
class Query(Message, Generic[R]):
    """A request for data, returning R. A query handler must not change anything."""


@dataclass(frozen=True)
class Context:
    """What a handler gets besides its message.

    `session` is the unit of work's open session: stage changes in it, but never commit (the bus does).
    `clock` gives "today" and timestamps, so handlers never call date.today() themselves.
    """

    session: Session
    bus: "MessageBus"  # for asking other modules, inside the same transaction
    clock: Clock


@dataclass
class _UnitOfWork:
    """The unit of work in progress: its session, and whether commands may run in it (False for a query's)."""

    session: Session
    writable: bool


class MessageBus:
    """Sends each command or query to its one handler, and owns the transaction around it.

    Built once by the composition root (bootstrap.build_bus), with the session factory
    (infrastructure/db.session_factory) and the clock that handlers receive. One bus serves every request at once:
    each thread or task sees only its own unit of work.
    """

    def __init__(self, session_factory: SessionFactory, clock: Clock) -> None:
        """A bus with no handlers yet: `session_factory` opens each unit of work's session; handlers get `clock`."""
        self._session_factory = session_factory
        self._clock = clock
        self._handlers: dict[type[Message], Callable[[Context, Any], Any]] = {}
        # The unit of work in progress in this thread (or task), if any. A ContextVar, not an attribute:
        # requests run in parallel threads, and each must only ever see its own session.
        self._current: ContextVar[_UnitOfWork | None] = ContextVar("unit_of_work", default=None)

    def register(self, message_type: type[M], handler: Callable[[Context, M], Any]) -> None:
        """Make `handler` the handler for `message_type`. Each module's register_handlers calls it at startup.

        Raises ValueError if the type already has a handler.
        """
        # Exactly one handler per message: a second registration is a wiring mistake, so fail loudly.
        if message_type in self._handlers:
            raise ValueError(f"{message_type.__name__} already has a handler")
        self._handlers[message_type] = handler

    def execute(self, command: Command[R]) -> R:
        """Run a command and return what its handler returns (None, or the new item's id).

        Outside any unit of work, it opens one: the change is committed when the handler returns, and rolled
        back if it raises. Inside a command (sent through ctx.bus) or a `with unit_of_work()` block, it runs in
        a SAVEPOINT of that transaction instead, and the outermost one commits. Raises RuntimeError when sent
        from inside a query, LookupError if nothing handles the command, and whatever the handler raises, after
        undoing the command's changes.
        """
        current = self._current.get()
        if current is None:
            with self.unit_of_work():
                return self._handle(command)
        if not current.writable:
            # A query that changes data would break the promise every caller relies on.
            raise RuntimeError(f"{type(command).__name__} can't run inside a query")
        # Inside another command: a SAVEPOINT, so a failure undoes only this command's changes, even if
        # the caller catches the error and carries on. The outermost command still commits everything.
        with current.session.begin_nested():
            return self._handle(command)

    def ask(self, query: Query[R]) -> R:
        """Run a query and return its result. Nothing is ever committed for a query.

        Inside a unit of work (a handler asking another module, say), it reads through that session, so it
        sees the transaction's changes so far. Otherwise it opens a read-only scope of its own, in which any
        command is refused. Raises LookupError if nothing handles the query, and whatever the handler raises.
        """
        if self._current.get() is not None:
            return self._handle(query)  # inside a unit of work: read through its session
        with self._scope(writable=False):
            return self._handle(query)

    @contextmanager
    def unit_of_work(self) -> Iterator[None]:
        """Run several commands as one transaction: all of them are saved, or none (e.g. the seed script).

        Each command sent inside the `with` block runs in a SAVEPOINT of this transaction. It's committed when
        the block ends normally, and rolled back if an exception leaves it. execute() uses it too, for a
        command sent on its own.
        """
        if self._current.get() is not None:
            yield  # already inside one: the outermost commits
            return
        with self._scope(writable=True) as session:
            yield
            session.commit()

    @contextmanager
    def _scope(self, writable: bool) -> Iterator[Session]:
        """Open a session, make it this thread's (or task's) unit of work, and yield it.

        On any exception the session is rolled back and the error re-raised. Either way the session is closed
        and the unit of work cleared again. Committing is the caller's job (unit_of_work).
        """
        with self._session_factory() as session:
            token = self._current.set(_UnitOfWork(session, writable))
            try:
                yield session
            except BaseException:
                # BaseException, not Exception: even an interruption (Ctrl+C, a cancelled task) undoes the changes.
                session.rollback()
                raise
            finally:
                self._current.reset(token)

    def _handle(self, message: Message) -> Any:
        """Call the message's handler with a Context for the current unit of work, and return its result.

        Raises LookupError if no handler is registered for the message's exact type (for example, a module
        left out of bootstrap.MODULES).
        """
        handler = self._handlers.get(type(message))
        if handler is None:
            raise LookupError(f"No handler registered for {type(message).__name__}")
        current = self._current.get()
        assert current is not None  # every caller opens a scope first
        logger.debug("handling %s", type(message).__name__)
        return handler(Context(current.session, self, self._clock), message)
