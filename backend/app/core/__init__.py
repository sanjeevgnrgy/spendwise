"""Shared technical building blocks (config, database, money, LLM): the foundation every module stands on.

- config.py: settings from .env, and the fixed API_PREFIX, API_VERSION and MCP_PATH;
- cqrs.py: Command, Query, and the MessageBus that runs them (also the unit of work);
- db.py: database engines (SQLite made transactional), session factories, and the default engine;
- ids.py: the rules for record ids (RecordId, MAX_ID), apart from db.py so contracts don't load the database;
- errors.py: the expected errors handlers raise, and how the API reports them (RFC 9457 problem details);
- dependencies.py: FastAPI dependencies that give routes the bus and the clock (BusDep, ClockDep, IdPath);
- clock.py, months.py, money.py: today's date, calendar months, and rupees <-> paise;
- logging.py: console logging for our own loggers;
- llm/: the language-model port, provider-neutral messages, and the Gemini adapter (gemini.py for the SDK
  calls, gemini_wire.py for Gemini's wire format).

Core holds no business rules and never imports from app.modules, so every module
can depend on it without creating import cycles.
"""
