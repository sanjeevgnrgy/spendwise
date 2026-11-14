# Decision log

Every design decision so far, newest phase last. Each entry says what was decided, why, and when
to look at it again. Add new entries at the end; don't rewrite old ones. If a decision is replaced,
add a new entry and mark the old one **Superseded by D<n>**.

---

## Setup and tooling

### D1. One virtual environment per project, at `spendwise/.venv` (Phase 1)
- **Why:** keeps SpendWise's libraries separate from every other Python project, so versions can't clash
  and `requirements.txt` is the complete list. See [concepts/python-tooling.md](concepts/python-tooling.md).
- **Consequence:** `.venv` is never committed. Recreate it after moving or renaming the project folder.
- **Updated by D36:** the venv is now `.venv` at the repo root.

### D2. Pin direct dependencies to exact versions (Phase 1)
- **Why:** every machine installs the same versions, so "works on my machine" means it works everywhere.
- **How:** only packages we import directly are listed, as `package==x.y.z`; pip resolves the rest.
  For example, `python-dotenv` isn't listed because `pydantic-settings` installs it (Phase 3).
- **Updated by D160:** the web app's `package.json` is pinned the same way.

### D3. Run tools as `python -m <tool>` (Phase 1)
- **Why:** guarantees `pip` / `uvicorn` run with the venv's Python, even if another copy comes first on `PATH`.

