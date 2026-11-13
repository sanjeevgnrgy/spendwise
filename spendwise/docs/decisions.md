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
