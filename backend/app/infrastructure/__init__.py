"""Infrastructure: the code that talks to something outside the process (settings, database, logs, the model).

- config.py: settings from .env, and the fixed API_PREFIX, API_VERSION and MCP_PATH;
- db.py: database engines (SQLite made transactional), session factories, and the default engine;
- migrations.py: run or check the Alembic migrations from code;
- logging.py: console logging for our own loggers;
- llm/: adapters for the core/llm port (gemini.py for the SDK calls, gemini_wire.py for Gemini's wire format).

It may import core/, never a module, web/ or the composition root. Only the composition root (bootstrap.py) and
the entry points (main.py, seed.py, mcp_stdio.py, the migrations' env.py, the export script) import it: business
modules get what it builds (the bus's sessions, the model) passed in, so they never depend on it.
"""
