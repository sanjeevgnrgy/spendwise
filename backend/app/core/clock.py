"""The current date and time, as a dependency instead of a global.

Code that asks `date.today()` directly can only ever see the real day, so "this month" can't be
pinned in a check, and every caller silently uses the server's time zone. Handlers get a Clock
instead; the app gives them the system clock, and anything else (a script, a check) can pass its own.

Core layer: bootstrap.build() picks the clock, the bus hands it to every handler (ctx.clock), and routes get it
through core/dependencies.ClockDep.
"""

from datetime import UTC, date, datetime
from typing import Protocol


class Clock(Protocol):
    """Where the app gets the date and time. Any object with these two methods will do.

    today() is the date that "this month" and default dates are based on; now() is a time-zone-aware moment,
    for timestamps such as an expense's created_at.
    """

    def today(self) -> date:
        """Today's date: what "this month" and default dates are based on."""
        ...

    def now(self) -> datetime:
        """The current moment, time-zone aware (UTC in the app): for timestamps such as created_at."""
        ...


class SystemClock:
    """The real clock, which the app uses unless bootstrap.build() is given another."""

    def today(self) -> date:
        """Today's date on the server."""
        # The server's local date. Per-user time zones need users first (the planned auth phase).
        return date.today()

    def now(self) -> datetime:
        """The current moment, in UTC."""
        # Always UTC for timestamps; showing them in local time is the client's job.
        return datetime.now(UTC)
