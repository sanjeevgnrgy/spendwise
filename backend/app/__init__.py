"""SpendWise backend: one FastAPI app split into business modules (a modular monolith).

core/ is the shared technical foundation, modules/ the business modules, bootstrap.py the composition root
that wires them, main.py the web app, and migrations.py runs the database migrations. Entry points (uvicorn,
seed.py, mcp_stdio.py, the migrations, the export script) import from here.
"""
