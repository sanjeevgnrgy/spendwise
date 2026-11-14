"""SpendWise backend: one FastAPI app split into business modules (a modular monolith).

Grouped by concern: core/ holds the shared building blocks (the bus, errors, values, the LLM port), modules/ the
business modules, and infrastructure/ what talks to the outside world (settings, database, migrations, logging,
Gemini). bootstrap.py is the composition root that wires them, and main.py the web app. Entry points (uvicorn,
seed.py, mcp_stdio.py, the migrations, the export script) import from here.
"""
