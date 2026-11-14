"""Shared building blocks (the bus, errors, values, the LLM port): the foundation every module stands on.

- cqrs.py: Command, Query, and the MessageBus that runs them (also the unit of work);
- errors.py: the expected errors handlers raise (NotFoundError, BusinessRuleError, ExternalServiceError);
- ids.py: the rules for record ids (RecordId, MAX_ID);
- clock.py, months.py, money.py: today's date, calendar months, and rupees <-> paise;
- llm/: the language-model port (port.py) and provider-neutral messages (messages.py).

Core does no I/O and imports no framework, no module, and neither infrastructure/ nor web/, so everything else can
depend on it without creating import cycles. What talks to the outside world (settings, the database, logging, the
Gemini adapter) is in infrastructure/; the FastAPI plumbing routes share (dependencies, problem responses) is in web/.
"""
