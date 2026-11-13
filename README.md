# SpendWise

An agentic expense tracker, built one small phase at a time as a learning project.

**Current state (Phase 5):** a modular-monolith FastAPI backend with a REST API for expenses
(create, list with filters, read, update, delete), a monthly summary, a categories list, and
`POST /ask` (sends a prompt to Gemini). `backend/seed.py` fills the database with sample data.
A pytest suite covers the API, the business rules and the module boundaries.

## Requirements

- Python 3.11 or newer (developed on 3.14)
- Commands below are for Windows PowerShell. macOS/Linux equivalents are noted where they differ.

## Quick start (Windows)

From the project folder (the repo root, where `run.ps1` is):

```powershell
Copy-Item .env.example .env     # once, then paste your Gemini API key into .env
.\run.ps1                       # creates .venv, installs requirements, starts the server
```

In a second terminal, add sample data (safe to run more than once):

```powershell
.\.venv\Scripts\python.exe backend\seed.py
```

`run.ps1` creates `.venv` on the first run, installs `requirements.txt` whenever that file has
changed, and starts the server with auto-reload. No activation is needed. Extra arguments are
passed to uvicorn, for example `.\run.ps1 --port 8001`.

Get a Gemini API key at https://aistudio.google.com/apikey and put it after `GEMINI_API_KEY=` in `.env`.
If PowerShell refuses to run the script, allow local scripts once with
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then try again.

## Manual setup (any OS)

What `run.ps1` does, step by step. From the project folder:

```powershell
py -3 -m venv .venv                         # macOS/Linux: python3 -m venv .venv
.\.venv\Scripts\Activate.ps1                # macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
Copy-Item .env.example .env                 # macOS/Linux: cp .env.example .env
python -m uvicorn app.main:app --app-dir backend --reload --reload-dir backend
python backend/seed.py                      # in a second terminal
```

`--app-dir backend` is needed because the code imports itself as `app.…`, and the `app`
package lives inside `backend/`.

## Check it works

With the server running:

- http://127.0.0.1:8000/health → `{"status":"ok"}`
- http://127.0.0.1:8000/docs → interactive API docs (Swagger UI): try every route from here
- http://127.0.0.1:8000/categories → the 8 categories
- http://127.0.0.1:8000/expenses?search=grocer → expenses whose merchant or note contains "grocer"
- http://127.0.0.1:8000/summary?month=2026-11 → that month's total and per-category totals

The full route list, filters, status codes and example requests are in
[docs/phases/phase-4-expenses-api.md](docs/phases/phase-4-expenses-api.md).

To try Gemini, open `/docs`, expand **POST /ask**, click **Try it out**, send
`{"prompt": "Give me one tip to save money on groceries."}` and click **Execute**.
A working setup returns `200` with `{"answer": "..."}`. A missing key returns `500` (the
terminal says which setting is missing); a wrong key returns `502` with Google's error message.

The seed script prints the 10 sample expenses it saved, each in rupees and in paise.
The database is the file `backend/spendwise.db`; delete it to start from an empty database.

## Run the tests

