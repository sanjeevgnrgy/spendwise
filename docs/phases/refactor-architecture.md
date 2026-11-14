# Refactor: CQRS backend, feature-slice web app (after Phase 18)

**Goal:** an architecture review asked for no magic strings, no duplicated code, a strict modular monolith with CQRS,
strict feature slices in the web app, and no tight coupling. This refactor makes the code meet those rules, without
changing what the app does for you (two visible additions: a **Stop** button in the chat, and `/api/v1` in the URLs).

> **How it was checked:** offline, with a scripted fake model against the real app, on copies of the real database.
> - Migrations: up, down and up again, on a copy of the real database. The chat history converted and converted back
>   to the original rows exactly.
> - REST over HTTP: problem details, `/health`, and `/mcp/` (no token: 401, bad Host: 421, bad Origin: 403).
> - Every agent flow: the insight card; a delete with Approve or Cancel; Approve from another thread, after an edit,
>   or twice; the form; `/chat` deletes.
> - The in-process and the remote MCP tool adapters.
> - The real web modules, loaded through Vite against that backend: API calls, the validated stream, cards, Stop, and
>   both pages rendered with TanStack Query data.
> - `npm run build` and `npx oxlint` pass. Not yet tried by hand in a browser.

## Design: CQRS, and the unit of work

**Command Query Responsibility Segregation** splits every operation in two kinds:

- a **command** changes something ("create this expense") and returns at most an id;
- a **query** reads something ("this month's summary") and changes nothing.

Why bother? Because the two have different needs. Commands need rules, checks and transactions. Queries need to be
fast and shaped for the screen. Mixing them in one `service.py` made both harder to see: was `delete_expense(confirmed=False)`
a read or a write? (It was both. Now `get_expense` is a query and `delete_expense` is a command.)

Each command or query is a small frozen model (`CreateExpense(amount=..., ...)`) with exactly one handler, sent through
a **bus**: `bus.execute(command)`, `bus.ask(query)`. Callers know the message, not the handler or the tables.

The bus is also the **unit of work**: one database session per outermost command, **committed once** when the handler
succeeds, rolled back if it fails. Before, every repository function committed on its own, so "create these 18
things" was 18 transactions. Now the seed runs inside `bus.unit_of_work()`: all or nothing.

**Analogy:** a restaurant. Orders (commands) go to the kitchen and change the stock; questions (queries) go to the
waiter, who just looks. Either way you talk to the front desk (the bus), never walk into the kitchen. A large order
is cooked as one ticket: if one dish fails, the whole ticket is sent back.

## Design: ports and adapters

A **port** is what the app needs ("talk to an LLM", "use the expense tools"), as an interface. An **adapter** is one
way of doing it (Gemini; MCP in-process; MCP over HTTP). The composition root picks the adapter.

- `core/llm` is the LLM port; `core/llm/gemini.py` the only Gemini-specific code. The chat history is stored in
  SpendWise's own message types, not Gemini's wire format, so a new provider is one new adapter, not a data migration.
- `assistant/tools.py` is the tools port; `McpExpenseTools` uses the MCP SDK's `Client`, which talks to this app's MCP
  server **in-process** by default. No more HTTP calls to our own port.
- The assistant's use cases yield plain events; `agui.py` (an adapter) turns them into AG-UI. The REST routes and the
  MCP server are adapters too, over the same commands and queries.

## Design: feature slices

The web app was grouped by kind of file: all components here, all hooks there, one `api.ts` for everything. To change
"expenses", you touched five folders. Now each **feature** is one folder that owns its components, hooks, API calls and
types. Other code imports it only through its `index.ts`. `shared/` holds what any feature may use and knows no
feature. `app/` is the only place that connects features.

**Analogy:** a department store. Each department (feature) has its own stock and staff. Shared services (lifts,
tills: `shared/`) serve every department and belong to none. Store management (`app/`) decides how departments work
together: "when the assistant changes expenses, the Expenses and Dashboard departments restock".

