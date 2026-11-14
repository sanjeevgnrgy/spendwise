"""Adapters for the language-model port (core/llm): today, Google's Gemini (gemini.py, gemini_wire.py).

Infrastructure. The composition root (bootstrap.py) imports gemini.GeminiModel and injects it; nothing else
imports this package, so the rest of the app depends only on the port.
"""
