# Troubleshooting

Problems already hit while building SpendWise, and how to fix them. All commands are run from
the project folder (the repo root, where `run.ps1` is) unless noted.

## Running the app

### The backend stopped answering after pulling changes ("the database isn't at the latest migration")
- **Cause:** the code expects a newer database than yours (a new migration, e.g. 0005 for receipts). The app
  refuses to start rather than run on the wrong tables; with `--reload`, the reloaded app stops at that check while
  the reloader keeps the port, so requests hang or fail instead of reaching an error page.
- **Fix:** stop `run.ps1` (Ctrl+C) and start it again: it runs `alembic upgrade head` first.

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

### Every request stays "(pending)" after I changed backend code
- **Cause:** with `--reload` (which `run.ps1` uses), a code change starts a reload that first waits for every open request
  to finish, with no time limit. Until then the old server answers nothing new, not even `/health`. One request that never
  finishes (like the 429 sleep below, before D108) blocks the reload, and with it the whole server.
- **Fix:** Ctrl+C in the `run.ps1` terminal (press it again if it doesn't stop), then `.\run.ps1`.

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

## Gemini (`/parse`, `/chat`, the assistant)

See the error table in [gemini.md](gemini.md#when-something-goes-wrong). In short: `500` means a setting
is missing (the terminal says which); `502` means Gemini refused or failed (bad key, quota, model not available
on your tier, or temporarily overloaded). The app only says the service didn't answer properly; Google's own message
is in the backend terminal (D180).

### Server log: "... is currently experiencing high demand ... Please try again later." (a `502`)
- **Cause:** Google returned `503 Service Unavailable`: that model is overloaded right now. Not a problem in our code.
- **Fix:** wait a few minutes and retry, or set `GEMINI_MODEL=gemini-4-hydrogen` (also free tier) in `.env` and restart.

### The assistant shows "Thinking…" forever / `/chat` never answers
- **Cause (fixed in Phase 14, D108):** the free-tier quota was used up, so Gemini answered **429**, and the SDK quietly
  slept for as long as Google asked before retrying, with no upper limit. Nothing reported an error.
- **Now:** the reply is a red bubble (or a `502` from `/chat`) saying the service didn't answer properly; the backend
  terminal logs "Error code: 429 ... RESOURCE_EXHAUSTED" with Google's quota message.
- **Fix:** wait for the quota to reset (per-minute limits clear within a minute; daily limits reset at midnight Pacific, see
  [gemini.md](gemini.md)), or set another free-tier model in `GEMINI_MODEL` and restart. Every agent step is one Gemini
  request, so a single chat message can use 2–5 of them.

### `/parse` or `/chat` takes a very long time
- **Cause (fixed in Phase 6):** the SDK used to retry up to 5 times, up to 60 s apart, while Gemini was down.
- **Now:** each attempt gives up after 60 s and there are at most 2. If it still hangs much longer, check your network.

### `/chat` returns 502; the server log says "Request timed out. This is a client-side timeout."
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
- **Cause:** only the last 10 turns are sent (`MAX_HISTORY_TURNS` in `modules/assistant/application/assistant.py`),
  to keep cost down. Older turns are still stored (`GET /threads/{id}`), but the model doesn't see them.
- **Fix:** repeat the detail, or start a new thread for a new topic.

### `/parse` returns 422 "There are no categories yet"
- **Fix:** run `.\.venv\Scripts\python.exe backend\seed.py`. Parsing needs the category list to choose from.

## Receipts (`/receipts`)

### Upload returns 422 "Only photos (JPEG, PNG or WEBP) and PDF files can be read as receipts."
- **Cause:** the file's first bytes aren't a JPEG, PNG, WEBP or PDF, whatever its name says. Most often an iPhone
  photo in HEIC format, renamed or sent unconverted.
- **Fix:** export or share it as JPEG (on the iPhone: Settings → Camera → Formats → Most Compatible), or take a
  screenshot of it. HEIC isn't accepted yet (D181).

### Upload returns 422 "The file is larger than 5 MB."
- **Fix:** a phone's "medium" or "large" size instead of the original, or a single-page PDF. The limit is
  `MAX_RECEIPT_MB` in `receipts/values.py`.

### Extraction returns 404 "The file for receipt … is missing. Upload it again."
- **Cause:** the row exists, but its file isn't in `UPLOADS_DIR`: the folder was emptied or moved, or the database
  was copied without it (they go together). The server log names the missing key.
- **Fix:** upload the receipt again; or point `UPLOADS_DIR` back at the folder that has the files.

### Extraction returns 502 "The receipt couldn't be read."
- **Cause:** Gemini answered, but not in the shape asked for. The server log has a WARNING line ("didn't match
  ReceiptExtraction"); Pydantic's explanation is logged only at DEBUG, as it quotes the receipt.
- **Fix:** try again; if it repeats with the same receipt, try a sharper photo. Other 502s are Gemini failing: see
  the Gemini section above.

### Extraction answers, but with `null`s
- **Cause:** a field the receipt doesn't show (or that's unreadable) is `null` on purpose, never guessed. So is a value
  that can't be right: a category that isn't one of yours, a currency that isn't a three-letter code, a total that
  isn't positive.
- **Fix:** nothing is wrong; the person fills the gaps when confirming (Part 2's form). A blurred or cropped photo
  gives more `null`s.

### Chat: attaching a receipt shows a toast "… can't be read as a receipt" or "… is larger than 5 MB"
- **Cause:** the browser checks the file before uploading it: a photo (JPEG, PNG, WEBP) or a PDF, at most 5 MB.
  An iPhone photo may be HEIC (see "Upload returns 422 …" above).
- **Fix:** attach a JPEG or PDF of the receipt instead.

### Chat: the receipt's form has empty fields, or a wrong category
- **Cause:** whatever the receipt doesn't show clearly is left empty rather than guessed, and the category is only
  a suggestion from your list.
- **Fix:** fill in or change the fields, then press Save: nothing is saved before that.

## Web app

### Red toast "Can't reach SpendWise right now"
- **Cause:** the backend isn't running, runs on another port, or the browser blocked the response (CORS). The toast
  doesn't name the address (D180); the failed request in the browser's Network tab does.
- **Fix:** start it with `.\run.ps1`. On another port, set `VITE_API_URL` in `web/.env` and restart `npm run dev`.
  If the backend *is* running, check the browser console for a CORS error (next entry).

### A page or the app says "Something went wrong. Try again; if it keeps happening, reload the page."
- **Cause:** something in the browser crashed while drawing (a bug, not a server error). Its message is for developers,
  so it's not shown (D180); the browser console has it, with the stack. While developing, a common cause is a tab left
  open while files changed under the running `npm run dev`: the tab can end up mixing new code with an old module
  (for example "Cannot read properties of undefined (reading 'upi')" right after the generated contract changed).
- **Fix:** reload the page. If it comes back after a reload, read the console's error and fix the code.

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

### Assistant panel: the reply bubble is red
- **Cause:** the run (`POST /agent`) failed. The text says what failed: the backend isn't running ("Can't reach SpendWise
  right now"), or Gemini failed ("The assistant's service didn't answer properly", a `RUN_ERROR` event). Why Gemini
  failed (overloaded, quota, bad key) is in the backend terminal only (D180). "Sorry, I can't reach the expense tools" is
  a normal (grey) reply, not a red bubble.
- **Fix:** see the Gemini and MCP sections below for each message.

### Assistant panel: a red bubble right under half a reply
- **Cause:** the run failed after it had started streaming (a `RUN_ERROR` event, e.g. Gemini became overloaded). The text
  that had already arrived stays. The failed turn isn't saved, so the assistant won't remember that exchange.
- **Fix:** ask again. If a tool had already run (e.g. an expense was added before the failure), that change stays even
  though the page didn't refresh, so check the Expenses page before repeating an "add".

### Assistant panel: "The connection closed before the reply was finished."
- **Cause:** the stream ended without `RUN_FINISHED` or `RUN_ERROR`: the backend stopped mid-run (Ctrl+C, a crash, or a
  forced restart). An auto-reload doesn't cut a run; it waits for it to finish (see "Every request stays pending" above).
- **Fix:** send the message again (same caveat as above if a tool had already run).

### Assistant panel: the reply appears all at once instead of word by word
- **Cause:** Gemini decides how big each piece is; a short reply may come in one or two pieces. Otherwise, something
  between the backend and the browser is buffering the response (a proxy, or an antivirus "web shield" that scans traffic).
- **Fix:** watch the raw stream with `curl.exe -N` (see [phases/phase-14-agui-streaming.md](phases/phase-14-agui-streaming.md)).
  If the events arrive spread out there, the backend streams correctly and the buffering is on the browser's side.

### Swagger UI (`/docs`) shows nothing for `POST /agent` until the run ends
- **Cause:** Swagger UI waits for the whole response before displaying it. The stream itself is fine.
- **Fix:** use `curl.exe -N` to watch the events arrive, or `POST /chat` for a plain JSON reply.

### Assistant panel: the assistant added an expense but the page didn't update
- **Cause:** the pages reload when the agent sends a `STATE_SNAPSHOT` (the assistant then reports "data changed", and
  `app/providers.tsx` invalidates the expenses and Dashboard queries). That happens only after a tool that may change
  data **succeeded** (a ✓ chip such as "Expense saved"). A red ✗ chip means the backend refused it.
- **Check:** in the raw stream (`curl.exe -N`, see [phases/phase-15-tool-progress.md](phases/phase-15-tool-progress.md)),
  a `STATE_SNAPSHOT` should follow that tool's `TOOL_CALL_RESULT`. If it doesn't, the tool may be marked
  `read_only_hint=True`: check which annotations (`READS_ONLY`, `ADDS_DATA`, `CHANGES_DATA`, from
  `modules/mcp/tools/support.py`) its own file in `modules/mcp/tools/` registers it with. After changing a tool's
  annotations, restart the app: the assistant reads the tool list only once.

### Assistant panel: a tool chip keeps spinning
- **Cause:** the tool is still running. An MCP call gives up after 15 s, and then the chip turns red. If the whole run
  fails, every spinning chip turns red along with the red error bubble.
- **Fix:** if one spins much longer than 15 s, check the backend terminal; the server may be stuck (see "Every request
  stays pending" above).

### Assistant panel: "Waiting for your OK" after asking to delete
- That's the delete safety rule (decisions D129, D145): in the web panel, the assistant's `delete_expense` call only looks
  the expense up (`get_expense`), and nothing is deleted. Press **Approve** on the card; the chip then reads "Deleting expense…" → "Expense deleted".

### Assistant panel: the conversation disappeared
- **Cause:** a browser reload clears it (it's kept in memory across pages and panel toggles, not across reloads), or
  **New conversation** was clicked. The thread itself is still on the server: `GET /api/v1/threads/{id}`.

### Build error: `Cannot find module 'cn'` in a `shared/ui/` file
- **Cause:** `cn` is a real npm package, shadcn's class-name merger, listed in `web/package.json`. The shadcn components
  import it. This error means `node_modules` is missing or out of date. (An earlier version of this entry blamed
  shadcn and said to edit the import; that was wrong, see decisions D119.)
- **Fix:** run `npm install` in `web/`.

### Assistant panel: a card says "Can't show …"
- **Cause:** the agent's A2UI description contained something the renderer doesn't allow or support yet: a component
  outside the catalog, a data-bound value, a broken child reference, or very deep nesting. Showing a harmless note
  instead is deliberate (decisions D118).
- **Fix:** none needed in the browser. If a card from SpendWise's own backend shows this, its card builder
  (`modules/assistant/a2ui/cards.py`) has a bug.

### Assistant panel: Approve says "That card can't be used any more"
- **Cause:** the server has no record of that delete card. It was already answered (each card decides once), it's more
  than 15 minutes old, the backend restarted since it was shown (records live in memory), or it belongs to an earlier
  conversation. Nothing was deleted.
- **Fix:** ask to delete it again, and press Approve on the new card.

### Assistant panel: Approve says "I couldn't confirm that expense #… is still what the card showed"
- **Cause:** before deleting, the server checks the expense against what the card showed. It was edited since, it's
  already gone, or the tools couldn't be reached for the check. Deleting anyway could remove something you never saw
  on the card, so nothing was deleted.
- **Fix:** ask again; the new card shows the expense as it is now.

### Assistant panel: a chip says "Expense saved?" (with a question mark)
- **Cause:** the connection broke while that tool was running, so the browser never heard whether it finished. The
  pages were reloaded to show what really happened.
- **Fix:** look at the Expenses page before trying again, so nothing is saved twice.

### Assistant panel: I said "yes, delete it" but nothing was deleted
- **Cause:** that's the design (D129). In the web panel, only the **Approve** button deletes; the model can't, whatever
  it's told. Saying "yes" just gets you a new card to approve.
- **Fix:** press Approve on the card.

### Assistant panel: the insight card's donut is empty or squashed
- **Cause:** the chart is drawn by Recharts, which measures the space it has; a very narrow panel leaves little room.
  The legend beside it always lists every category and amount.
- **Fix:** drag the panel wider. "Can't show a chart without data" means the chart arrived with no usable points
  (a broken description); a month with no spending simply has no chart, and says "No expenses in <month>".

### Assistant panel: "add lunch" got questions in text, not a form
- **Cause:** the model chose to ask instead of calling `show_expense_form`. It's guided by its instructions, not
  forced, and smaller models (like flash-lite) follow them less reliably. `POST /chat` never shows forms (D123).
- **Fix:** answer the questions; that works too. Or say "show me the form". If it never shows a form, check that the
  backend reloaded after the update.

### Assistant panel: the form's Save button is greyed out
- **Cause:** the form was already sent (one submission only), or another run is still in progress (all forms lock
  while the assistant works). If the send failed, the form unlocks again.
- **Fix:** wait for the reply. To change something after sending, just say so in the chat ("make it 300").

### The form shows, but not the model's own: the backend logs "the model's form was rejected"
- **Cause:** the form the model wrote didn't pass the checks: an unknown component, a property the catalog doesn't
  have, a broken child id, a bad binding path, or no Save button. The log line says which. The built-in form was sent
  instead (`metadata.source: "fallback"`). That's the design (D125), not an error.
- **Fix:** nothing needed. If it happens nearly every time, the model is struggling with the catalog text in
  `a2ui/forms.py`.

### A form field says "Can't show a time picker" or "a multiple-choice picker"
- **Cause:** only date pickers and single-choice pickers are supported (D121). A form asking for a time or several
  choices gets a placeholder for that field.

### Assistant panel: a tool ran but no card appeared
- **Cause:** a card is only sent after a **successful** tool call (a ✓ chip); a red ✗ chip never gets one. If the tool's
  result couldn't be read, the card is skipped on purpose and the text reply still arrives. The backend terminal then
  logs `no A2UI card for <tool>: ...`.
- **Fix:** read that log line. After changing backend code, check that the server reloaded.

### Dashboard shows "Couldn't load the dashboard"
- **Cause:** one of its requests failed, most often because the backend isn't running.
- **Fix:** start the backend (`.\run.ps1`) and click **Try again**. The message under the title says what failed; if it
  says "Something went wrong", the browser console has the details.

### Dashboard charts say "No spending…" but I have expenses
- **Cause:** the charts show the **current** month and the last 6 months, in **INR** only. Expenses dated outside
  that window, or in another currency, aren't included.
- **Fix:** check the expense dates (the seed script dates its samples relative to the day it ran).

### `npm run dev`: "Cannot find module" or a blank page after pulling changes
- **Cause:** `package.json` changed but `node_modules` wasn't updated.
- **Fix:** run `npm install` in `web/`, then `npm run dev` again.

### A shadcn component looks wrong, or I want to change it
- shadcn/ui components are source files in `web/src/shared/ui/` (`components.json` points shadcn there). Edit them like
  any other file.
  `npx shadcn@latest add <name>` adds new ones; re-adding an existing one asks before overwriting.

### `404` for `/expenses`, `/summary`, `/chat` ... (the old URLs)
- **Cause:** the REST API moved under `/api/v1` (D149): `/api/v1/expenses`, `/api/v1/chat`, ... `/health` and `/mcp/`
  stay where they were.

### TypeScript errors after changing the backend's API, or a type doesn't match what the API sends
- **Cause:** the web app's API types are generated from the backend, and they're out of date.
- **Fix:** `.\.venv\Scripts\python.exe backend\scripts\export_contracts.py`, then `cd web; npm run gen:api`.

### `npm install openapi-typescript` fails with `ERESOLVE` (peer typescript ^5)
- **Cause:** openapi-typescript 7.13 wants TypeScript 5; this app uses 7 (D160).
- **Fix:** don't install it; `npm run gen:api` runs it pinned through `npx`, in its own install.

### `npx oxlint`: "… import is restricted from being used by a pattern"
- **Cause:** an import breaks the feature-slice rules (D153): a file inside another feature, a relative import out of a
  feature, `@/app` in a feature, or a feature in `shared/`.
- **Fix:** import the other feature's public API (`@/features/<name>`; export what you need from its `index.ts`), or
  move the shared piece into `shared/`.

### Assistant panel: "Stopped." under a reply
- You pressed **Stop**. What already arrived stays; a tool that was running shows "?" (it may or may not have finished),
  and the pages reload so they show what really happened.

## MCP

### `No module named 'mcp.server.fastmcp'` / tutorials say `FastMCP`
- **Cause:** MCP SDK 2.x renamed `FastMCP` to `MCPServer`.
- **Fix:** `from mcp.server.mcpserver import MCPServer`, as `modules/mcp/server.py` does.

### `Error loading ASGI app. Attribute "app" not found in module "app.main"`
- **Cause:** an old start command. The app is built by `create_app()` and served in uvicorn's factory mode, so
  importing `app.main` builds nothing by itself (D173).
- **Fix:** start it with `.\run.ps1`, or `uvicorn app.main:create_app --factory --app-dir backend`.

### A page or the chat panel says it hit a problem: "Failed to fetch dynamically imported module"
- **Cause:** pages and the chat panel load their code on first use (D174). That load failed: the network dropped, or
  the tab was open across a rebuild and the old file is gone.
- **Fix:** press **Try again**; it loads the code afresh (`lazyWithRetry`). After a rebuild, reloading the page also
  works.

### An MCP client can't connect to `http://127.0.0.1:8000/mcp/`: 404, 401, 421 or 403
- **404:** MCP over HTTP is off until `MCP_TOKEN` is set in `.env` (D150). Set it, restart, and use
  `http://127.0.0.1:8000/mcp/` (with the trailing slash; `/mcp` answers with a redirect some clients don't follow).
- **401:** the client must send `Authorization: Bearer <MCP_TOKEN>` (in MCP Inspector, as a custom header). Stdio
  (`backend\mcp_stdio.py`) needs no token.
- **421 "Invalid Host header" or 403:** the SDK only accepts local Host and Origin headers; connect to 127.0.0.1 or
  localhost, not another hostname.

### A tool call returns only "Error executing tool <name>"
- **Cause:** an *unexpected* exception; the SDK hides its text from clients on purpose.
- **Fix:** read the traceback in the server's terminal (for stdio, the host's server log). Expected problems, like an
  unknown category, come with a clear message instead.

### `/chat` replies "Sorry, I can't reach the expense tools right now"
- **Cause:** by default the tools run in-process, so this means `MCP_URL` is set in `.env` and that server didn't answer
  (wrong URL or port, server down, or a wrong `MCP_TOKEN`: it answers 401).
- **Fix:** remove `MCP_URL` from `.env` (and restart) unless the tools really run as a separate service. The terminal
  logs where it tried.

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
3. Run `.\.venv\Scripts\python.exe backend\seed.py` (it runs the migrations, which create empty tables, then fills them).

### The server won't start: "The database is at migration …, but the code needs …"
- **Cause:** the code expects newer tables than the database has (D148). `.\run.ps1` runs the migrations first, but
  starting uvicorn some other way doesn't.
- **Fix:** `.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head`, then start again. Your data is kept.
  (After the code-review fixes, a database at `0002` needs `0003`, which adds `expense.version`: restarting
  `.\run.ps1` applies it.)

### A migration failed half-way: is my database half-changed?
- **No.** An upgrade runs in one transaction, schema changes included (D163), so a failure leaves the database at the
  migration it was at before. The error above the traceback says which step failed.
- **Fix:** fix the cause, then run `upgrade head` again.

### I changed a table's fields, but the database didn't change
- **Cause:** tables change only through migrations (D148).
- **Fix:** `.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini revision --autogenerate -m "what changed"`,
  read the new file in `backend\migrations\versions\`, then `upgrade head`.

### Seed says "Already seeded; nothing to do"
- **Cause:** categories already exist, and the seed refuses to duplicate them.
- **Fix:** that's expected. Delete the database first if you want to start over.

### Approve says "I couldn't confirm that expense … is still what the card showed", or "has changed since it was shown"
- **Cause:** the expense was edited (or deleted) after its card appeared. Approve deletes only the exact version the card
  showed (D162), so nothing was deleted.
- **Fix:** ask the assistant again; the new card shows the expense as it is now.

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
