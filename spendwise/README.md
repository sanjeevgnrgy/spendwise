# SpendWise

An agentic expense tracker, built one small phase at a time as a learning project.

**Current state (Phase 2):** a FastAPI backend with `GET /health`, `GET /hello/{name}`, and
`POST /ask`, which sends a prompt to Gemini and returns its answer.

## Requirements

- Python 3.11 or newer (developed on 3.14)
- Commands below are for Windows PowerShell. macOS/Linux equivalents are noted where they differ.

## Quick start (Windows)

From the `spendwise/` folder:

```powershell
Copy-Item .env.example .env     # once, then paste your Gemini API key into .env
.\run.ps1
```

Get a Gemini API key at https://aistudio.google.com/apikey and put it after `GEMINI_API_KEY=` in `.env`.

`run.ps1` creates `.venv` on the first run, installs `requirements.txt` whenever that file has
changed, and starts the server. No activation is needed. Extra arguments are passed to uvicorn,
for example `.\run.ps1 --port 8001`.

If PowerShell refuses to run the script, allow local scripts once with
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then try again.

## Manual setup (any OS)

What `run.ps1` does, step by step. From the `spendwise/` folder:

```powershell
py -3 -m venv .venv                         # macOS/Linux: python3 -m venv .venv
.\.venv\Scripts\Activate.ps1                # macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
Copy-Item .env.example .env                 # macOS/Linux: cp .env.example .env
python -m uvicorn backend.main:app --reload
```

## Check it works

With the server running, open:

- http://127.0.0.1:8000/health → `{"status":"ok"}`
- http://127.0.0.1:8000/hello/Priya → `{"message":"Hello, Priya!"}`
- http://127.0.0.1:8000/docs → interactive API docs (Swagger UI)

To try Gemini, open `/docs`, expand **POST /ask**, click **Try it out**, send
`{"prompt": "Give me one tip to save money on groceries."}` and click **Execute**.
A working setup returns `200` with `{"answer": "..."}`. A missing key returns `500` (the
terminal says which setting is missing); a wrong key returns `502` with Google's error message.

`--reload` restarts the server whenever a file changes. Use it for development only.
Stop the server with `Ctrl+C`.

## Project layout

```
spendwise/
  backend/
    __init__.py      makes backend/ an importable package
    main.py          FastAPI app and routes
    llm.py           ask_gemini(): the one place that talks to Gemini
  run.ps1            one-command dev start (Windows)
  requirements.txt   pinned direct dependencies
  .env.example       names of the settings the app expects (no secret values)
  .env               your real settings and API key (git-ignored, you create it)
  .gitignore
  README.md
```

`mcp_server/`, `agents/`, `skills/`, `web/` and `tests/` are added in later phases.

## Conventions

### Virtual environment

- One venv per project, at `spendwise/.venv`. Never install project packages into the global Python.
- Activate it before working. Your prompt should start with `(.venv)`.
  To double-check, `python -c "import sys; print(sys.prefix)"` should print a path ending in `.venv`.
- Run tools as `python -m pip` and `python -m uvicorn` rather than bare `pip` / `uvicorn`.
  This guarantees the tool runs with the same Python that runs the app.
- `.venv` is never committed. It can be deleted and rebuilt from `requirements.txt` at any time.
- If you move or rename the project folder, delete `.venv` and create it again:
  a venv stores absolute paths and stops working when moved.
- In VS Code, run **Python: Select Interpreter** and choose `.venv`, so the editor and terminal use the same Python.

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
- When a phase adds a new setting, add its name to `.env.example` in the same commit.

### Generated files

- `__pycache__/` folders hold compiled bytecode that Python creates and refreshes automatically on import.
  They are git-ignored and safe to delete at any time; Python rebuilds them on the next run.
- Leave bytecode caching on (don't set `PYTHONDONTWRITEBYTECODE`). It only makes startup faster.

### What gets committed

| Commit | Never commit |
|---|---|
| Source code (`backend/`, ...) | `.venv/` |
| `requirements.txt` | `__pycache__/`, `*.pyc` |
| `.env.example` | `.env` |
| `.gitignore`, `README.md` | |

Before each commit, check that `git status` lists none of the files in the right-hand column.
