# Troubleshooting

Problems already hit while building SpendWise, and how to fix them. All commands are run from
the project folder (the repo root, where `run.ps1` is) unless noted.

## Running the app

### `./run.ps1 : The term './run.ps1' is not recognized...`
- **Cause:** the terminal isn't in the project folder (the one containing `run.ps1`).
- **Fix:** `cd` into the project folder, then `.\run.ps1`. Or call the script by its path from anywhere
  (it switches to its own folder). Check where you are with `Get-Location`.

### PowerShell refuses to run `run.ps1` or `Activate.ps1`
- **Cause:** the execution policy blocks local scripts.
- **Fix (once):** `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### `GET / 404 Not Found` and `GET /favicon.ico 404` in the server log
- **Cause:** there's no route at `/`. The browser also asks for a tab icon automatically.
- **Fix:** nothing is broken. Open `/health` or `/docs` instead.

### Port already in use
- **Cause:** another server (often an old SpendWise one) is still running on port 8000.
- **Fix:** stop it with Ctrl+C in its terminal, or start on another port: `.\run.ps1 --port 8001`.

### Changed `.env` but nothing changed
- **Cause:** settings are read once at startup, and auto-reload only watches `.py` files.
- **Fix:** stop the server (Ctrl+C) and run `.\run.ps1` again.

### The app stopped working after moving or renaming the project folder
- **Cause:** a venv stores absolute paths.
- **Fix:** delete `.venv` and run `.\run.ps1`, which recreates it.

### Can't delete or move `.venv` or `spendwise.db`: "Access is denied" / "being used by another process"
- **Cause:** a Python process still has the files open, usually the dev server. With `--reload`, uvicorn runs
  a separate worker process whose command line only mentions `multiprocessing`, so it's easy to miss, and it
  can keep running after its parent is killed.
- **Fix:** stop the server with Ctrl+C in its terminal. If files are still locked, list Python processes with
  `Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Select ProcessId, CommandLine` and stop the
  leftover one with `Stop-Process -Id <id>`.

## Gemini (`POST /ask`, `POST /parse`)

See the error table in [gemini.md](gemini.md#when-something-goes-wrong). In short: `500` means a setting
is missing (the terminal says which); `502` means Gemini refused or failed (bad key, quota, model not available
on your tier, or temporarily overloaded).

### `502` "... is currently experiencing high demand ... Please try again later."
- **Cause:** Google returned `503 Service Unavailable`: that model is overloaded right now. Not a problem in our code.
- **Fix:** wait a few minutes and retry, or set `GEMINI_MODEL=gemini-4-hydrogen` (also free tier) in `.env` and restart.

### `/ask`, `/parse` or `/chat` takes a very long time
- **Cause (fixed in Phase 6):** the SDK used to retry up to 5 times, up to 60 s apart, while Gemini was down.
- **Now:** each attempt gives up after 60 s and there are at most 2. If it still hangs much longer, check your network.

### `/chat` returns 502 "Request timed out. This is a client-side timeout."
- **Cause:** one Gemini step took longer than 60 s, usually because the model was "thinking" for a long time.
- **Fix:** already mitigated: the agent uses `thinking_level="low"` (`agent.THINKING_LEVEL`). If it keeps happening,
  Gemini may be slow right now; retry later, or try another model in `GEMINI_MODEL`.

### `/chat` replies "Sorry, that took too many steps"
- **Cause:** Gemini kept calling tools without answering, and the loop stopped at `MAX_STEPS = 5`.
- **Fix:** look at the console log to see which tools it called, and why it got stuck. Rephrase more specifically
  (e.g. give the expense's merchant and date).

### `/chat` forgot what I just said ("yes" doesn't confirm a delete)
- **Cause:** the follow-up was sent without a `thread_id`, so it started a new conversation.
- **Fix:** copy `thread_id` from the previous reply and send it with the next message:
  `{"message": "yes, delete it", "thread_id": "<from the last reply>"}`.

### `/chat` or `GET /threads` returns 404 "Thread ... not found"
- **Cause:** that `thread_id` doesn't exist. It may be mistyped, or it may come from a database you've since deleted
  (e.g. when re-seeding).
- **Fix:** check the id, or leave `thread_id` out to start a new conversation.

### The assistant forgot something from much earlier in a long thread
- **Cause:** only the last 10 turns are sent (`MAX_HISTORY_TURNS` in `modules/assistant/service.py`), to keep cost down.
  Older turns are still stored (`GET /threads/{id}`), but the model doesn't see them.
- **Fix:** repeat the detail, or start a new thread for a new topic.

### `/parse` returns 422 "There are no categories yet"
- **Fix:** run `.\.venv\Scripts\python.exe backend\seed.py`. Parsing needs the category list to choose from.

## Web app

### Red toast "Can't reach the SpendWise API at http://localhost:8000"
- **Cause:** the backend isn't running, runs on another port, or the browser blocked the response (CORS).
- **Fix:** start it with `.\run.ps1`. On another port, set `VITE_API_URL` in `web/.env` and restart `npm run dev`.
  If the backend *is* running, check the browser console for a CORS error (next entry).

### Browser console: "blocked by CORS policy: No 'Access-Control-Allow-Origin' header"
- **Cause:** the page's address isn't in the backend's allowed origins (default `http://localhost:5173` and
  `http://127.0.0.1:5173`). Common when Vite picks another port because 5173 is busy (it prints the URL it uses).