### D4. `run.ps1` for a one-command start (Phase 1)
- **Why:** removes the "forgot to activate / forgot to install" mistakes.
- **How:** creates `.venv` if missing; reinstalls only when `requirements.txt` is newer than the marker file
  `.venv\requirements.installed` (pip's "already installed?" check costs ~2.5 s per start); then starts
  uvicorn with `--app-dir backend --reload --reload-dir backend`.
- **Revisit when:** macOS/Linux users join (add a `run.sh`).

### D5. Secrets and settings in `.env`; `.env.example` committed (Phase 1–2)
- **Why:** the API key never reaches git; `.env.example` tells others which settings exist.
- **Rule:** a phase that adds a setting adds its name to `.env.example` in the same commit.

---

## Gemini

### D6. Use Gemini's Interactions API, not `generate_content` (Phase 2)
- **Why:** Google's docs (checked 2026-11-13) call the Interactions API generally available since June
  2026 and "the recommended interface for all new projects". `generate_content` is "legacy" but still
  fully supported, with no end date announced.
- **Revisit when:** building the assistant's function calling. The docs say automatic function calling
  (Python), the Batch API and explicit caching are "not yet available in the Interactions API".

### D7. `store=False` on every Gemini call (Phase 2)
- **Why:** by default, the Interactions API keeps every request and answer on Google's servers
  (1 day on the free tier, 55 days on paid) for later retrieval. We don't need server-side history,
  and prompts will contain spending data.
- **Not covered:** this doesn't change the free tier's data-use terms. See D11.

### D8. Catch errors broadly, but only around the single Gemini call (Phase 2)
- **Why:** google-genai 3.3.0 raises the Interactions API's errors from a private module
  (`google.genai._gaos...`) and doesn't export that class publicly. Catching the public
  `google.genai.errors.APIError` would miss every Gemini error, and importing from a private
  module could break in any SDK update.
- **Revisit when:** the SDK exports the class publicly; then catch it by name.

### D9. Pass the API key explicitly to `genai.Client` (Phase 2)
- **Why:** the SDK reads both `GEMINI_API_KEY` and `GOOGLE_API_KEY`, and silently prefers
  `GOOGLE_API_KEY` if both are set. Passing ours explicitly removes that surprise.

### D10. Model `gemini-3.8-flash`, set by `GEMINI_MODEL` (Phase 2)
- **Why:** it's labelled stable and is available on the free tier. `gemini-4-argon` and `gemini-4-carbon`
  are not on the free tier. (`gemini-4-hydrogen` is free too and was used at first.)
- **How to change:** edit `GEMINI_MODEL` in `.env` and restart. No code changes needed.

### D11. Only sample data while on the free tier (Phase 2)
- **Why:** Google's pricing page says free-tier content is "used to improve our products"; the paid tier
  says it is not. Use made-up expenses and receipts, not real financial data, until billing is set up.

---

## Architecture (Phase 3)

### D12. Modular monolith
- **What:** one FastAPI app, one database, split into business modules under `backend/app/modules/`.
  The rules are in [architecture.md](architecture.md).
- **Boundaries:** the MCP server becomes an `mcp` module mounted at `/mcp`. The A2A agents (receipt,
  insights, currency) are separate services outside the monolith, in `agents/`.
- **Updated by D139, D140:** modules now speak in commands and queries through a bus, and plug in through `module.py`.

### D13. No database foreign keys between modules
- **Why:** a foreign key would tie two modules' tables together at the database level. Ids are checked
  through the other module's public service instead (`categories.get_category()`).
- **Trade-off:** the database no longer guards the link, so the service must.

### D14. Services return frozen DTOs, never table rows
- **Why:** callers get a read-only copy, so they can't change or lazy-load another module's data through it.
- **Updated by D139:** queries return frozen DTOs; commands return at most an id.

### D15. Money as integer paise plus a currency code
- **What:** `amount_minor: int` (450.50 rupees is `45050`) and `currency` (default `INR`).
- **Why:** floats can't store most decimal fractions exactly (`0.1 + 0.2 = 0.30000000000000004`);
  whole numbers are exact.
- **How:** convert only with `app.core.money`, which uses `Decimal` and **rejects** fractions of a paisa
  rather than rounding them away. Never pass money through a `float`.

### D16. Settings through pydantic-settings, in one place
- **What:** `backend/app/core/config.py` reads `.env` into a typed `Settings` object.
- **Details:** real environment variables override `.env`; an empty value (`KEY=`) counts as not set;
  the API key is a `SecretStr`, which prints as `**********`.

### D17. SQLite file `backend/spendwise.db` by default
- **Why:** zero setup for learning. `DATABASE_URL` switches to another database (e.g. Postgres) without code changes.
- **Detail:** `check_same_thread=False` is set for SQLite only, because FastAPI runs routes on worker threads.

### D18. Tables created at startup with `create_all`; no migrations yet
- **Consequence:** `create_all` creates missing tables but **never changes existing ones**. After changing
  a model, delete `backend/spendwise.db` and re-seed.
- **Revisit when:** there's data worth keeping, or before moving to Postgres. Add migrations (Alembic) then.
- **Superseded by D148:** Alembic migrations create and change the tables; the app no longer calls `create_all`.

### D19. `created_at` stored in UTC
- **Why:** one unambiguous time zone in storage; converting to local time is the frontend's job.

### D20. Payment method is a fixed list (`PaymentMethod` enum)
- **Values:** `cash`, `upi`, `card`, `netbanking`, `wallet`, `other`.
- **Why:** reports can group by it, and typos like `"UPI "` can't get in.

### D21. Category icons are names (`utensils`), not emoji
- **Why:** plain text is safe everywhere (the Windows terminal can fail on emoji); the frontend maps names to pictures.

### D22. The seed script is safe to re-run
- **How:** it stops if any category exists. To start over, stop the server, delete `backend/spendwise.db`,
  restart the server, then run the seed.
- **Rule:** it uses only the modules' public interfaces, like any other caller.

### D23. `/hello` removed
- **Why:** it was a Phase 1 demo with no home in a business module.

---

## Repository

### D24. Git identity set for this repo only
- **What:** name and email come from this repo's `.git/config` (`git config --local`); the global git
  identity is unchanged. See [git.md](git.md).

### D25. `.vscode/settings.json` is committed
- **Why:** it points VS Code at `spendwise/.venv` and at `spendwise/backend` for imports. Everyone who opens
  the repo gets working import checking. It contains no secrets. The interpreter path is Windows-only.
- **Updated by D36:** the paths are now `.venv` and `backend` at the repo root.

---

## Expenses API (Phase 4)

### D26. The API takes rupees; responses give both paise and rupees
- **In:** `amount` as a decimal (`450.50`), sent as a JSON number or string. At most 2 decimal places and 12 digits.
- **Out:** `amount_minor` (int, the exact stored value) and `amount` (computed from it, e.g. `"450.50"`).
- **Why strings in JSON:** Pydantic writes `Decimal` as a string, so no client parses money into a float by accident.
- **Where it's converted:** in the expenses service, so every caller (API, seed, later MCP) gets the same conversion.

### D27. Schemas check shape; services check business rules
- **Schemas:** types, lengths, ≤ 2 decimal places, currency pattern, date order in filters.
- **Services:** amount > 0, the category exists.
- **Why:** shape errors are caught before any code runs. Business rules live in the one place every caller
  passes through.
- **Updated by D139:** business rules live in each module's `domain.py` and command handlers.

### D28. Service errors become HTTP responses in one place
- **What:** services raise `NotFoundError` or `BusinessRuleError` (`core/errors.py`). `main.py` registers
  handlers that turn them into 404 / 422 with `{"detail": "<message>"}`.
- **Why:** services stay free of HTTP (so MCP tools can reuse them), and routers need no try/except.
- **Revisit when:** a third kind of error appears, or to move `/ask`'s Gemini → 502 mapping here too.
- **Updated by D48:** a third kind was added (`ExternalServiceError` → 502).
- **Updated by D149:** every error is now an RFC 9457 problem-details response.

### D29. 404 only for the resource in the URL
- An unknown `category_id` in a request body is **422**, not 404: the endpoint exists, the body is invalid.

### D30. PATCH is a partial update
- Only fields the client sent are changed (`model_dump(exclude_unset=True)`).
- Required fields can't be set to `null` (422). `note` can, which clears it.
- Changing `amount` or `category_id` re-runs the same rules as create.

### D31. Filters for `GET /expenses`
- Named `start_date`, `end_date` (both inclusive), `category_id`, `merchant` (exact, any case) and `search`
  (contains, in merchant or note).
- `%` and `_` in `search` are matched literally (`autoescape`), not as SQL wildcards.
- Defined as one query model with `extra="forbid"`, so unknown parameters are a 422 instead of being ignored.
- Filtering by category **id** rather than name keeps it exact; the frontend and AI can look up ids via `GET /categories`.

### D32. `GET /summary` covers one month in one currency
- `month=YYYY-MM` is required; `currency` defaults to `INR`, because adding different currencies is meaningless.
- The database adds up the totals (`GROUP BY`); category names come from the categories module's public interface.
- A category id with no matching category shows as "Unknown" instead of failing (possible because there's no foreign key).
- Categories are listed biggest spend first. Categories with no spending that month are left out.

### D33. `DELETE` is permanent and returns 204
- No "are you sure?" at the API level. Confirmation is the assistant's job (project safety rule: confirm before deletes).
- **Revisit when:** undo or soft-delete is wanted.

### D34. No pagination on `GET /expenses` yet
- It returns every matching row. Fine for a learning dataset.
- **Revisit when:** lists get long. Add `limit` / `offset` then.
- **Superseded by D149:** `GET /expenses` returns `{items, total}` with `limit` and `offset`.

### D35. `get_expense` raises; `get_category` returns `None`
- `expenses.get_expense()` raises `NotFoundError`, because callers asking for a specific expense expect it to exist.
- `categories.get_category()` returns `None`, because other modules use it as a "does this exist?" check.

---

## Repository on GitHub

### D36. The project lives at the repository root
- **What:** everything that was in `spendwise/` moved up to the repo root, just before the first push.
- **Why:** GitHub shows the root README on the repo's front page, and a fresh `git clone` gives
  `spendwise/backend`, `spendwise/docs`, ..., matching these docs.
- **Consequence:** the venv was recreated, because venvs can't be moved. Local folder names don't matter;
  "the project folder" means wherever the repo is checked out.

### D37. The GitHub remote URL includes the account name
- **What:** `origin` is `https://sanjeevgnrgy@github.com/sanjeevgnrgy/spendwise.git` (a private repo).
- **Why:** Git Credential Manager on the development machine already holds a login for a different GitHub
  account. With the username in the URL, it keeps a separate login for this repo, and other repos are unaffected.

---

## Tests (Phase 5)

> **Superseded by D64:** the tests, `pytest.ini` and `requirements-dev.txt` were removed after Phase 8.

### D38. Test tools live in `requirements-dev.txt`
- **What:** `requirements-dev.txt` = `-r requirements.txt` + `pytest` + `httpx` (needed by `TestClient`), pinned.
- **Why:** a deployed server installs only `requirements.txt` and never gets test tools.

### D39. Every test gets its own in-memory database
- **How:** the `engine` fixture creates `sqlite://` with `StaticPool` (one shared connection; otherwise each
  connection would be a different, empty database) and `check_same_thread=False` (TestClient runs the app in
  another thread). The `client` fixture swaps `get_session` through `app.dependency_overrides`.
- **Safety net:** `conftest.py` sets `DATABASE_URL=sqlite://` and dummy Gemini settings **before** importing
  the app, so neither `backend/spendwise.db` nor the real API key in `.env` can be reached, even by mistake.
- **No Gemini in tests:** `/ask` isn't tested yet; testing it would need a fake Gemini client.

### D40. The architecture test is a small `ast`-based pytest, not import-linter
- **Why:** our main rule ("only the package or names in its `__all__`, never a submodule") is easy to state in
  ~60 lines of plain Python and hard to express in import-linter contracts. It also adds no dependency, and
  the rules are readable in one file.
- **Limitation:** it reads `import` statements only. Imports done at runtime with `importlib` aren't seen; we don't use those.
- **Exempt:** `main.py` (the composition root imports routers) and the tests.

### D41. The checker has its own test
- `test_checker_catches_violations` builds a fake project with known violations and checks each one is reported.
  A checker that silently found nothing would otherwise pass forever.

---

## Structured output (Phase 6)

### D42. Structured output through `response_format`, validated with Pydantic
- **How:** `interactions.create(..., response_format={"type": "text", "mime_type": "application/json",
  "schema": ParsedExpense.model_json_schema() ...})`, then `ParsedExpense.model_validate_json(output_text)`.
  This is the pattern in Google's structured-output docs (checked 2026-11-13). The older `response_mime_type`
  parameter is marked deprecated in the SDK.
- **If the answer doesn't validate:** `GeminiError` → 502.

### D43. Every schema field is required; unknowns are `null`
- **Why:** Gemini must fill every field, and `null` lets it say "not stated" instead of inventing a value.
  This follows Google's advice: "Mark properties as required where possible and allow null values when a field can be empty."
- **No defaults in the schema:** only keywords the docs list as supported are sent.
- **`amount` travels as a string** (`WithJsonSchema({"type": ["string", "null"]})`) so the exact digits survive;
  Pydantic turns it into a `Decimal`.

### D44. Categories are an `enum` added to the schema per request
- The names come from `categories.list_categories()` (public interface). With no categories, `/parse` returns 422
  without calling Gemini.
- The answer is re-checked: a category not in the list becomes `null`. Model output is data to verify.

### D45. `/parse` never saves; it returns `missing_fields`
- `missing_fields` lists what `POST /expenses` would still need: `amount`, `category`, `merchant`, `payment_method`.
- `currency` (default INR) and `spent_on` (default today) always get a value, so they're never missing.
- Saving stays a deliberate step: the user, or later the assistant after confirming, calls `POST /expenses`.

### D46. "Today" is the server's date
- Good enough for one user running locally.
- **Revisit when:** there's auth and users in different time zones; then the client should send its date.
- **Updated by D151:** "today" comes from a Clock (still the server's date).

### D47. The note is treated as data
- The system instruction tells Gemini the note is data to extract from, and to ignore any instructions inside it.

### D48. `ExternalServiceError` → 502, handled in one place
- `core/errors.py` adds `ExternalServiceError`; `GeminiError` is a kind of it. `/ask` and `/parse` have no try/except;
  the shared handler returns 502.

### D49. Gemini calls give up within about a minute
- **Why:** the SDK's defaults (5 attempts, up to 60 s between them) made requests hang for minutes during a 503
  "high demand" outage of `gemini-3.8-flash`.
- **How:** `HttpOptions(timeout=30_000 ms, retry_options=HttpRetryOptions(attempts=2))` on the client.
  Measured: an outage now returns 502 in about 32 s.
- **Revisit when:** responses legitimately take longer than 30 s (e.g. long reports); then raise the limit for those calls.
- **Updated by D56:** the per-attempt limit is now 60 s.
- **Updated by D108:** only 5xx errors are retried; a 429 fails at once.

---

## Function calling chat (Phase 7)

### D50. A hand-written agent loop, capped at 5 steps
- **How:** send the history and tool declarations; if Gemini returns `function_call` steps, run them, append its steps
  (unchanged) plus one `function_result` per call (matched by `call_id`), and repeat until it answers in text.
- **Stateless:** with `store=False`, each request carries the whole history, as Google's "stateless function calling" docs describe.
- **Cap:** `MAX_STEPS = 5` Gemini calls per message. At the cap, `/chat` returns a "too many steps" reply with the calls made so far.
- **Why by hand:** the docs say automatic function calling isn't available in the Interactions API (Python), and
  writing the loop makes every step visible.

### D51. Tool declarations are built from the tool functions
- Each tool's docstring is its description, and each argument is `Annotated[type, "description"]`. `agent.py` turns
  the signature into `{"type": "function", "name", "description", "parameters"}`, so declarations can't drift from the code.
- Arguments are plain JSON types (`str`, `int`, `bool`; optional = `| None` with a default). Amounts and dates are strings;
  the expenses module validates them, as for the REST API.
- Tools call only the `expenses` and `categories` public interfaces (the architecture test enforces this).

### D52. Tool errors go back to the model
- Unknown tool, wrong arguments (`inspect.signature(...).bind`), `BusinessRuleError`, `NotFoundError` and `ValueError`
  (including Pydantic's `ValidationError`) become `{"error": ...}` with `is_error: true`. The model can correct
  itself or tell the user. Unexpected exceptions still surface as 500s, so real bugs aren't hidden.

### D53. Deleting needs explicit confirmation
- `delete_expense(expense_id, confirmed=False)` only looks the expense up and returns `needs_confirmation`.
  The system instruction says to show it and ask, and to use `confirmed=true` only when the user clearly confirms.
- **Limitation:** this is a *soft* guard, because the model decides when `confirmed=true` is justified.
- **Revisit when:** conversation threads exist; then confirmation can be enforced on the server (e.g. a pending action the user approves).
- **Updated by D129:** in the web panel, the server now enforces it with Approve/Cancel buttons; `POST /chat` keeps this soft guard.
- **Updated by D145:** the preview is the read-only `get_expense`; `delete_expense` needs a strict `confirmed=true`.

### D54. `/chat` is single-turn for now
- Each message starts a new conversation, so a follow-up must repeat the details.
- **Revisit when:** chat threads are added (assistant module, later phase).
- **Superseded by D58–D61** (Phase 8: threads and memory).

### D55. The agent uses `thinking_level="low"`
- **Why:** in live tests, a delete request spent 40–60+ s per step thinking and timed out. With `low` it took 9 s in total.
  Bookkeeping tasks don't need deep reasoning.
- **Where:** `agent.THINKING_LEVEL`, passed through `llm.ask_gemini_with_tools(..., thinking_level)` as
  `generation_config={"thinking_level": ...}`.
- **Updated by D102:** the function is now `llm.stream_gemini_with_tools()`; the setting is unchanged.

### D56. Gemini attempts time out after 60 s (was 30 s)
- A function-calling step can take 20–30 s. With 2 attempts, a total outage still ends in a 502 within about 2 minutes.

### D57. SpendWise logs its own steps to the console
- `core/logging.py` (called in `main.py`) sets `spendwise.*` loggers to INFO; libraries stay at WARNING.
- The agent logs the user message, each step, each tool call with its arguments, and each result (first 300 characters).
- These logs contain expense data. Fine on your own console; don't ship them to an external service without thinking about privacy.
- **Updated by D152:** message text and tool arguments are logged only at DEBUG.

---

## Memory (Phase 8)

### D58. Threads are stored as raw Gemini steps in `ChatMessage`
- **What:** one row per step (`user_input`, `thought`, `function_call`, `function_result`, `model_output`), with
  `thread_id`, `turn` and the step as JSON, in a table owned by the assistant module.
- **Why raw steps:** stateless function calling needs the history resent exactly as received, thoughts included.
  Storing anything else would mean rebuilding Gemini's format later.
- **No separate `Thread` table:** a thread is just the rows that share a `thread_id`. Add one if threads need titles or owners.
- **Superseded by D141:** threads are stored as provider-neutral messages in the conversations module.

### D59. The server picks thread ids; an unknown id is a 404
- New threads get `uuid4().hex` (32 characters). Sending an id that doesn't exist returns 404 instead of starting a
  new conversation, so a typo can't silently lose the context.

### D60. Only the last 10 turns are sent (`MAX_HISTORY_TURNS`)
- **Why:** history is paid for on every request and every agent step, and long histories are slower and can distract
  the model. Ten turns covers normal follow-ups.
- Trimmed by whole turns, so calls and results stay paired. Older turns stay stored.
- **Revisit when:** conversations need longer memory. Then summarise old turns instead of dropping them.

### D61. A turn is saved in one go, after it finishes
- The agent returns every step of the turn (`AgentResult.steps`), and the service stores them in a single commit.
- When the 5-step cap is hit, the apology is stored as the model's answer, so the turn still ends cleanly.
- **Limitation:** if Gemini fails mid-turn (a 502), that turn isn't stored, but tools that already ran (e.g.
  `add_expense`) have changed data. A retry may then repeat the action. **Revisit when:** this bites; then store
  steps as they happen and mark the turn incomplete.

### D62. `GET /threads/{id}` is a readable view
- Returns turn, kind, text and time per step. `thought` steps are stored but hidden, because they're internal
  reasoning, not conversation.

### D63. Token usage is logged per step
- `tokens: N in, M out` (from `interaction.usage`) makes the cost of history visible while you chat.

**Note on D53 (delete confirmation):** with threads, "yes" in a follow-up now has context, so confirming a delete
is natural. It's still a soft, model-judged guard.

---

## Tests removed (after Phase 8)

### D64. No automated tests for now
- **What:** the pytest suite (`backend/tests/`), `pytest.ini`, `requirements-dev.txt` and the `.pytest_cache/` ignore
  rule were removed at the developer's request. Tests will be added later, by hand. Until then, phases don't add tests.
- **Consequences:**
  - Nothing checks the module-boundary rules automatically; use the scans in [architecture.md](architecture.md#checking-the-rules).
  - Changes are verified by running the server and calling the routes.
- Supersedes D38–D41.

---

## MCP module (Phase 9)

### D65. MCP SDK 2.x: `MCPServer`, not `FastMCP`
- `mcp[cli]==2.3.0`. In 2.x, `FastMCP` was renamed `MCPServer` (`from mcp.server.mcpserver import MCPServer`).
  We use the current SDK rather than pinning `mcp<2`.

### D66. The MCP module is an adapter with no tables and no rules
- `modules/mcp/server.py` holds one `MCPServer("spendwise")` with 5 tools and 2 resources. Each calls only the
  `expenses` and `categories` public interfaces, and opens its own database session per call.
- It exports nothing to other modules. `main.py` (composition root) and `backend/mcp_stdio.py` import `server`.

### D67. The assistant's tools and the MCP tools are near-copies, for now
- `assistant/tools.py` (Phase 7) and `mcp/server.py` wrap the same services in almost the same way. Modules can't
  share internals, and the plan is for the assistant to call the MCP tools.
- **Revisit when:** the assistant becomes an MCP client. Then delete `assistant/tools.py`.
- **Resolved by D72** (Phase 10): `assistant/tools.py` is deleted.

### D68. One server, two transports
- **Streamable HTTP**, mounted at `/mcp` in the FastAPI app: `streamable_http_app(streamable_http_path="/",
  stateless_http=True, json_response=True)`. Stateless with JSON responses, because our tools are simple
  request/response and need no per-client session in memory. The session manager is started in `main.py`'s `lifespan`.
- The URL is **`/mcp/`** with a trailing slash; `/mcp` returns a 307 redirect to it.
- **stdio**, via `backend/mcp_stdio.py`, for local hosts (Inspector, Claude Desktop). It never prints to stdout.

### D69. Expected errors become `ToolError`s
- The SDK reports unexpected exceptions to clients as a bare "Error executing tool" (their text could leak internals).
- `_tool_session()` converts `BusinessRuleError`, `NotFoundError` and `ValueError` (incl. Pydantic validation) into
  `ToolError`, whose message the client's model does see and can act on.

### D70. No authentication on `/mcp` yet
- Anyone who can reach the server can read and change expenses through MCP, as with the REST API today. Fine on
  `127.0.0.1`. The SDK's default DNS-rebinding protection only accepts local Host headers.
- **Revisit when:** auth is added, or before exposing the server beyond localhost.
- **Superseded by D150:** `/mcp/` is served only with `MCP_TOKEN`, as a bearer token.

### D71. Deletes over MCP use the same soft confirmation as the assistant
- `delete_expense(confirmed=false)` only reports what would be deleted. Hosts such as Claude Desktop also ask the
  person to approve tool calls, which is a second check.
- **Superseded by D145.**

---

## Agent uses MCP (Phase 10)

> Written without running the server or Gemini, at the developer's request. Not yet exercised end to end.

### D72. The agent is an MCP client; it has no tools of its own
- `assistant/mcp_client.py` connects to `MCP_URL` (default `http://localhost:8000/mcp`, this app's own MCP module),
  lists the tools, converts them to Gemini declarations, and runs every call with `call_tool`.
- `assistant/tools.py` is deleted. `agent.py` imports no business module and takes no database session; category
  names come from the `expenses://categories` resource.
- **Still direct:** `/parse` uses the `categories` and `expenses.PaymentMethod` public interfaces.
- **Updated by D143:** by default the client connects to this app's MCP server in-process, not over HTTP.

### D73. Tools are listed on first use and cached
- Not at app startup: by default the MCP server is this same app, which isn't serving yet during startup.
- The cache lasts until the app restarts. **Revisit when:** tools change while the app runs.

### D74. One short MCP connection per operation, run with `asyncio.run`
- The SDK is async; the agent runs in a worker thread. Each operation (list, call, read) opens a connection, does
  one thing and closes, with a 15 s timeout.
- `/chat` must remain a plain `def` route, or calling the app's own `/mcp` would deadlock the event loop.
- **Revisit when:** the extra round trips matter; then keep one session per chat turn.
- **Updated by D143:** the SDK's `Client`, in-process by default; still one short session per operation.

### D75. MCP input schemas are simplified for Gemini
- `anyOf [X, null]` becomes `X`; only `type`, `description`, `enum`, `items`, `format` are kept.
- **Revisit when:** a tool uses nested objects or other keywords this drops.

### D76. MCP failures become part of the reply
- `isError` results go back to the model as error results.
- Unreachable before the loop: an apology is returned without calling Gemini (200, stored in the thread).
- Unreachable during a call: the model is told, and tells the user.

### D77. Running on another port needs `MCP_URL`
- The default assumes port 8000. With `--port 8001`, set `MCP_URL=http://localhost:8001/mcp`.
- **Updated by D136:** the default is now `http://127.0.0.1:8000/mcp/` (no redirect, no IPv6 attempt).
- **Superseded by D143:** `MCP_URL` is unset by default (in-process); set it only for a separate MCP server.

---

## Frontend (Phase 11)

> Checked with `npm run build` (type-check and bundle); not yet opened in a browser.

### D78. The frontend stack, as set up by the current tools
- `web/` was created with `create-vite` 9 (`react-ts`): React 19, Vite 8, TypeScript 7, oxlint.
- Tailwind CSS 4 via `@tailwindcss/vite`; the `@/` import alias in `vite.config.ts` and the tsconfig files
  (`paths` only: TypeScript 7 dropped `baseUrl`).
- shadcn/ui via `shadcn init -b radix -p nova` (Radix primitives, "Nova" preset: lucide icons, Geist font,
  neutral colours, CSS variables).
- React Router 8 (`BrowserRouter` + nested `Routes`) and TanStack Table 9.

### D79. TanStack Table 9's opt-in features
- `tableFeatures({ rowSortingFeature, rowSelectionFeature, sortedRowModel: createSortedRowModel() })` and
  `useTable({ features, columns, data })`. Sort functions are passed per column (`sortFn: sortFn_basic` etc.),
  which needs no registration. Cells come from `row.getAllCells()`.

### D80. Filtering on the server, sorting in the browser
- Filters go to the API as query parameters (one source of truth, and fine for large data later). Sorting is done
  by TanStack on the rows returned, because the API has no sort parameter yet.
- Search waits 300 ms after typing stops, and stale responses are ignored (effect clean-up).

### D81. Validation stays on the server
- The form only checks that required fields are filled. Rules like amount > 0 come back from the API and are shown
  as toasts, so they're written once for REST, chat and MCP.

### D82. Theme with `next-themes`
- shadcn's toast component already depends on it, and it works outside Next.js. `attribute="class"` toggles `.dark`
  on `<html>`, matching the `dark` variant shadcn put in `index.css`. Saves the choice; "System" follows the OS.
- **Superseded by D87.**

### D83. All backend calls in `web/src/api.ts`
- Typed functions per endpoint; one `request()` turns failures into `ApiError` with the backend's message
  (`detail` string or validation list), or "Can't reach the SpendWise API" when there's no response at all.
- The base URL is `VITE_API_URL` (default `http://localhost:8000`). Nothing secret may go in `web/.env`:
  `VITE_` variables are visible to anyone using the app.
- **Superseded by D153, D155:** each feature has its own `api.ts`, over a generated, typed client in `shared/api`.

### D84. CORS allows only the Vite dev server
- `CORSMiddleware` with `settings.cors_origins` (default `http://localhost:5173`, `http://127.0.0.1:5173`), methods
  GET/POST/PATCH/DELETE, header `Content-Type`, no credentials. `CORS_ORIGINS` in `.env` changes the list.
- Not authentication: it only governs what browsers let other pages read.
- **Revisit when:** the frontend is served from another address, or in production (then maybe serve both from one origin).

### D85. Deleting always asks first
- An AlertDialog confirms single and bulk deletes, naming the expense for single ones (project safety rule).
  Bulk deletes run one request each with `Promise.allSettled`, and the toast reports successes and failures separately.

### D86. Known warnings
- oxlint warns about four generated shadcn files (`only-export-components`, one `set-state-in-effect`), left as shadcn ships them.
- Vite warns the bundle is over 500 kB. **Revisit when:** more pages exist; then split routes with lazy imports.

### D87. Our own small ThemeProvider instead of `next-themes`
- **Why:** `next-themes` renders a `<script>` for server-rendered apps; in this browser-only app React logs
  "Encountered a script tag while rendering React component".
- **How:** `components/theme-provider.tsx` + `lib/theme.ts` (as in shadcn's Vite dark-mode guide); the edited
  `ui/sonner.tsx` reads the theme from it. An inline script in `index.html` applies the saved theme before React loads,
  to avoid a light flash. `next-themes` is uninstalled.

### D88. Table row selection is controlled state, reset during render
- **Why:** clearing it in `useEffect(..., [expenses, table])` looped forever, because `useTable` returns a new `table`
  object on every render (blank Expenses page, "Maximum update depth exceeded").
- **How:** `useState<RowSelectionState>` passed as `state: { rowSelection }` with `onRowSelectionChange`; cleared when
  the `expenses` prop changes, by comparing during render rather than in an effect.
- **Rule of thumb:** never put a library's per-render return value in an effect that sets state.

---

## Dashboard (Phase 12)

### D89. Aggregation happens in the backend, in SQL
- `GET /summary/trend` groups and sums in the database; the browser receives one number per month.
- Grouping uses `EXTRACT(year/month FROM spent_on)` (SQLAlchemy's `extract`), standard SQL that SQLite and Postgres both
  support, not SQLite's `strftime`.

### D90. The trend is zero-filled, oldest first
- One entry per month in the window, with `total_minor = 0` for months without spending, so charts have no gaps.
- The window counts back from the server's today (as `/parse` and `/chat` do). `months` is 1–24, `currency` defaults to INR.

### D91. `GET /expenses` gains `limit`
- Optional, 1–500, applied in SQL after the newest-first ordering. Added for the Dashboard's "5 most recent"
  instead of downloading every expense.
- **Updated by D149:** `limit` now defaults to 100, with `offset` and a `total`.

### D92. The Dashboard loads four requests in parallel
- Summary, trend, 5 recent expenses and categories, with `Promise.all`. If any fails, the whole page shows an error
  card with Try again, rather than a partial dashboard with misleading zeros.
- **Revisit when:** one slow or failing part should not block the rest; then load each card independently.

### D93. shadcn charts (Recharts 3) for visualisation
- `components/ui/chart.tsx` from `npx shadcn add chart`. Colours come from `ChartConfig` as `--color-<key>` CSS
  variables, set to `var(--primary)` so charts follow the theme. Category breakdown is a horizontal bar chart
  (readable with many categories); the trend is a line.
- Chart values are rupees as numbers, converted from paise **for display only**.

---

## Chat panel (Phase 13)

> Checked with `npm run build`; not yet used in a browser, and no live chat calls were made.

### D94. Pages refresh through a shared "data version" context
- `DataSyncProvider` (in `main.tsx`) holds `dataVersion` and `notifyDataChanged()`. Pages list `dataVersion` in their
  loading effects; the chat bumps it when the assistant changed data.
- **Why not more:** no global store library, no websocket. One number is enough to say "reload", and the backend
  remains the source of truth.
- **Revisit when:** changes can come from outside this browser tab (other devices, background jobs); then the server
  must push updates (e.g. the later AG-UI / SSE work).
- **Updated by D112:** the number now comes from the agent's `STATE_SNAPSHOT`; `setDataVersion` replaces `notifyDataChanged`.
- **Superseded by D154:** TanStack Query; the assistant reports changes and the app invalidates queries.

### D95. "Did the assistant change data?" is decided in the browser from the tool calls
- `add_expense` / `update_expense` that succeeded, or `delete_expense` with `confirmed: true`, in `hooks/use-chat.ts`.
- **Trade-off:** the tool names are repeated here. **Revisit when:** tools grow; then have `/chat` report
  `data_changed` (e.g. from MCP tool annotations like `readOnlyHint`).
- **Superseded by D111** (MCP tool annotations decide, on the server).

### D96. The conversation lives in a `useChat()` hook in the layout
- So it survives closing the panel, switching between desktop panel and mobile sheet, and changing pages.
- It doesn't survive a browser reload; the thread stays on the server (`GET /threads/{id}`). **Revisit when:**
  reloading should restore the chat; then save `thread_id` in localStorage and load the thread on start.
- **Superseded by D154:** the conversation lives in the assistant feature's `AssistantProvider`.

### D97. Desktop: resizable panel with ids; mobile: Sheet
- `ResizablePanelGroup orientation="horizontal"`; the page panel (`id="page"`, min 40%) and the chat panel
  (`id="chat"`, default 32%, 22–50%) are added and removed by `chatOpen` without remounting the page.
- react-resizable-panels v4: **string sizes are percentages, numbers are pixels**.
- Below 768 px (`useIsMobile`), the chat is a right-side `Sheet` (its own close button turned off; a screen-reader-only
  title for accessibility).

### D98. Assistant replies are plain text
- The panel renders text as-is (line breaks kept), so the agent's system instruction now asks for no Markdown.
- **Revisit when:** rich formatting is wanted; then render Markdown safely, or use A2UI components (later phase).

### D99. Fixed shadcn's generated `resizable.tsx`
- It imported `cn` from `"cn"`; changed to `"@/lib/utils"`. Re-adding the component with the CLI could bring the bug back.
- **Superseded by D119:** that import wasn't a bug; `cn` is shadcn's npm package.

### D100. The inner content wrapper is a `<div>`, not `<main>`
- `SidebarInset` already renders `<main>`; the nested `<main>` from Phase 11 was invalid HTML.

---

## AG-UI streaming (Phase 14)

> Checked offline with a scripted fake Gemini stream (TestClient, a real uvicorn server, and the web app's
> `runAgent()` in Node), plus `npm run build`. Not yet run against real Gemini or in a browser.

### D101. `POST /agent` speaks AG-UI over SSE, with FastAPI's own SSE support
- **Types:** `ag-ui-protocol` 1.0.0 (`ag_ui.core`): `RunAgentInput` as the request body, and the event classes. Each event
  is sent as `model_dump_json(by_alias=True)` (camelCase, empty fields left out), which is exactly what the package's
  `EventEncoder` writes.
- **Transport:** `response_class=EventSourceResponse` (FastAPI 0.162) on a **sync generator** route, not a hand-made
  `StreamingResponse`. FastAPI runs the generator in a worker thread, which keeps D74 (the agent calls this app's own `/mcp`,
  so nothing may block the event loop). It also keeps `SessionDep` open until the stream ends, sends `: ping` every 15 s,
  and sets `Cache-Control: no-cache` and `X-Accel-Buffering: no`.
- **Revisit when:** the agent becomes async end to end; then an `async def` generator would avoid tying up a worker thread per run.

### D102. One agent loop for both endpoints; Gemini is always streamed
- `agent.stream()` yields text pieces and finally the `AgentResult`. `/agent` forwards the pieces; `agent.run()` (`/chat`)
  just waits for the result. One loop means the two endpoints can't drift apart.
- `llm.stream_gemini_with_tools()` replaces `ask_gemini_with_tools()`. With `stream=True`, the final
  `interaction.completed` event has **no steps**, so `GeminiStream` rebuilds them from `step.start` + `step.delta` by index:
  `text` → `content`, `arguments_delta` → JSON-parsed `arguments`, `thought_signature` → `signature`. Other deltas are skipped,
  as Google's streaming docs advise.
- **Trade-off:** `/chat` now also depends on that rebuilding code. **Revisit when:** the SDK offers a "final interaction"
  helper for streams; then use it instead.

### D103. The client names the thread; only the newest user message is read
- AG-UI clients choose `threadId` (the web app uses a random 32-hex id), so an unknown id starts a new thread, while
  `/chat` answers 404. Ids over 32 characters are rejected (the `ChatMessage.thread_id` column).
- The server stores the history itself (with thoughts and tool results the browser never sees), so it reads only the last
  `role: "user"` message from `messages` (text parts only, 1–2000 characters, the same limit as `/chat`). The web app
  sends just that one message.

### D104. Errors: an HTTP status before the stream, `RUN_ERROR` after it
- A body FastAPI can't validate (no `threadId`, ...) is a normal 422. Once `RUN_STARTED` has gone out, the 200 can't change,
  so every failure (`BusinessRuleError`, `GeminiError`, anything else) ends the run with `RUN_ERROR`.
- `message` is the error's own text for our expected errors and a generic sentence for anything else (the traceback goes to the
  server log). `code` is the exception class name, or `InternalError`.
- A failed run isn't saved, as with `/chat`. **Known limitation:** if a tool had already changed data before the failure,
  the change stays, but the thread doesn't record it and the page isn't refreshed. **Revisit when:** partial turns can be
  stored, or tools report their effects separately.

### D105. Tool calls ride in `RUN_FINISHED.result`, not `TOOL_CALL_*` events
- This phase streams text only. The tool calls the badges and the page refresh need (D95) are sent once, as
  `RUN_FINISHED.result = {"toolCalls": [...]}`. That is AG-UI's free-form slot for a run's outcome.
- **Revisit when:** the panel should show tools live ("Adding expense…"); then emit `TOOL_CALL_START/ARGS/END/RESULT`.
- **Superseded by D109** (Phase 15: tool events; `RUN_FINISHED` no longer has a `result`).

### D106. One assistant message per run, started lazily
- `TEXT_MESSAGE_START` is sent with the first piece of text, so the panel shows "Thinking…" until there is something to read.
- Text from a later Gemini step (after a tool call) continues the same message, starting a new paragraph (`\n\n`).
  `AgentResult.reply` (used by `/chat`) is the same joined text.
- **Updated by D110:** a text message is now closed before a tool call; text after it is a new message (still one bubble).

### D107. The browser reads the stream with `fetch()`, without an AG-UI client library
- `EventSource` only does GET without a body, so `api.ts` POSTs with `fetch()` and reads `response.body` through a
  `TextDecoderStream`. It splits events on blank lines, keeps the `data:` lines (pings have none), and `JSON.parse`s each.
  `RUN_ERROR` throws; a stream that ends without `RUN_FINISHED` throws too.
- **Why not `@ag-ui/client`:** about 40 lines of our own code show exactly how SSE works, without another dependency.
  **Revisit when:** we adopt an AG-UI frontend framework (e.g. CopilotKit) or need more event types.
- **Updated by D156:** events are now validated with `@ag-ui/core`'s schemas.

### D108. Gemini calls never retry a 429; only 5xx errors are retried
- **Found:** after a few test questions the chat hung forever ("Thinking…", the request pending). Two live probes showed
  Gemini answering every request, streamed or not, with **429 (quota used up)** within a second. The SDK then retried:
  before retrying it sleeps for as long as Google's `retry-after-ms` header says, with **no upper limit** (our 60 s timeout
  only covers the HTTP request itself, not that sleep).
- **Knock-on effect:** with `--reload`, a code change waits for open requests to finish, so the sleeping request also
  blocked the reload, and the server stopped answering every new request.
- **How:** `HttpRetryOptions(attempts=2, http_status_codes=[500, 502, 503, 504])`. The list replaces the SDK's default
  (`408, 409, 429, 5XX`). Checked offline with a mock transport: a 429 with `retry-after-ms: 600000` now fails in under
  1 s with Google's message (before: still waiting after 20 s); a 503 is still retried once.
- **Trade-off:** a momentary per-minute rate limit is no longer retried automatically; the user sees the quota message and
  sends again. **Revisit when:** short automatic waits are wanted; then retry 429 ourselves with a capped delay.

---

## Tool progress (Phase 15)

> Checked offline: the real app and real MCP server with a scripted fake Gemini (a successful add, a read-only summary,
> a failing delete), the raw SSE from Python and the web app's `runAgent()` from Node, plus `npm run build`.
> Not yet tried with real Gemini or in a browser.

### D109. Each MCP call streams as `TOOL_CALL_START/ARGS/END`, then `TOOL_CALL_RESULT`
- START, ARGS (the arguments as one JSON piece) and END go out just **before** the MCP call; RESULT goes out **after** it.
  In AG-UI, END means "the arguments are complete" (the package's docstring), not "the tool has run"; the outcome is RESULT.
- Success is `metadata.ok`: `TOOL_CALL_RESULT` has no error field, and `metadata` is every event's slot for extra data.
  `content` is the tool's text (its error message when it failed), so a failed chip can show why.
- The arguments are sent whole, not as Gemini's fragments: they're only known once `GeminiStream` has the complete call.
- `RUN_FINISHED` no longer carries `result.toolCalls` (D105). `/chat` still returns `tool_calls`.

### D110. A text message is closed before a tool call
- If Gemini wrote text before calling a tool ("Let me check."), `TEXT_MESSAGE_END` is sent before `TOOL_CALL_START`, and
  later text is a new message (starting with the `\n\n` from D106). Tool events never interleave with an open text
  message, which keeps strict AG-UI clients happy. The panel joins a run's text into one bubble.
- **Updated by D115:** the "strict clients" reason was wrong; the behaviour stays, for a different reason.

### D111. "Did this tool change data?" comes from MCP tool annotations
- The MCP server marks `list_expenses` and `get_summary` `read_only_hint=True`; `add_expense` is `destructive_hint=False`;
  `update_expense` and `delete_expense` are `destructive_hint=True`. `mcp_client.changes_data(name)` treats anything not
  marked read-only as a change, as the MCP spec says to assume. Only successful calls count.
- **Why:** the knowledge lives with the tools, and no tool names are repeated in the assistant or the browser (D95).
- **Trade-offs:** annotations are hints, fine to trust from our own server, never from a third-party one. A
  `delete_expense` preview (`confirmed: false`) counts as a change, so the pages reload once for nothing (harmless).
  The tool list is cached (D73), so restart the app after changing annotations.
- **Updated by D133:** in the web panel, a delete preview no longer counts as a change.

### D112. `dataVersion` is AG-UI shared state
- The panel sends `state: {"dataVersion": n}` with every run. After each data-changing tool, the agent sends
  `STATE_SNAPSHOT {"dataVersion": n + 1}`, and the panel stores it in the data-sync context, which makes the pages reload
  (D94) while the reply is still streaming.
- **Why send it each time:** the agent continues from the client's number. Starting from 0 every run could repeat a
  number the panel already has, and then nothing would reload.
- The number counts changes in this browser session only, and a reload starts it at 0 again (pages load fresh anyway).
  **Revisit when:** other tabs or devices must see changes; then the server needs its own version (D94).

### D113. No `STEP_STARTED` / `STEP_FINISHED`
- The phase allowed them "if useful". The chips, streaming text and "Thinking…" already show the user everything
  meaningful, and a step (one round trip to Gemini) means nothing to them. **Revisit when:** steps get names worth
  showing (e.g. "Asking the receipt agent" with A2A agents).

### D114. Chip wording lives in the browser, and never overclaims
- `tool-chip.tsx` maps each tool to running / done / failed wording, falling back to the tool's name for new tools.
- A `delete_expense` without `confirmed: true` reads "Checking the expense…" → "Waiting for your OK", never "Deleting".
- If the run fails, chips still spinning turn into failures, so nothing keeps spinning forever.
- "Thinking…" shows only while nothing else shows progress: before the first event, or between finished tools and the
  start of the answer's text.
- **Superseded by D157:** the backend sends each chip's labels.

---

## Sources (after Phase 15)

### D115. Correction to D110's reason
- D110 said closing the text message before a tool call "keeps strict AG-UI clients happy". That was from memory, not
  a source. Checked against AG-UI's TypeScript event verifier ([sources.md](sources.md) §3), it's wrong: nothing there
  forbids tool events while a text message is open.
- **The behaviour stays:** each text message is then one continuous piece of the reply, and a client that shows messages
  separately places the tool call between them in the right order. SpendWise's panel joins them into one bubble anyway.
- **Lesson:** facts from docs, specs or library code now go in [sources.md](sources.md), with a link or file path. A
  reason that can't be traced to a source is written as an assumption.

---

## A2UI card (Phase 16)

> Checked offline: the models against valid and invalid cards, the card in the real `/agent` stream (fake Gemini, real
> MCP), and the web renderer by rendering the card plus hostile descriptions to HTML with React's server renderer.
> `npm run build` passes. Not yet seen in a browser or with real Gemini.

### D116. A2UI v1.0, a seven-component subset, as strict Pydantic models
- v1.0 is the current spec ([sources.md](sources.md) §8). `modules/assistant/a2ui/models.py` covers Text, Card, Row,
  Column, List, Button and Divider, plus the createSurface, updateComponents and deleteSurface messages. JSON keys are
  camelCase (aliases), as in the spec.
- **Strict like the spec's schema:** unknown fields are rejected; ids must look like identifiers (no hyphens); `component`
  picks the model (a discriminated union), so anything outside the catalog fails. `CreateSurface` also checks that there
  is a `root`, that ids are unique, and that every child reference exists.
- **Left out for now:** data bindings (`{"@path": ...}`), template child lists, `functionCall` actions, `updateDataModel`,
  and the components we don't use. `a2ui-core` on PyPI exists; we write our own models because the phase is about
  learning the format.
- **Updated by D121, D122:** three input components and data bindings were added in Phase 17.

### D117. A card is one `createSurface` message in one AG-UI `CUSTOM` event named `a2ui`
- The v1.0 schema lets `createSurface` carry its components, so one message describes a whole card. AG-UI has no A2UI
  event of its own, so it travels in `CUSTOM` (`value` = the A2UI message), as the phase asks.
- Cards are **built by code** (`a2ui/cards.py`) from the tool's actual result, not by the model. They're sent only for
  successful calls, right after the `TOOL_CALL_RESULT` (and any `STATE_SNAPSHOT`).
- The phase asked for `add_expense`'s card. On request, all five tools have one: saved, updated, delete preview /
  deleted, month summary, and found expenses (up to 10 rows).
- **The delete card never overclaims:** without confirmation it reads "Delete this expense?" and says nothing is deleted
  until you reply "yes" (D53, D114).
- **A new surface id per card** (`<kind>_<12 hex>`): the same expense can be updated twice in one chat, and the spec
  forbids creating a surface twice.
- Which tool gets which card is a table in `cards.py`, like the chip wording in the browser (D114). If a result can't be
  read, the card is skipped and logged; the reply still arrives. `/chat` sends no cards.
- **Updated by D128, D129:** the month summary is now an insight card, and the delete check card has Approve/Cancel.

### D118. The renderer: an allowlist mapped to our components, and nothing else
- `components/a2ui/a2ui-surface.tsx` maps each allowed component to our shadcn components: Card to `Card`, Divider to
  `Separator`, Button to `Button`, Row/Column/List to flex `div`s, and Text to a `span` styled as caption or body.
  Anything else renders a dashed "Can't show …" placeholder.
- **Never markup from the server:** text goes through React, which escapes it; nothing uses `innerHTML`. Text's "simple
  Markdown" isn't rendered yet. Server values only pick from fixed tables of class names (`Object.hasOwn`), so they can't
  inject classes.
- A List is `role="list"` with a `role="listitem"` around each child, for screen readers.
- **Defensive structure:** `lib/a2ui.ts` checks every message before using it and ignores other protocol versions.
  Components are kept in a `Map`, so an id like `__proto__` is just a key. Nesting stops at depth 12, so a component that
  contains itself can't loop forever.
- **Button** is drawn but disabled ("Not available yet") until a later phase sends actions back to the agent.
- **Updated by D124:** buttons work now, sending their action (Phase 17).

### D119. Correction to D99: `cn` is shadcn's npm package
- `web/package.json` has had `"cn": "^0.5.2"` since Phase 11 (shadcn init). Its own description: "Fast, small, compiled
  class-name merging for Tailwind CSS. Drop-in replacement for clsx + tailwind-merge". Its repository is
  `github.com/shadcn-ui/cn`. 19 of our shadcn components import it.
- So `resizable.tsx`'s `import { cn } from "cn"` was fine. Changing it to `@/lib/utils` did no harm, since both merge
  classes the same way. The shadcn components use the package, and our own code uses `@/lib/utils`. The troubleshooting
  entry now says to run `npm install`.

### D120. Expense ids are shown as `#14` everywhere
- **Why:** the assistant asked "let me know its ID", but the UI never showed ids. They now appear in the expense cards
  (top right), in every row of the list card, and as a sortable **ID** column in the Expenses table (read-only in the
  edit row).
- The system instruction tells the assistant that the app shows ids as `#14`, to include them when it mentions specific
  expenses, and that `#14` from the user means id 14.
- The **full** id is shown, not "the first 6 characters" (as first asked). Ids are whole numbers counting up from 1, so
  they're short, and cutting a number would point at the wrong expense once ids pass 999,999. **Revisit when:** ids
  become long random strings (e.g. UUIDs); then show a short prefix and make the server accept it.

---

## A2UI forms (Phase 17)

> Checked offline: a scripted fake Gemini with the real app and MCP server (valid model form, invalid form with
> fallback, a form submission saved, a forged action refused, `/chat` without forms), the renderer and data-model
> helpers via React's server renderer, and the web app's `runAgent()` doing the whole round trip. `npm run build`
> passes. Not yet tried in a browser or with real Gemini.

### D121. Three input components, as A2UI v1.0 defines them
- **TextField:** `label` and `value` are required; `variant` shortText, longText, number or obscured.
- **ChoicePicker:** the prompt said "Select", but v1.0's basic catalog has none. ChoicePicker is its dropdown, and its
  value is a list, `["Food"]`. Only one choice at a time (`mutuallyExclusive`); multi-select gets a placeholder.
- **DateTimeInput:** dates only. `enableDate: true` is required, because the spec's default is false; a time picker
  gets a placeholder.
- **Drawn with:** shadcn `Input` or `Textarea`, `Select`, and `Popover` + `Calendar`. `npx shadcn add popover
  calendar` also installed `react-day-picker` 10 and `date-fns` 4. "number" stays a text box with a decimal keypad, so
  amounts keep their exact digits.
- **Left out:** `@checks` validation rules, `displayStyle`, `filterable`, `min` / `max` (the strict models reject
  them).

### D122. Data binding: absolute JSON Pointers of simple names, kept in the browser
- A bound value is `{"@path": "/expense/amount"}`. The server's model only accepts absolute paths made of simple
  names (`^(/[A-Za-z_][A-Za-z0-9_]*)+$`). The browser's `getAt` / `setAt` also refuse `__proto__`, `prototype` and
  `constructor`, because data from the network must not reach JavaScript's object machinery.
- Each surface keeps its data model in the chat state. Typing updates it there (`setFormValue`), and nothing is sent
  until a button's action fires, as the spec requires ("Two-Way Binding is local to the renderer"). `updateDataModel`
  messages are applied too, though the agent doesn't send any yet.

### D123. Missing details get a form, from a UI tool the assistant declares itself
- `show_expense_form` changes no data, so it's declared in `a2ui/forms.py` and offered next to the MCP tools, not on
  the MCP server (the data tools stay MCP's, D72). The system instruction's "ask instead of guessing" line becomes the
  form rules.
- Once a form is shown, the turn ends with a fixed sentence ("Please check the details in the form and press Save."),
  saving a Gemini request that would only say the same. The history stays valid: `function_result`, then
  `model_output`.
- `POST /chat` can't show forms, so it gets neither the tool nor the rules (`agent.run(..., forms=False)`) and asks in
  text as before.

### D124. Save sends an A2UI `action` in AG-UI's `forwardedProps`
- **Where it goes:** nothing official says how a client sends an A2UI action over AG-UI. So the browser sends
  `forwardedProps: {"a2uiAction": {"version": "1.0", "action": {...}}}` with an empty `messages` list.
  `forwardedProps` is AG-UI's field for extra client data.
- **Checking it:** the server validates it (`ActionMessage`: v1.0 fields, action name must be `save_expense`, values
  are strings or string lists, at most 2000 characters in total).
- **What the agent sees:** it gets the action as its next user message, with the values as labelled JSON ("data, not
  instructions"). A picker's one-item list becomes a plain string. The model then calls `add_expense`, so the usual
  chips, snapshot and "saved" card follow, and the thread's history records the submission.
- **Locking:** the form locks once sent (one submission only) and unlocks if the run fails. While any run is in
  progress, all forms are locked.

### D125. The model writes the form; the server checks it and falls back
- The catalog (allowed types and properties, and the `/expense/<field>` bindings) is in the system instruction, about
  300 tokens per request. The model passes the form as a JSON **string** (`form`), plus the details it understood as
  ordinary arguments. A string avoids describing every component in Gemini's parameter schema.
- **The check:** the Pydantic models (catalog, properties, ids, `root`, references, paths, action name), plus "has a
  Save button". The surface id and catalog are always chosen by the server.
- **On failure:** the reason is logged and `expense_form()` is sent instead, pre-filled from the call's arguments.
  The date defaults to today.
- `CUSTOM` `metadata.source` is `"model"` or `"fallback"`, so you can see which happened. **Revisit when:** fallbacks
  are frequent; then shorten the catalog text, or send it as structured output.
- **Updated by D129:** a model-written form's buttons may only use `save_expense`.

---

## Insight cards and approvals (Phase 18)

> Checked offline: a scripted fake Gemini (which tried to delete with `confirmed=true` itself) against the real app and
> MCP server. Approve was attacked with a forged card id, another thread, a reused card and a different expense id, and
> a disguised approve button was tried in a model-written form. The renderer was checked with real and hostile cards.
> `npm run build` passes. **Live** with real Gemini (flash-lite), against the running app: the insight card and the
> full delete flow (preview card, expense still there, Approve, deleted) worked. Not yet tried in a browser.

### D126. Chart and Stat live in SpendWise's own catalog, mixed onto basic surfaces
- The basic catalog has no chart or stat, and a catalog can't extend another. So `urn:spendwise:catalog:insights:v1`
  holds Chart and Stat, and each such component carries `"@catalogId"`. Surfaces keep the basic catalog as their
  default.
- The renderer resolves each component's catalog (its own `@catalogId`, then the surface's; the spec's order) and
  draws only these two catalogs. Anything else gets "a catalog this app doesn't know".
- The id is a URN: the spec says it's a name, not a resolvable address. No `catalog_definition.json` is published; the
  Pydantic models are the definition. **Revisit when:** another client needs our catalog; then publish a definition
  file.

### D127. Charts are data and labels only, drawn with a fixed config
- **Chart:** `chartType` (bar, line or donut), `data` of 1 to 24 `{label, value}` points with finite numbers, optional
  `unit` (at most 4 characters). **Stat:** `label`, `value`, optional `change` and `trend` (up, down or flat).
- shadcn's `ChartStyle` writes the config's keys and colours into a `<style>` tag (`dangerouslySetInnerHTML`). So the
  config is fixed (`value` and `--chart-1`), and donut slices use the theme's five chart colours. Agent labels only
  ever appear as chart text.
- The donut has a legend list with every value, which is also its text version for screen readers. Stat arrows show
  direction without red or green, since whether "up" is good depends on what's measured.

### D128. "Where did my money go?" is the month summary, now as an insight card
- `get_summary` also returns `previous_month` (month, total, count). It's added alongside the old fields, so existing
  clients don't break.
- Its card is now the insight card: Stats "Spent in <month>" ("+12% vs October", "Same as …", or "Nothing spent in …")
  and "Biggest category" (amount · share), plus a donut of the top 4 categories and "Everything else" (5 slices, 5
  colours). This replaces Phase 16's list-style summary card (D117).
- With the web panel, the instruction asks for a reply of a sentence or two when a card shows the details.

### D129. Deleting is human-in-the-loop, enforced by the server
- **The guard:** with the web panel (`rich_ui`), `approvals.guard()` runs every delete the model asks for as a preview
  (`confirmed=false`), and the instruction tells the model it can't delete.
- **The card:** a delete preview card has Approve and Cancel (`approve_delete` / `cancel_delete`, with `userMessage`).
  When it's sent, the server records `(thread id, surface id) -> expense id`.
- **The decision:** Approve or Cancel goes to `agent.approval_turn()`, with no model involved. Approve deletes the
  **recorded** expense through MCP, so the browser's `expense_id` is ignored. Each record is used once (`take()`)
  and only in its own thread.
- **The history:** the turn is stored as plain text ("I pressed Approve…", "Done…"), so later messages know what
  happened.
- **Closing the gaps:** a model-written form can't contain approval buttons (D125). The records are kept in memory
  only, so a restart forgets them and the user asks again.
- `POST /chat` (no buttons) keeps D53's text confirmation.
- **Updated by D133:** the code review found the guard could be bypassed (`confirmed: "true"`); approvals now also keep
  a snapshot, expire, and survive a failed run.
- **Revisit when:** there's more than one server process; then store the records in the database.
- **Updated by D146:** the records are in the database now (`pending_approval`).

### D130. Which actions need approval
- **Only deleting:** it can't be undone.
- **No approval needed:** reads change nothing; adds and updates are visible (chips, cards, the page refresh) and
  reversible.
- Asking for approval too often trains people to click without reading. **Revisit when:** bulk changes, payments,
  messages to other people, or anything outside the app arrive.
- The delete *preview* still sends a `STATE_SNAPSHOT` (D111's known trade-off: the pages reload once for nothing).
  **Updated by D133:** it no longer does.

### D131. Smaller fixes in Phase 18
- **Button messages:** a button's `userMessage` ("Approve deleting #14") is what your chat bubble shows for the click.
- **Whole numbers:** action contexts list `int` before `float`, so an id stays `3` (it came out as `3.0`).
- **The agent's switch:** `agent.stream`'s `forms` became `rich_ui`, because it now covers forms, cards and approval
  buttons.

---

## Code review of every area (after Phase 18)

> `/code-review` was run on Phase 18, then on today's code area by area: backend foundation (Phases 1–8), MCP (9–10),
> assistant (6–18) and the web app (11–18). 57 findings, many overlapping. The fixes were checked offline:
> - **Attacks:** the Phase 18 attack script again, plus the string `"true"` bypass and an edit between card and Approve.
> - **MCP tools** through the real protocol, and **REST** validation over HTTP.
> - **Logging** after start-up.
> - **The renderer** against runaway descriptions, and real cards.
>
> `npm run build` passes.

### D132. Every phase ends with a code review
- After a phase is built and checked, its changes get a code review. What holds up is fixed and re-checked, and the
  summary says what was fixed and what was deliberately not, before the user is asked to commit.
- **Why:** the first review after Phase 18 found a real hole in that phase's safety guarantee (D133).

### D133. Approvals, hardened
- **The bypass:** the guard only caught `confirmed is True`, but the MCP tool also read `"true"`, `"yes"` or `1` as true.
  Now:
  - the guard sends `confirmed=False` for **any** delete in the web panel;
  - the model is offered `delete_expense` **without** `confirmed` at all, with a description saying only Approve
    deletes;
  - the MCP tool's `confirmed` is `strict`, so `"yes"` and `1` are errors.
- **A snapshot, not an id:** a card's record is the expense as the card showed it. Approve first re-reads the expense
  and refuses if it changed or is gone. An edit, or an id reused after a delete, can't redirect Approve.
- **Expiry and failures:**
  - records expire after 15 minutes, and at most 200 are kept;
  - if a run fails before finishing, the record is put back (`restore()`), so Approve works again when the browser
    unlocks the card;
  - a failed delete says nothing was deleted and asks the user to ask again.
- **Previews and the model:** a guarded preview no longer counts as a data change (no needless reload). The model's
  copy of the preview result says nothing was deleted and the user now sees Approve/Cancel, so it doesn't retry.
- Approval stays delete-only, keyed on the tool's name, not on every `destructive_hint` tool: the preview/confirm
  protocol exists only for delete, and updates are reversible (D130).
- **Updated by D145, D146:** previews are `get_expense` lookups; records are stored in the database.

### D134. MCP tool inputs
- **Empty means not given:** optional text arguments are plain `str`, with `""` meaning "not given". Models fill unused
  strings with `""`, and the SDK pre-parses non-`str` arguments as JSON (`"null"` became `None`). `list_expenses("")`
  works now; `update_expense(note="null")` keeps the text.
- **`add_expense` and `update_expense`:**
  - `amount` also accepts a number;
  - `update_expense` gains `currency` and `clear_note`, and refuses a call that changes nothing (it used to report
    "updated");
  - every currency must match `^[A-Z]{3}$`, as in REST (a lowercase `inr` gave a silent 0 total);
  - ids are bounded.
- **Inside the tools:**
  - categories are loaded once per call, and names are trimmed; an empty table gets a clear message;
  - `get_summary`'s previous month comes from `monthly_trend` (no second month calculation);
  - the recent-expenses resource stops after 20 rows in SQL;
  - tool errors pass on only `ValidationError` and our own errors, and a locked database says "try again".

### D135. REST inputs
- **Expense bodies:** `ExpenseCreate` and `ExpenseUpdate` reject unknown fields (a typo'd PATCH was a silent 200) and
  strip spaces (`"Swiggy "` never matched a filter; `"   "` saved a blank merchant).
- **Filters:** `merchant=` (empty) is a 422, like `search=`.
- **Ids and months:**
  - ids are capped at SQLite's largest integer (above it was a 500 from the driver);
  - months must be 1900–2099 (`0000-01` was a 500).
- **Categories:** a new one can't duplicate an existing name in another letter case or with spaces. The database's
  unique constraint is still case-sensitive (no migrations, D18), so the check is in the service.
- **Merchant filter:** the database lowercases both sides. SQLite only lowercases A–Z, so "CAFÉ" matches "CAFÉ" but
  not "café". Fine for now. **Revisit when:** non-English merchant names are common; then fold case in Python.

### D136. Smaller backend fixes
- **Logging:** `setup_logging()` uses `force=True`. Creating the MCP server had already set up root logging at INFO,
  which made our setup a no-op and let every httpx request print.
- **`MCP_URL`:** the default is `http://127.0.0.1:8000/mcp/`. `/mcp` answered with a 307 redirect first, and
  `localhost` tried IPv6 before IPv4, which cost extra round trips on every MCP call.
- **Model checks:**
  - chart labels allow 50 characters, like category names;
  - Stat texts and button messages are capped;
  - `CreateSurface` rejects a component that contains itself;
  - a model-written form may only use the form components.
- **Cards:**
  - `card_for` also catches `ArithmeticError` (a bad Decimal);
  - an empty month says "No expenses in <month>";
  - small changes keep a decimal ("+0.4%", not "Same as");
  - `approval_needed` uses the same test as the card and the shared constants;
  - `monthly_summary` reuses `_months_back`.

### D137. Web fixes
- **Saving forms:** a form unlocks after a failed run only if nothing changed on the server. If the save went through
  and a later step failed, pressing Save again would save twice.
- **Runaway cards:** before drawing, a surface is measured, counting shared children each time. Over 300 components,
  or one that contains itself, becomes one "Can't show" note. A loop, or 3 copies of a child 12 levels deep, could
  freeze the tab.
- **Broken connections:** a tool interrupted by a lost connection shows "Expense saved?" (not confirmed) instead of
  "failed", and the pages reload.
- **Updates to older cards:** A2UI updates aimed at a card from an earlier reply reach it.
- **Expenses page edit row:** it compares with a snapshot taken when editing started, so a reload mid-edit can't undo
  someone else's change, and repeated Enter saves once.
- **Small fixes:**
  - the Dashboard clears an old error after a successful reload;
  - the chat scrolls on new content, not on every keystroke in a form;
  - Enter while an input method is composing doesn't send;
  - `useIsMobile` starts with the real answer (no double mount on phones);
  - "1 expense" is singular;
  - chart amounts use the server's style;
  - date helpers are shared (`lib/format.ts`).

### D138. Findings deliberately not fixed
- **The seed's "already seeded" check after a crash midway:** it's a dev tool, and the fix is to delete the database
  and seed again (troubleshooting).
- **The same computed `total` in three schemas:** cosmetic.
- **`mcp_stdio.py` setting up tables and logging on import:** it's a dev entry point, and creating tables is harmless
  to repeat.
- **`list_expenses` loading every matching row to count them:** fine at one person's scale. **Revisit when:** lists
  are paginated.
- **Two runs on one thread at once storing the same turn number:** the panel sends one message at a time. **Revisit
  when:** the same thread can be used from two devices.
- **No Stop button or client timeout for a run:** every server step is time-limited (Gemini 60 s × 2, MCP 15 s).
  **Revisit when:** adding a Stop button.
- **Every bubble re-rendering on each streamed token:** fine at chat sizes. **Revisit when:** long chats feel slow;
  then memoize the bubbles.
- **The same one-line error-to-text conversion in three places:** not worth a shared helper yet.
- **Updated by D158, D139, D140, D149:** the Stop button, the shared error helper, the `total` duplication, `mcp_stdio.py`'s import side effects and list counting were addressed in the refactor.

---

## Architecture refactor: CQRS and feature slices (after Phase 18)

> An architecture review of the whole codebase (no magic strings, no duplication, a strict modular monolith with CQRS,
> feature slices in the web app, no tight coupling) found about 40 issues; all are addressed below except D161.
> Checked offline:
> - the migrations on a copy of the real database (up, down, up; the chat history converts losslessly both ways);
> - REST, problem details, `/health` and `/mcp/` (token, Host and Origin checks) over HTTP;
> - every agent flow with a scripted fake model (insight card, delete with Approve/Cancel, a stale or foreign card, an
>   edit before Approve, the form, `/chat` deletes);
> - the in-process and remote tool adapters;
> - the real web modules through Vite's SSR loader against that backend (API calls, the validated stream, cards,
>   both pages with TanStack Query data).
>
> `npm run build` and `npx oxlint` pass. See [phases/refactor-architecture.md](phases/refactor-architecture.md).

### D139. Commands and queries (CQRS-lite), run by one bus that is also the unit of work
- Every module's business operations are **commands** (change data, return at most an id) or **queries** (read,
  change nothing): small frozen Pydantic models with one handler each, in `commands.py` and `queries.py`.
- Callers send them through `MessageBus` (`core/cqrs.py`): `bus.execute(CreateExpense(...))`, `bus.ask(GetExpense(...))`.
- The bus opens one session per outermost message and **commits only after a command's handler returns** (rolls back
  if it raises). Messages sent from inside a handler (`ctx.bus`) share that session, so a command and its checks are
  one transaction. Repositories only stage changes; `bus.unit_of_work()` groups several commands (the seed).
- A query can't send a command (refused at runtime).
- Same database for reads and writes: full CQRS (separate read models, event sourcing) would be overkill here.
- **Why:** one `service.py` per module mixed reads and writes, and repositories committed on their own, so two writes
  couldn't be one transaction.
- **Revisit when:** reads and writes need different storage, or a handler needs to run after another commits (events).

### D140. Modules plug in through `module.py`; `bootstrap.py` is the composition root
- Each module has `module.py` (handlers, routes, tables) for the composition root, and `__init__.py` (its contract)
  for other modules. `app/bootstrap.py` holds the one list of modules; `main.py`, `seed.py`, `mcp_stdio.py` and the
  migrations all build from it. Nothing registers itself just by being imported.
- Shared services reach routes through FastAPI dependencies (`BusDep`, `ClockDep`), not globals.
- **Why:** tables used to register as a side effect of importing routers, and the module list was implied.

### D141. Conversations are their own module, stored as provider-neutral messages
- `modules/conversations` owns the chat history (`conversation_message`, renamed from `chatmessage`) with
  `AppendTurn`, `GetLastTurn`, `GetHistory`, `GetThread`, and `GET /threads/{id}`.
- Messages are SpendWise's own types (`core/llm/messages.py`): `UserText`, `AssistantText`, `ToolCall`, `ToolResult`,
  `Reasoning`. A provider's private reasoning (Gemini's thought signature) is kept as opaque data for that provider.
- Migration 0002 converted the stored history; converting it back gives the original rows exactly.
- **Why:** the history was stored in Gemini's wire format, so changing provider meant migrating every conversation.

### D142. The LLM is a port; Gemini is one adapter
- `core/llm/__init__.py` is the port (`stream_with_tools`, `ask_for_json`, `LlmError`, the message types);
  `core/llm/gemini.py` is the only code that knows Gemini's steps, events and schema subset. Its wire names are enums.
- `ask_gemini()` went with `/ask` (D150).
- **Updated by D166:** the port is a `LanguageModel` protocol, injected from `bootstrap.py`.

### D143. The assistant's tools are a port; this app's MCP server is called in-process by default
- The agent only knows `ExpenseTools` (`assistant/tools.py`). `McpExpenseTools` implements it with the MCP SDK's
  `Client`, which connects to an `MCPServer` **object in-process**, or to a URL.
- `MCP_URL` is unset by default: no HTTP request to our own port, no handshake per call. Set it only when the tools
  run as a separate service (then `MCP_TOKEN` is sent as a bearer token).
- The tools still go through MCP, so the agent stays decoupled from the expenses module (D72).
- **Why:** calling ourselves over HTTP was what forced sync routes and a connection per tool call.

### D144. MCP tools return typed results; the contract lives in the mcp module
- Each tool returns a Pydantic model (`ExpenseSaved`, `ExpenseSearch`, `MonthSpending`, ...). The SDK publishes it as
  the tool's `outputSchema` and sends `structuredContent`; cards validate it with the same models.
- Tool names, resource URIs and argument names are enums or constants in `mcp/contracts.py`, exported by the module.
- **Why:** the cards read the result by dictionary key from a JSON string, so renaming a field silently removed cards.

### D145. Previews are queries; `delete_expense` needs a strict `confirmed=true`
- New read-only tool `get_expense`. `delete_expense` only deletes.
- It requires `confirmed`, strictly `true`; anything else is an error and deletes nothing.
- **Why:** a delete with a "preview" switch was a query and a command in one. The SDK ignores arguments a tool doesn't
  declare, so without the required interlock a client still sending the old `confirmed=false` ("just show me") would
  have deleted for real.
- In the web panel the model never runs a delete: its `delete_expense` call becomes a `get_expense` lookup and an
  Approve/Cancel card, and the model isn't shown `confirmed` (D146). `/chat` keeps the text confirmation.
- **Updated by D162:** `delete_expense` also takes `expected_version`; Approve uses it.

### D146. Approvals are stored in the database
- `pending_approval` (assistant module): the card's id (its surface id), the thread, the expense snapshot, the time.
  Commands `RequestApproval` and `TakeApproval`; expiry (15 minutes) and the cap (200) are enforced in SQL.
- The rules of D129/D133 are unchanged: each card decides once, in its own thread; Approve deletes only if the
  expense still matches the snapshot; a run that fails puts the card back.
- **Why:** in memory, a second server process (or a restart) lost the cards.
- **Updated by D164:** a decision completes before streaming; a restored card keeps its age.

### D147. AG-UI and A2UI are adapters; the use cases yield plain events
- `turns.py` holds the use cases (`Assistant.run_turn`, `decide`, `chat`); the agent yields `AgentEvent`s
  (`TextDelta`, `ToolStarted`, `ToolFinished`, `ApprovalRequested`, `FormRequested`, `TurnFinished`).
- `agui.py` turns them into AG-UI events, reads `forwardedProps`, and adds cards; `api.py` serves HTTP.
- The names on the wire beyond AG-UI's own are in `assistant/protocol.py`.
- **Why:** the service built AG-UI events itself, mixing a transport protocol into the use cases.

### D148. Migrations with Alembic
- `backend/alembic.ini` and `backend/migrations`. 0001 is the schema as it was, created only where missing, so existing
  databases keep their data; 0002 is D141 + D146. SQLite changes run in "batch" mode.
- `.\run.ps1` runs `alembic upgrade head` before starting; the app **refuses to start** on an out-of-date database and
  says how to fix it. `seed.py` and `mcp_stdio.py` upgrade first.
- A migration doesn't import app code: it must keep doing exactly what it did after the code changes.
- **Why:** `create_all` never changes an existing table, so any schema change meant deleting the database.
- **Updated by D163:** migrations run in one transaction, schema changes included, on SQLite too.

### D149. Errors are RFC 9457 problem details; the API lives under `/api/v1`
- Every error, including validation errors and FastAPI's own 404/405, is `application/problem+json` with `type`
  (a `urn:spendwise:problem:...` name), `title`, `status`, `detail`, `instance`; validation adds `errors`.
- REST routes moved under `/api/v1`. `/health` (now also checks the database) and `/mcp/` stay at the root.
- `POST /expenses` answers 201 with a `Location` header; `GET /expenses` returns `{items, total}` with `limit` (default
  100, max 500) and `offset`.
- **Why:** errors had two shapes, and a breaking API change had nowhere to go.
- **Updated by D165:** unexpected 500s carry CORS headers; FastAPI's own errors keep their headers.

### D150. MCP over HTTP only with `MCP_TOKEN`; `/ask` removed
- `/mcp/` is mounted only when `MCP_TOKEN` is set, and then answers only `Authorization: Bearer <token>` (compared in
  constant time). The SDK's DNS-rebinding protection (Host and Origin checks for a server on 127.0.0.1) stays on.
- `POST /ask` sent any prompt to Gemini: an open proxy to your quota, with no product use. Removed.
- **Revisit when:** users exist (the planned auth phase); then the REST API and the web app get real login.

### D151. A Clock instead of `date.today()`
- `core/clock.py`: routes get it as `ClockDep`, handlers as `ctx.clock`. Created-at times come from it too.
- **Why:** "today" was read in four places, always the server's local date, and impossible to pin.

### D152. Message text and tool arguments are logged only at DEBUG
- INFO lines say what happened (a message of N characters, a tool name, ok or error, token counts).
- **Why:** they're one person's financial data, and INFO logs are the ones kept and shipped around.

### D153. The web app is organised as feature slices, enforced by lint
- `src/features/<name>/` (expenses, categories, dashboard, assistant) each own their components, hooks, API calls,
  types and constants, and export through `index.ts`. `src/shared/` (ui kit, HTTP client, config, formatting, theme,
  error boundary) knows no feature; `src/app/` (providers, routes, layout) composes them.
- `.oxlintrc.json` (`no-restricted-imports`): no deep imports into another feature, no relative import out of a
  feature, nothing from `app/` in a feature, nothing from features or `app/` in `shared/`.
- Not Feature-Sliced Design's layers: plain feature folders, by choice.
- **Why:** files were grouped by kind (`components/`, `hooks/`, `lib/`, `pages/`), and one `api.ts` held everything.

### D154. Server data through TanStack Query; the assistant says "data changed", the app decides what reloads
- Each feature has query keys and hooks (`useExpenses`, `useMonthlySummary`, `useCategories`, mutations that
  invalidate their keys). Requests get an `AbortSignal`; outdated ones are cancelled.
- `AssistantProvider` takes `onDataChanged`; `app/providers.tsx` wires it to invalidate the expenses and Dashboard
  queries. The assistant doesn't know which pages exist.
- **Why:** pages fetched in effects by hand, and every page had to remember to watch a shared `dataVersion`.

### D155. One contract, generated from the backend
- `npm run gen:api` turns `web/openapi.json` into `src/shared/api/schema.gen.ts` (openapi-typescript), and the
  client is openapi-fetch: a request or response that doesn't match the API is a compile error.
- `backend/scripts/export_contracts.py` writes `openapi.json` and `src/shared/api/contracts.gen.ts`: the A2UI
  catalogs and actions, AG-UI names and keys, payment-method labels, limits, "Unknown".
- **Why:** types, labels and protocol names were copied by hand into TypeScript.

### D156. AG-UI events are validated with `@ag-ui/core`'s schemas
- The stream client is still our own `fetch()` reader (D107), but every event goes through
  `EventSchemas.safeParse()` and the code uses AG-UI's `EventType` enum and types.
- **Why:** events were trusted with a type cast.

### D157. Chip labels come from the backend
- `TOOL_CALL_START` carries `metadata.labels` (running/done/failed). An approval check has its own labels.
- **Why:** the browser knew MCP tool names and the delete tool's arguments.

### D158. Error boundaries, Stop, and abortable requests
- An error boundary around each A2UI card and around the page area: a crash shows a note, not a blank app.
- The chat has a **Stop** button (aborts the stream); a tool cut off by it shows "?" and the pages reload.

### D159. Money looks the same everywhere
- `₹1,25,000.50` (Indian grouping, two decimals) in cards, charts and pages: `core.money.format_money` on the server,
  `formatMoney` in the browser, same rule.

### D160. Web dependencies pinned exactly; openapi-typescript runs through `npx`
- `package.json` lists exact versions, like `requirements.txt` (D2).
- openapi-typescript 7.13 wants TypeScript 5 and the app uses 7, so `gen:api` runs it pinned through `npx`, in its
  own install.

### D161. Not done on purpose
- **Login for the REST API and the web app:** a feature, not a refactor; planned with users (auth phase).
- **Two runs on one thread at once** (D138) and **re-rendering bubbles** (D138): unchanged.
- **Splitting the bundle by page:** the assistant (always loaded) already pulls in the chart library.

---

## Code reviews of the refactor

> Two independent reviews (backend, web) read the refactored code and reproduced findings with scratch scripts:
> 11 backend bugs and 6 standards issues, 9 web bugs and 10 standards issues. All are resolved below except where
> noted (D170). Full list: [architecture-review.md](architecture-review.md). Checked again offline: migrations (including
> a failing one left untouched), the bus, REST and problem responses, MCP over HTTP, every agent flow with a fake model,
> and the web modules against that backend; `tsc -b`, `oxlint` and `npm run build` clean.

### D162. Optimistic concurrency for expenses
- `expense.version` starts at 1 and every update raises it (migration 0003). `DeleteExpense` (and the MCP tool) take an
  optional `expected_version`: `DELETE … WHERE id = ? AND version = ?`, so the check and the delete are one statement.
- Approve passes the version the card showed. The snapshot comparison before it stays, for a clear message; the
  version is the guarantee.
- **Why:** the review found that an edit landing between Approve's check and the delete would be deleted unseen. A
  version column is the standard fix: no lock is held while the user decides.

### D163. SQLite made transactional: atomic migrations, savepoints
- `core/db.py` applies SQLAlchemy's documented recipe for pysqlite (the driver's own transaction handling off, an
  explicit `BEGIN`), so schema changes are transactional and SAVEPOINTs work. Migrations run with
  `transactional_ddl=True`: an `upgrade` either completes or leaves the database exactly as it was.
- A command sent from inside another runs in a SAVEPOINT (`begin_nested`): if it fails and the caller carries on, only
  its own changes are undone.
- **Why:** a failing 0002 left the table renamed but unconverted, and every later upgrade failed.

### D164. No database session around slow work; approvals decided eagerly
- `/parse` is a use case, not a query handler: it reads the categories (a short query), then calls the model with no
  session open. A query handler holding a pooled connection for up to two minutes could starve the pool.
- `Assistant.decide` completes the whole decision (take the card, check, delete, save the turn) before streaming the
  result. On a failure the card goes back at once (`RestoreApproval`), keeping its original time, so it still
  expires on schedule.
- **Why:** the put-back used to run when the stream's generator was garbage-collected (after a disconnect): at an
  unpredictable time, on the event loop.

### D165. Errors, at the edges
- Unexpected errors are turned into a 500 problem by a middleware **inside** CORS, so the browser can read it.
- FastAPI's own errors keep their headers (`Allow` on a 405).
- The MCP bearer scheme is matched case-insensitively (RFC 9110).
- Only SQLite lock errors are reported to MCP clients as "busy"; other database errors aren't disguised.

### D166. The LLM port is injected; the mcp package is its contract
- `core/llm/port.py`: `LanguageModel` and `LlmStream` protocols and `LlmError`. `GeminiModel` (`gemini.py`) implements
  it; `bootstrap.build()` creates it and hands it to the assistant. Nothing else imports the provider.
- `app.modules.mcp` exports only the tool contract; the server and its HTTP endpoint come from `mcp/module.py`, used by
  the composition root alone. Importing the contract loads no server code.
- Approvals store the assistant's own `ExpenseSnapshot`, not the MCP contract's `ExpenseView`, so stored rows don't
  break if that contract changes.
- Tool descriptions are built from the contract's names, and the server checks its tools' parameters at start-up.
- **Updated by D172:** the port is split by use (`StructuredOutputModel`, `ToolCallingModel`); `LanguageModel` is both.

### D167. `/agent` checks its input before streaming
- A FastAPI dependency (`agui.read_request`) validates the thread id, the message or the button click: problems are a
  422 problem response. The stream starts only with a valid run.

### D168. Web: one refresh rule; data kept when a refresh fails; boundaries everywhere
- Mutations declare `meta: { changes: DATA_SCOPES.expenses }`; `app/query-client.ts` has the one rule
  (`refreshExpenseData`) for mutations and the assistant alike.
- A page shows an error card only when nothing has loaded; if a reload fails, the data stays with a "couldn't refresh"
  notice, and Retry refetches only what failed.
- A form stays locked after a broken run if the server **may** have changed data (a tool was still running).
- Error boundaries at the root and around the chat panel, as well as the page area and each card.
- **Updated by D172:** the refresh rule is a `STALE_AFTER` table applied by `refreshAfter`.

### D169. Web: shared values from one place
- The A2UI component names, chart types, trends and limits come from the generated contract; the basic catalog's own
  vocabulary is named once (`basic-catalog.ts`).
- The app's name (`APP_NAME`), every page (`PAGES`, for both the router and the sidebar), and the theme boot script
  (generated from `theme-constants.ts` and injected into `index.html` by Vite) are each defined once.
- oxlint gains the jsx-a11y plugin and rules for `app/` and for relative imports out of `shared/`.

### D170. Not changed on purpose
- **Text after a tool call** already starts with a paragraph break (the agent adds it), so the reviewer's "joined text"
  isn't a bug.
- **`TakeApproval` returns data:** reading and removing a card must be one step, or two clicks could both get it.
- **A 405's `Allow` lists one method:** Starlette's per-method routes; the header now reaches the client.
- **The `dark` class in `index.css`:** Tailwind's variant is CSS and can't import the constant.

---

## Inline documentation

### D171. Every file, function and rule explained in the code
- **What:** every backend and web file starts with a header (a module docstring; a `//` block) saying what it's for,
  where it sits in the architecture and who uses it. Every function, method, class, component and hook says what it's
  for, what it returns and raises, and the rule it enforces; business rules are explained where they're applied. Web
  exports use `/** */` comments, so editors show them on hover.
- **Except docstrings that are data.** Pydantic copies a model's or enum's docstring into its JSON schema; FastAPI uses
  a route function's docstring as its OpenAPI description; the MCP SDK reads tool functions. So those get `#` comments
  above them instead. Changing one would change the OpenAPI document (and the generated web contract), the MCP tools'
  schemas, or, for `ParsedExpense`, the schema Gemini answers `/parse` in: a behaviour change, not a comment.
- **Why:** an engineer new to the code (or anyone, months later) shouldn't have to reverse-engineer what a file is
  for or why a rule exists; and documented exports show up in editors on hover.
- **How it was checked:** a script compared every file before and after with comments and docstrings removed (Python
  through its syntax tree, TypeScript with comments and whitespace stripped): no code changed. It also compared what
  Gemini is shown (system instructions, tool declarations, the `/parse` schema), what MCP clients see, and the OpenAPI
  document: all unchanged.
- **Revisit:** if the API documentation should carry descriptions, change model docstrings deliberately, regenerate
  the web contract, and for anything the model reads, try it against Gemini first.

---

## SOLID, testability and scalability

> Two reviews (backend, web) against single responsibility and the other SOLID principles, clean code, god files,
> testability and scalability found nine issues each. All were fixed, or documented as known limits (D174). The
> backend was verified by recording its behaviour through the HTTP API, with a fake model at the model port, before and
> after: identical. Details: [phases/refactor-solid.md](phases/refactor-solid.md) and
> [architecture-review.md](architecture-review.md#5-the-solid-review).

### D172. Small units with one job, extended through tables and protocols
- **What:**
  - The assistant's loop no longer switches on a `rich_ui` flag. A `Surface` (`WebPanel`, `TextChat`) carries what
    differs: prompt rules, offered tools, the calls it handles itself.
  - The prompt, running a tool and Approve/Cancel are separate files, and so are reading and writing AG-UI.
  - The MCP server registers its tools from `TOOL_REGISTRARS`, so a new tool is a registrar plus one entry.
  - The Gemini adapter keeps SDK calls apart from pure wire translation.
  - The model port is split by use: `StructuredOutputModel` and `ToolCallingModel`; `LanguageModel` is both.
  - Web: the chat hook's logic became pure functions; the A2UI renderer looks components up in `CATALOGS`; the expenses
    table, its editor and the forms were split; the refresh rule is a `STALE_AFTER` table the compiler checks.
  - Size targets: backend files under about 180 lines of code and functions under 50. Web files under about 150 and
    components or hooks under 60.
- **Why:** each of those files changed for several reasons, so every change risked the others. Switch statements and
  flags meant editing shared code for every new tool, card or client.
- **Revisit:** if a table grows entries that need special cases, that's a sign the abstraction is wrong. Split the
  table rather than adding branches to it.

### D173. Testability through seams, verified by recorded behaviour
- **What:**
  - `bootstrap.build(clock, llm, tools, engine)` builds the app around any of them.
  - `main.create_app(services)` serves the result.
  - `core.db.create_db_engine(url)` builds an engine without touching the default one.
  - Use cases take their ports in their constructors.
  - `GeminiModel(api_key, model, client_factory)` reads no global settings.
  - Tables no longer stamp their own timestamps: time comes only from the injected clock.
  - `migrations.upgrade_to_latest(engine)` migrates any engine; an in-memory SQLite engine shares one connection.
  - Nothing is built at import: uvicorn calls `create_app` (`--factory`), and the id rules moved to `core/ids.py`,
    so importing a contract doesn't create the database engine.
- **How refactors are checked until tests exist:** a fake model at the port and fixed scenarios through the real HTTP
  API, on a copy of the database. Every event, response and model call is recorded, and before and after must be
  identical.
- **Why:** a seam that needs monkeypatching is a hidden dependency. With these, a test (when the owner adds them) or a
  local run with a scripted model needs no special code.

### D174. Scalability: what was done, what is known
- **Done:**
  - `conversation_message` is indexed on (thread_id, turn) (migration 0004), and the redundant thread_id index is
    dropped.
  - The `/parse` schema is built once and copied per request, not rebuilt each time.
  - MCP's `get_expense` looks up one category, not all of them.
  - The web app loads each page, the chat panel and the chart library on demand (`lazyWithRetry`, which also makes a
    failed load retryable). The JavaScript loaded at start fell from 1,252 kB to 541 kB.
  - Typing in the chat no longer redraws every card.
  - Concurrent row saves each get their own state and toast.
  - A turn whose tool already ran can't fail afterwards because the tool list couldn't be fetched (with a remote
    MCP server right after a restart): the app assumes the tool may have changed data, as MCP says to.
- **Known limits, written down instead of fixed now:**
  - Worker threads (40) and database connections (5 + 10) are separate pools.
  - SQLite's deferred `BEGIN` can make two read-then-write commands fail together with "database locked". Fix with
    `BEGIN IMMEDIATE` and WAL, or Postgres.
  - `GET /threads/{id}` isn't paged.
  - Remote MCP opens a session per call (D74).
  - Details: [architecture.md](architecture.md#scalability).
- **Revisit:** when more than one person or process uses one database, start with the SQLite writer limit.