## What was built

**Backend**

| Where | What |
|---|---|
| `core/cqrs.py` | `Command`, `Query`, `MessageBus` (the unit of work) |
| `core/errors.py` | RFC 9457 problem details for every error |
| `core/clock.py`, `core/months.py`, `core/money.py`, `core/dependencies.py` | a Clock; `YearMonth`; `format_money` and the currency pattern; `BusDep`/`ClockDep` |
| `core/llm/` | the LLM port, neutral messages, the Gemini adapter |
| `modules/*/contracts.py, commands.py, queries.py, api.py, module.py` | every module in CQRS form |
| `modules/conversations/` | **new**: chat threads, moved out of the assistant, stored as neutral messages |
| `modules/mcp/` | typed results (`outputSchema`), `get_expense`, `delete_expense` with a strict `confirmed`, `/mcp/` only with `MCP_TOKEN` |
| `modules/assistant/` | the tools port, use cases (`turns.py`), events, the AG-UI adapter, approvals in the database |
| `app/bootstrap.py` | the composition root |
| `migrations/`, `alembic.ini`, `app/migrations.py` | Alembic: 0001 (the old schema, safe on existing databases), 0002 (neutral conversations, pending approvals), 0003 (expense versions, after the code reviews) |
| `scripts/export_contracts.py` | writes `web/openapi.json` and `web/src/shared/api/contracts.gen.ts` |
| removed | `POST /ask` (an open proxy to Gemini) |

**Web**

| Where | What |
|---|---|
| `src/app/` | providers (TanStack Query, theme, router, assistant), routes, layout with an error boundary |
| `src/features/{expenses,categories,dashboard,assistant}/` | each with `index.ts`, `api.ts`, `queries.ts` / `model/`, components |
| `src/shared/` | the shadcn kit, the typed HTTP client, generated contract, config, formatting, theme, error boundary |
| `.oxlintrc.json` | the slice rules, enforced |
| `package.json` | every version pinned; `gen:api` |

## After the code reviews

Two independent reviews (backend and web) then read the refactored code and reproduced each finding with a scratch
script. Every finding was fixed except four left on purpose (D170). The full list, with the reason for each, is in
[architecture-review.md](../architecture-review.md); the decisions are D162–D170.

| Problem found | What changed |
|---|---|
| An edit between Approve's check and the delete would be deleted unseen | `expense.version`; Approve deletes only the version its card showed, checked in the `DELETE` itself (D162) |
| A failing migration left the database half-changed; a failing nested command undid its caller's work | SQLite made transactional: atomic migrations, SAVEPOINTs for nested commands (D163) |
| `/parse` held a database connection for the whole model call | it's a use case now: a short query, then the model call with no session open (D164) |
| A put-back Approve card ran whenever the garbage collector got to it, and lost its age | the decision completes before streaming; a failure restores the card at once, with its original time (D164) |
| A crash's 500 had no CORS headers, so the browser saw a "network error" | the error middleware sits inside CORS; `Allow` and other headers kept; `bearer` matched in any case (D165) |
| The assistant built its own Gemini client; importing the MCP contract loaded the server | an injected `LanguageModel` port; the mcp package exports only its contract (D166) |
| A bad `/agent` request became a `RUN_ERROR` mid-stream | a 422 problem before the stream starts (D167) |
| Each mutation listed the queries to reload; a failed reload wiped the page | one `meta.changes` rule in `app/`; data kept with a "couldn't refresh" notice; more error boundaries (D168) |
| A2UI names, the app's name, the page list and the theme script were each written in two places | generated or defined once; jsx-a11y lint rules (D169) |

## Run it

```powershell
.\run.ps1                       # runs the migrations first, then the server
cd web; npm install; npm run dev
```

