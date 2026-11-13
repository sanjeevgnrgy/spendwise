# SpendWise

An agentic expense tracker, built one small phase at a time as a learning project.

**Current state (Phase 14):** a React web app (`web/`) with a sidebar layout, light/dark theme, a
Dashboard (this month's total, category and 6-month trend charts, recent expenses), an
Expenses page (sortable table, filters, add/edit/delete) and an Assistant chat panel on every page
that shows the agent's reply as it's written and refreshes the page when it changes data, on top of a modular-monolith FastAPI
backend with a REST API for expenses
(create, list with filters, read, update, delete), a monthly summary, a categories list,
`POST /ask` (sends a prompt to Gemini), `POST /parse` (turns a note like "Paid 450 at Swiggy
yesterday" into a structured expense, without saving it), `POST /chat` (a Gemini agent that
adds, finds, summarises, updates and deletes expenses through tools, and remembers the conversation
per `thread_id`; see it with `GET /threads/{id}`) and `POST /agent` (the same agent, streaming its reply as
AG-UI events over Server-Sent Events; the chat panel uses this one). The same expense tools are also exposed to any MCP client (MCP Inspector, Claude
Desktop) by an MCP server at `/mcp/` and over stdio. `backend/seed.py` fills the database with sample
data.

## Requirements

- Python 3.11 or newer (developed on 3.14)
- Node.js 20 or newer, for the web app (developed on 24)
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

**The web app**, in another terminal, with the backend running:

```powershell
cd web
npm install      # first time, and after package.json changes
npm run dev      # then open http://localhost:5173
```

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
- http://127.0.0.1:8000/summary/trend?months=6 → totals for each of the last 6 months (the Dashboard's line chart)
- `POST /parse` in `/docs` with `{"text": "Paid 450.50 at Swiggy yesterday via GPay"}` → the parsed expense
  and `missing_fields` (needs your Gemini key; nothing is saved)
- `POST /chat` in `/docs` with `{"message": "How much did I spend on food this month?"}` → a reply plus the
  tools the agent called; watch the server terminal to see each step (needs your Gemini key; `/chat` can change data).
  Send the reply's `thread_id` with your next message to continue the same conversation, and view it with
  `GET /threads/{thread_id}`
- `POST /agent` streams the same agent's reply as AG-UI events; watch it arrive with `curl.exe -N` as shown in
  [docs/phases/phase-14-agui-streaming.md](docs/phases/phase-14-agui-streaming.md#test-it-by-hand)

The full route list, filters, status codes and example requests are in
[docs/phases/phase-4-expenses-api.md](docs/phases/phase-4-expenses-api.md).

To try Gemini, open `/docs`, expand **POST /ask**, click **Try it out**, send
`{"prompt": "Give me one tip to save money on groceries."}` and click **Execute**.
A working setup returns `200` with `{"answer": "..."}`. A missing key returns `500` (the
terminal says which setting is missing); a wrong key returns `502` with Google's error message.

The seed script prints the 10 sample expenses it saved, each in rupees and in paise.
The database is the file `backend/spendwise.db`; delete it to start from an empty database.

## MCP server

With the app running, MCP clients can connect to `http://127.0.0.1:8000/mcp/` (Streamable HTTP; keep the
trailing slash). To explore it by hand in the MCP Inspector, over stdio (needs Node.js and uv):

```powershell
.\.venv\Scripts\mcp.exe dev backend\mcp_stdio.py
```

The assistant behind `POST /chat` and `POST /agent` uses this same server: it connects to `MCP_URL` (default
`http://localhost:8000/mcp`) to find and run its tools. If you start the app on another port, set
`MCP_URL` in `.env` to match.

Tools: `add_expense`, `list_expenses`, `get_summary`, `update_expense`, `delete_expense`. Resources:
`expenses://categories`, `expenses://recent`. Inspector steps and Claude Desktop setup:
[docs/phases/phase-9-mcp-module.md](docs/phases/phase-9-mcp-module.md).

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
        errors.py          NotFoundError -> 404, BusinessRuleError -> 422, ExternalServiceError -> 502
        logging.py         console logging for SpendWise's own messages
        money.py           rupees <-> paise helpers
        llm.py             the one place that talks to Gemini (plain, structured output, streamed tool steps)
      modules/
        assistant/         POST /ask, /parse, /chat, /agent (AG-UI stream), GET /threads; ChatMessage table (+ parse, agent, mcp_client)
        mcp/               MCP server: expense tools and resources for any MCP client, mounted at /mcp/
        categories/        Category table, GET /categories, public interface
        expenses/          Expense table, CRUD routes, GET /summary, public interface
    seed.py                default categories and sample expenses
    mcp_stdio.py           runs the MCP server over stdio (MCP Inspector, Claude Desktop)
    spendwise.db           local SQLite database (git-ignored, created automatically)
  web/                     React frontend (see web/README.md)
    src/api.ts             every call to the backend
    src/pages/expenses/    the Expenses page: table, filters, add dialog, inline edit
    src/pages/dashboard/   the Dashboard: cards, charts, recent expenses
    src/components/chat/   the Assistant chat panel (state in src/hooks/use-chat.ts)
    src/components/ui/     shadcn/ui components (copied source, editable)
  run.ps1                  one-command dev start (Windows)
  requirements.txt         pinned direct dependencies
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
| `requirements.txt` | `__pycache__/`, `*.pyc` |
| `.env.example` | `.env` |
| `.gitignore`, `README.md`, `docs/`, `run.ps1` | `*.db` (your local database) |

Before each commit, check that `git status` lists none of the files in the right-hand column.
Update `docs/` in the same commit as the code it describes (see [docs/README.md](docs/README.md)).
