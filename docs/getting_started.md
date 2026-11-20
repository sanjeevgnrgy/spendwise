# Getting Started

From an empty machine to the app running with sample data. Commands are for Windows PowerShell; macOS/Linux
equivalents are noted where they differ.

## 1. Prerequisites

| Tool | Version | Check | Get it |
|---|---|---|---|
| Python | 3.11 or newer (developed on 3.14) | `py -3 --version` | https://www.python.org/downloads/ |
| Node.js | 20 or newer (developed on 24) | `node --version` | https://nodejs.org/ |
| Git | any recent | `git --version` | https://git-scm.com/ |
| A Gemini API key | free tier is enough | | https://aistudio.google.com/apikey (only for the assistant) |

Optional: **uv** (for `mcp dev`, the MCP Inspector launcher).

## 2. Get the code and your settings

```powershell
git clone https://github.com/sanjeevgnrgy/spendwise.git
cd spendwise
Copy-Item .env.example .env       # macOS/Linux: cp .env.example .env
```

Open `.env` and set at least:

```ini
GEMINI_API_KEY=<your key>
GEMINI_MODEL=gemini-3.5-flash-lite
OIDC_ISSUER=<your identity provider>
OIDC_CLIENT_ID=<the client id>
OIDC_CLIENT_SECRET=<the client secret>
SESSION_ENCRYPTION_KEYS=["<a Fernet key>"]
```

The `OIDC_*` settings and the key are for signing in (Phase 22): set up the provider first with
[identity_provider.md](identity_provider.md). Without them the app starts, but nobody can sign in and every API
route answers 401.

`.env` is git-ignored: your secrets never get committed. Every other setting has a working default; see
[configuration.md](configuration.md).

## 3. Start the backend

```powershell
.\run.ps1
```

What it does, in order:

1. **Creates `.venv`** the first time (`py -3 -m venv .venv`).
2. **Installs `requirements.txt`** whenever that file changed since the last install.
3. **Runs the database migrations** (`alembic upgrade head`): creates `backend\spendwise.db` and its tables the first
   time, and brings an existing database up to date later. Your data is kept.
4. **Starts the server** with auto-reload on http://127.0.0.1:8000.

Extra arguments go to uvicorn, e.g. `.\run.ps1 --port 8001`. If PowerShell refuses to run the script, allow local
scripts once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

**The receipt agent** (Phase 24) reads receipts attached in the chat. It's a separate service: put a
`RECEIPT_AGENT_KEY` in `.env` (any random 32+ characters, e.g. from
`python -c "import secrets; print(secrets.token_urlsafe(32))"`), then start it in a second terminal with
`.\run-receipt-agent.ps1` (http://127.0.0.1:9001). Everything else works without it.

### The same, by hand (any OS)

```powershell
py -3 -m venv .venv                                   # macOS/Linux: python3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --app-dir backend --reload --reload-dir backend
```

(On macOS/Linux the venv's Python is `.venv/bin/python`.) `--app-dir backend` is needed because the code imports
itself as `app.…`, and the `app` package lives inside `backend/`.

## 4. Add sample data (optional)

In a second terminal:

```powershell
.\.venv\Scripts\python.exe backend\seed.py
```

It creates 8 categories (Food, Transport, Shopping, Bills, Entertainment, Health, Travel, Other) and 10 expenses dated
over the last three weeks, all in one transaction. Run it again and it says "Already seeded; nothing to do."

## 5. Start the web app

```powershell
cd web
npm install        # first time, and after package.json changes
npm run dev        # http://localhost:5173
```

The web app calls the API on its own address, and the dev server forwards those calls to the backend on
http://127.0.0.1:8000 (one origin, D184). If the backend runs elsewhere, create `web\.env` with
`API_PROXY_TARGET=http://127.0.0.1:8001`. The web app itself can run on any port.

## 6. Check it works

| Try | Expect |
|---|---|
| http://127.0.0.1:8000/health | `{"status":"ok"}` (needs no sign-in) |
| http://127.0.0.1:8000/docs | Swagger UI with every route under `/api/v1` |
| http://localhost:5173 | the sign-in page; after signing in at the provider, the Dashboard with numbers and charts |
| Assistant panel: *"Where did my money go this month?"* | a short reply and an insight card |

Opening an API route such as `/api/v1/categories` in the browser's address bar now answers 403: a page's own calls
carry the `X-CSRF` header, an address typed by hand doesn't (D186). To call the API from a script, see
[api_endpoints.md](api_endpoints.md#calling-the-api-from-a-script).

## 7. Connect an MCP client (optional)

**Over stdio** (the client starts the server itself; no web server needed):

```powershell
npx @modelcontextprotocol/inspector .\.venv\Scripts\python.exe backend\mcp_stdio.py
# or, with uv installed:
.\.venv\Scripts\mcp.exe dev backend\mcp_stdio.py
```

Claude Desktop setup: [phases/phase-9-mcp-module.md](phases/phase-9-mcp-module.md).

Every MCP connection acts for one person, with a **personal access token** made on the Settings page (D191). For
stdio, give it to the server in the environment: `$env:SPENDWISE_TOKEN = "spw_..."` before the commands above, or
`"env": {"SPENDWISE_TOKEN": "spw_..."}` in Claude Desktop's config.

**Over HTTP**, connect to `http://127.0.0.1:8000/mcp/` with the header `Authorization: Bearer <token>`. The assistant
needs neither: it calls the MCP server in-process, for whoever is signed in.

## Everyday tasks

| Task | How |
|---|---|
| Stop the server | `Ctrl+C` in its terminal |
| Start from an empty database | stop the server, delete `backend\spendwise.db`, run `seed.py` (it migrates first) |
| After pulling new code | `.\run.ps1` (installs changed requirements, runs new migrations); `npm install` in `web/` |
| After changing a backend API | `.\.venv\Scripts\python.exe backend\scripts\export_contracts.py`, then `npm run gen:api` in `web/` |
| Change a table | edit its `persistence/tables.py`, then generate and run a migration ([backend_onboarding.md](backend_onboarding.md#recipe-add-or-change-a-table)) |
| Type-check, lint and build the web app | `npm run build` and `npx oxlint` in `web/` |
| Something's wrong | [troubleshooting.md](troubleshooting.md) |