The REST API moved to `/api/v1` (open http://127.0.0.1:8000/docs). After changing an API:

```powershell
.\.venv\Scripts\python.exe backend\scripts\export_contracts.py
cd web; npm run gen:api
```

To use `/mcp/` over HTTP (MCP Inspector), set `MCP_TOKEN` in `.env` and send it as `Authorization: Bearer <token>`.
The assistant and `backend\mcp_stdio.py` don't need it.

## Verify it by hand

1. **Migrations.** Stop the server, run `.\run.ps1`. Expect a "Running upgrade" line for each new migration the first
   time, none after. Your expenses and old conversations are still there.
2. **Problem details.** http://127.0.0.1:8000/api/v1/expenses/999999 →
   `{"type": "urn:spendwise:problem:not-found", "title": "Not found", "status": 404, ...}`.
3. **The app.** Dashboard and Expenses look as before. Add, edit and delete an expense: the list updates by itself.
4. **The assistant.** "Where did my money go this month?" → the insight card. "Delete #N" → Approve/Cancel; Approve
   deletes, and both pages refresh. Money reads `₹1,234.50` in cards and on pages alike.
5. **Stop.** Ask something, press the square **Stop** button while it works: "Stopped." appears; a tool that was running
   shows "?" and the pages reload.
6. **Versions.** Ask the assistant to delete an expense, but before clicking Approve, change that expense's amount on
   the Expenses page. Now Approve: nothing is deleted, and the reply says the expense changed.
7. **The lint rules.** In `web/src/features/dashboard/`, import `@/features/expenses/queries` in any file; `npx oxlint`
   fails with "Import another feature only through its public API". Undo it.

## Design questions

**1. `delete_expense` used to take `confirmed=false` to preview. Why is that a CQRS problem, and what replaced it?**

<details><summary>Answer</summary>

One operation was both a query (show me) and a command (delete it), switched by a flag. A caller couldn't tell from its
name whether it changes data. Now `get_expense` is a read-only query and `delete_expense` only deletes. It still
requires `confirmed`, strictly `true`, as an interlock: the MCP SDK ignores arguments a tool doesn't declare, so an old
client sending `confirmed=false` to preview would otherwise delete for real.
</details>

**2. The seed creates 8 categories and 10 expenses. What happens now if the 9th expense fails, and why?**

<details><summary>Answer</summary>

Nothing is saved. The seed runs inside `bus.unit_of_work()`: every command joins the same session, handlers never
commit, and the bus commits once at the end, or rolls everything back if anything raised. Before, each repository call
committed by itself, so the first 8 would have stayed.
</details>

**3. After the assistant saves an expense, the Expenses table refreshes. Which code knows that, and why not the assistant?**

<details><summary>Answer</summary>

The app: `refreshExpenseData()` in `app/query-client.ts` (later a `STALE_AFTER` table applied by `refreshAfter`,
see [refactor-solid.md](refactor-solid.md)), wired up in `app/providers.tsx`. The assistant feature only
calls `onDataChanged()` when a `STATE_SNAPSHOT` arrives (and a mutation only declares `meta.changes`); the app decides
that means invalidating the expenses and Dashboard queries, and TanStack Query reloads whatever is on screen.
If the assistant knew about those pages, adding a Budgets page would mean changing the assistant: that's the tight
coupling feature slices avoid.
</details>

**4. Approve already checked that the expense still matched the card. Why add a version column too?**

<details><summary>Answer</summary>

The check and the delete were two statements. An edit landing between them (from the Expenses page, or another MCP
client) would pass the check and then be deleted unseen. `DELETE … WHERE id = ? AND version = ?` makes the check and
the delete one statement: if the row changed, nothing matches and nothing is deleted. No lock is held while you
decide. This is optimistic concurrency: assume no conflict, and detect one at the moment of writing.
</details>

**5. `/parse` used to be a query handler. Why was that a problem, when it doesn't change any data?**

<details><summary>Answer</summary>

A query handler runs inside the bus's unit of work, so a database connection was held for the whole model call (up to
two minutes). A few slow calls at once could take every pooled connection, and other requests would wait. As a use
case it asks for the categories (a short query, connection returned), then calls the model with no session open.
</details>
