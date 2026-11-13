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

### D13. No database foreign keys between modules
- **Why:** a foreign key would tie two modules' tables together at the database level. Ids are checked
  through the other module's public service instead (`categories.get_category()`).
- **Trade-off:** the database no longer guards the link, so the service must.

### D14. Services return frozen DTOs, never table rows
- **Why:** callers get a read-only copy, so they can't change or lazy-load another module's data through it.

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

### D28. Service errors become HTTP responses in one place
- **What:** services raise `NotFoundError` or `BusinessRuleError` (`core/errors.py`). `main.py` registers
  handlers that turn them into 404 / 422 with `{"detail": "<message>"}`.
- **Why:** services stay free of HTTP (so MCP tools can reuse them), and routers need no try/except.
- **Revisit when:** a third kind of error appears, or to move `/ask`'s Gemini → 502 mapping here too.
- **Updated by D48:** a third kind was added (`ExternalServiceError` → 502).

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

### D54. `/chat` is single-turn for now
- Each message starts a new conversation, so a follow-up must repeat the details.
- **Revisit when:** chat threads are added (assistant module, later phase).
- **Superseded by D58–D61** (Phase 8: threads and memory).

### D55. The agent uses `thinking_level="low"`
- **Why:** in live tests, a delete request spent 40–60+ s per step thinking and timed out. With `low` it took 9 s in total.
  Bookkeeping tasks don't need deep reasoning.
- **Where:** `agent.THINKING_LEVEL`, passed through `llm.ask_gemini_with_tools(..., thinking_level)` as
  `generation_config={"thinking_level": ...}`.

### D56. Gemini attempts time out after 60 s (was 30 s)
- A function-calling step can take 20–30 s. With 2 attempts, a total outage still ends in a 502 within about 2 minutes.

### D57. SpendWise logs its own steps to the console
- `core/logging.py` (called in `main.py`) sets `spendwise.*` loggers to INFO; libraries stay at WARNING.
- The agent logs the user message, each step, each tool call with its arguments, and each result (first 300 characters).
- These logs contain expense data. Fine on your own console; don't ship them to an external service without thinking about privacy.

---

## Memory (Phase 8)

### D58. Threads are stored as raw Gemini steps in `ChatMessage`
- **What:** one row per step (`user_input`, `thought`, `function_call`, `function_result`, `model_output`), with
  `thread_id`, `turn` and the step as JSON, in a table owned by the assistant module.
- **Why raw steps:** stateless function calling needs the history resent exactly as received, thoughts included.
  Storing anything else would mean rebuilding Gemini's format later.
- **No separate `Thread` table:** a thread is just the rows that share a `thread_id`. Add one if threads need titles or owners.

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
