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
M = TypeVar("M", bound="Message")


class Message(BaseModel):
    # Frozen: a message is a fact about what was asked, so nobody changes it on the way.
    # extra="forbid": a misspelt field is an error, not a silently ignored value.
    model_config = ConfigDict(frozen=True, extra="forbid")


class Command(Message, Generic[R]):
    """A request to change data. R is what it returns: None, or the new item's id."""


class Query(Message, Generic[R]):
    """A request for data, returning R. A query handler must not change anything."""


@dataclass(frozen=True)
class Context:
    """What a handler gets besides its message."""

    session: Session
    bus: "MessageBus"  # for asking other modules, inside the same transaction
    clock: Clock


@dataclass
class _UnitOfWork:
    session: Session
    writable: bool


class MessageBus:
    def __init__(self, session_factory: Callable[[], Session], clock: Clock) -> None:
        self._session_factory = session_factory
        self._clock = clock
        self._handlers: dict[type[Message], Callable[[Context, Any], Any]] = {}
        # The unit of work in progress in this thread (or task), if any. A ContextVar, not an attribute:
        # requests run in parallel threads, and each must only ever see its own session.
        self._current: ContextVar[_UnitOfWork | None] = ContextVar("unit_of_work", default=None)

    def register(self, message_type: type[M], handler: Callable[[Context, M], Any]) -> None:
        # Exactly one handler per message: a second registration is a wiring mistake, so fail loudly.
        if message_type in self._handlers:
            raise ValueError(f"{message_type.__name__} already has a handler")
        self._handlers[message_type] = handler

    def execute(self, command: Command[R]) -> R:
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
        if self._current.get() is not None:
            return self._handle(query)  # inside a unit of work: read through its session
        with self._scope(writable=False):
            return self._handle(query)

    @contextmanager
    def unit_of_work(self) -> Iterator[None]:
        """Run several commands as one transaction: all of them are saved, or none (e.g. the seed script)."""
        if self._current.get() is not None:
            yield  # already inside one: the outermost commits
            return
        with self._scope(writable=True) as session:
            yield
            session.commit()

    @contextmanager
    def _scope(self, writable: bool) -> Iterator[Session]:
        with self._session_factory() as session:
            token = self._current.set(_UnitOfWork(session, writable))
            try:
                yield session
            except BaseException:
                session.rollback()
                raise
            finally:
                self._current.reset(token)

    def _handle(self, message: Message) -> Any:
        handler = self._handlers.get(type(message))
        if handler is None:
            raise LookupError(f"No handler registered for {type(message).__name__}")
        current = self._current.get()
        assert current is not None  # every caller opens a scope first
        logger.debug("handling %s", type(message).__name__)
        return handler(Context(current.session, self, self._clock), message)
