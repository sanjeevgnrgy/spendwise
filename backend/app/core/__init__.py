"""Shared technical building blocks (config, database, money, LLM).

Core holds no business rules and never imports from app.modules, so every module
can depend on it without creating import cycles.
"""
