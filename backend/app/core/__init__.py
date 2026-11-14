"""Shared building blocks (the bus, errors, values, the LLM port): the foundation every module stands on.

- cqrs.py: Command, Query, and the MessageBus that runs them (also the unit of work);
- ids.py: the rules for record ids (RecordId, MAX_ID);
- errors.py: the expected errors handlers raise, and how the API reports them (RFC 9457 problem details);
- dependencies.py: FastAPI dependencies that give routes the bus and the clock (BusDep, ClockDep, IdPath);
- clock.py, months.py, money.py: today's date, calendar months, and rupees <-> paise;
- llm/: the language-model port (port.py) and provider-neutral messages (messages.py).

Core holds no business rules and imports no module and nothing from infrastructure/, so everything else can depend
on it without creating import cycles. What talks to the outside world (settings, the database, logging, the Gemini
adapter) is in infrastructure/.
"""
