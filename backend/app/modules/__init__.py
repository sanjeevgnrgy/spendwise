"""Business modules, one per domain: categories, expenses, conversations, assistant, and the mcp adapter.

Each one owns its tables and exposes its contract in its own __init__.py; other code imports only that
(`from app.modules import expenses`). The composition root (bootstrap.py) plugs each one in through its
module.py. This package itself exports nothing.
"""