- **Fix:** open the app at `http://localhost:5173`, or add its address to `CORS_ORIGINS` in `.env`
  (a JSON list) and restart the backend.

### Blank page; console says "Maximum update depth exceeded"
- **Cause:** a component keeps setting state in a loop, usually a `useEffect` that sets state and lists a value
  that's new on every render (an object or function created during render, or `useTable`'s `table`).
  The Expenses table had exactly this bug at first (decisions D88).
- **Fix:** find the effect in the component named in the console. Remove the unstable dependency, or compute the
  value during render instead of in an effect.

### Console: "Encountered a script tag while rendering React component"
- **Cause:** a component rendered a `<script>` (e.g. `next-themes`), which never runs in a browser-rendered React app.
- **Fix:** already removed from SpendWise (decisions D87). Put scripts in `index.html` instead.

### Dashboard shows "Couldn't load the dashboard"
- **Cause:** one of its four requests failed, most often because the backend isn't running.
- **Fix:** start the backend (`.\run.ps1`) and click **Try again**. The message under the title is the actual error.

### Dashboard charts say "No spending…" but I have expenses
- **Cause:** the charts show the **current** month and the last 6 months, in **INR** only. Expenses dated outside
  that window, or in another currency, aren't included.
- **Fix:** check the expense dates (the seed script dates its samples relative to the day it ran).

### `npm run dev`: "Cannot find module" or a blank page after pulling changes
- **Cause:** `package.json` changed but `node_modules` wasn't updated.
- **Fix:** run `npm install` in `web/`, then `npm run dev` again.

### A shadcn component looks wrong, or I want to change it
- shadcn/ui components are source files in `web/src/components/ui/`. Edit them like any other file.
  `npx shadcn@latest add <name>` adds new ones; re-adding an existing one asks before overwriting.

## MCP

### `No module named 'mcp.server.fastmcp'` / tutorials say `FastMCP`
- **Cause:** MCP SDK 2.x renamed `FastMCP` to `MCPServer`.
- **Fix:** `from mcp.server.mcpserver import MCPServer`, as `modules/mcp/server.py` does.

### An MCP client can't connect to `http://127.0.0.1:8000/mcp`
- **Cause:** the endpoint is `/mcp/` (with a trailing slash); `/mcp` answers with a 307 redirect that some clients don't follow.
- **Fix:** use `http://127.0.0.1:8000/mcp/`, with the app running (`.\run.ps1`).

### A tool call returns only "Error executing tool <name>"
- **Cause:** an *unexpected* exception; the SDK hides its text from clients on purpose.
- **Fix:** read the traceback in the server's terminal (for stdio, the host's server log). Expected problems, like an
  unknown category, come with a clear message instead.

### `/chat` replies "Sorry, I can't reach the expense tools right now"
- **Cause:** the assistant couldn't connect to the MCP server at `MCP_URL` (default `http://localhost:8000/mcp`).
  Most often the app is running on a different port, e.g. `.\run.ps1 --port 8001`.
- **Fix:** set `MCP_URL=http://localhost:<port>/mcp` in `.env` and restart. The terminal logs the URL it tried.

### `/chat` doesn't see a tool I just added to the MCP server
- **Cause:** the assistant lists the tools once, on the first chat, and caches them.
- **Fix:** restart the app.

### `mcp dev` fails: "npx not found" or `uv` not found
- **Cause:** the Inspector needs Node.js (`npx`), and `mcp dev` starts the server through `uv`.
- **Fix:** install Node.js and uv, or run the Inspector directly:
  `npx @modelcontextprotocol/inspector .\.venv\Scripts\python.exe backend\mcp_stdio.py`.

### The stdio server starts, then the client reports garbage or disconnects
- **Cause:** something printed to stdout, which carries the protocol messages.
- **Fix:** never `print()` in code the stdio server runs; use logging (it goes to stderr).

## Database

### I want fresh sample data
1. Stop the server.
2. Delete `backend\spendwise.db`.
3. Start the server (it recreates empty tables).
4. Run `.\.venv\Scripts\python.exe backend\seed.py`.

### I changed a model's fields, but the database didn't change
- **Cause:** tables are created with `create_all`, which never alters existing tables (no migrations yet,
  see [decisions.md](decisions.md) D18).
- **Fix:** delete `backend\spendwise.db` and re-seed, as above.

### Seed says "Already seeded; nothing to do"
- **Cause:** categories already exist, and the seed refuses to duplicate them.
- **Fix:** that's expected. Delete the database first if you want to start over.

## VS Code

### `Import "fastapi" could not be resolved` (or `app.…` imports)
- **Cause:** VS Code's checker (Pylance) is using a Python interpreter that isn't the project's venv,
  or doesn't know the `app` package lives in `backend/`.
- **Fix:** `.vscode/settings.json` sets both. If you chose another interpreter by hand, run
  **Python: Select Interpreter** and pick `.venv\Scripts\python.exe` in the project folder, then
  **Python: Restart Language Server**.

### Errors about files that no longer exist (e.g. old `tsconfig.json`)
- **Cause:** the editor's language servers still hold the old files in memory.
- **Fix:** close tabs from deleted files without saving, then run **Developer: Reload Window**.

## Git

### `warning: LF will be replaced by CRLF`
- **Cause:** Git for Windows converts line endings automatically.
- **Fix:** nothing to do; it's harmless.