From the project folder:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt   # once, and when it changes
.\.venv\Scripts\python.exe -m pytest                                # expect: 38 passed
```

Tests use a fresh in-memory database each, never `backend/spendwise.db` or your Gemini key.
How to run a subset and read a failure: [docs/phases/phase-5-tests.md](docs/phases/phase-5-tests.md).

## Architecture: modular monolith

One FastAPI app, one deployable, one database, split inside into **modules by business
domain** (expenses, categories, assistant, ...). A module talks to another only through that
module's public interface (`modules/<name>/__init__.py`) and never touches its tables.
Full rules, request flow and how to add a module: [docs/architecture.md](docs/architecture.md).

## Documentation

[docs/](docs/README.md) has the learning notes for each phase, the decision log, Gemini setup
and free-tier notes, and troubleshooting.

## Project layout

```
spendwise/
  backend/
    app/
      main.py              composition root: creates the app, includes module routers
      core/
        config.py          settings from .env (pydantic-settings)
        db.py              database engine, table creation, get_session / SessionDep
        errors.py          NotFoundError -> 404, BusinessRuleError -> 422
        money.py           rupees <-> paise helpers
        llm.py             ask_gemini(): the one place that talks to Gemini
      modules/
        assistant/         POST /ask (router, schemas, service)
        categories/        Category table, GET /categories, public interface
        expenses/          Expense table, CRUD routes, GET /summary, public interface
    seed.py                default categories and sample expenses
    spendwise.db           local SQLite database (git-ignored, created automatically)
    tests/                 pytest: conftest.py fixtures, one folder per module, architecture/
  run.ps1                  one-command dev start (Windows)
  requirements.txt         pinned direct dependencies
  requirements-dev.txt     requirements.txt + test tools (pytest, httpx)
  pytest.ini               where tests live; puts backend/ on the import path
  .env.example             names of the settings the app expects (no secret values)
  .env                     your real settings and API key (git-ignored, you create it)
  docs/                    learning notes, decisions, Gemini notes, troubleshooting
  README.md
```

## Conventions

### Virtual environment

- One venv per project, in `.venv` in the project folder. Never install project packages into the global Python.
- Activate it before working. Your prompt should start with `(.venv)`.
  To double-check, `python -c "import sys; print(sys.prefix)"` should print a path ending in `.venv`.
- Run tools as `python -m pip` and `python -m uvicorn` rather than bare `pip` / `uvicorn`.
  This guarantees the tool runs with the same Python that runs the app.
- `.venv` is never committed. It can be deleted and rebuilt from `requirements.txt` at any time.
- If you move or rename the project folder, delete `.venv` and create it again:
  a venv stores absolute paths and stops working when moved.
- In VS Code, the repo's `.vscode/settings.json` already points at `.venv`.

### Dependencies

- `requirements.txt` lists direct dependencies only, pinned to exact versions (`package==x.y.z`),
  so every machine installs the same thing.
- Tools needed only while developing (pytest) go in `requirements-dev.txt`, which includes `requirements.txt`.
- To add a dependency:
  1. With the venv active, run `python -m pip install <package>`.
  2. Run `python -m pip show <package>` to read the installed version.
  3. Add `<package>==<version>` to `requirements.txt`.
  4. Commit `requirements.txt` in the same commit as the code that uses the package.
- Upgrade deliberately: change the pin, reinstall, test again, then commit.

### Configuration and secrets

- Secrets and machine-specific settings (API keys, database URLs) live in `.env`, never in code.
- `.env` is git-ignored. `.env.example` is committed and lists every setting name with no real values.
- All settings are read in one place, `backend/app/core/config.py`. Real environment variables
  override values in `.env`.
- When a phase adds a new setting, add its name to `.env.example` in the same commit.

### Money

- Amounts are stored as whole **paise** (integer minor units) plus a currency code, default `INR`:
  450.50 rupees is stored as `45050`.
- Convert only with `app.core.money` (`rupees_to_paise`, `paise_to_rupees`), which use `Decimal`.
  Never put money through a `float`.

### Generated files

- `__pycache__/` folders hold compiled bytecode that Python creates and refreshes automatically on import.
  They are git-ignored and safe to delete at any time; Python rebuilds them on the next run.
- `backend/spendwise.db` is your local data. It's git-ignored and recreated (empty) when the server starts.

### What gets committed

| Commit | Never commit |
|---|---|
| Source code (`backend/`, ...) | `.venv/` |
| `requirements.txt`, `requirements-dev.txt`, `pytest.ini` | `__pycache__/`, `*.pyc`, `.pytest_cache/` |
| `.env.example` | `.env` |
| `.gitignore`, `README.md`, `docs/`, `run.ps1` | `*.db` (your local database) |

Before each commit, check that `git status` lists none of the files in the right-hand column.
Update `docs/` in the same commit as the code it describes (see [docs/README.md](docs/README.md)).
