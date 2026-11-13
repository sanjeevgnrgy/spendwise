# Architecture

SpendWise is **one backend** (FastAPI, a modular monolith with CQRS) and **one web app** (React, organised as feature
slices). Each half has strict boundaries, and the two share one contract that's generated from the backend.

## The backend: a modular monolith

**One app, deployed as one unit, with one database**, divided inside into **modules by business domain**:
categories, expenses, conversations, assistant, and an MCP adapter.

Think of an apartment building. Everyone shares the foundation and the plumbing (`core/`). Each flat (module) has its
own locked door. When you need something from a neighbour, you knock (send a command or query through the bus, using
their contract); you don't walk through the wall.

- **Compared with microservices** (separate buildings): one process to run, debug and deploy; calls between modules
  are plain function calls, not network requests.
- **Compared with a "big ball of mud"** (one open-plan floor): the boundaries keep code from tangling, so each part can
  change without breaking the others.
- **Escape hatch:** because modules only meet through their contracts, any one of them can later move into its own
  service.

### CQRS: commands and queries

Every business operation is one of two kinds:

- a **command** asks for a change (`CreateExpense`, `DeleteExpense`) and returns at most an id;
- a **query** asks for data (`GetMonthlySummary`, `ListExpenses`) and changes nothing.

Each is a small frozen Pydantic model with exactly one handler. Nobody calls a handler directly: everything goes
through the **bus** (`core/cqrs.py`): `bus.execute(command)`, `bus.ask(query)`.

The bus is also the **unit of work**. The outermost message opens a database session. A command's session is
committed when its handler returns, and rolled back if it raises. A message sent from inside a handler (`ctx.bus`)
joins the same session, so a command and the checks it makes are one transaction. A command sent from inside another
runs in a **SAVEPOINT**: if it fails and the caller carries on, only its own changes are undone. A query can't send a
command. `with bus.unit_of_work():` groups several commands into one transaction (D163).

This is "CQRS-lite": reads and writes are separate operations on the **same** database. Separate read databases or
event sourcing would be overkill here (D139).

### Layout

```
backend/
  app/
    main.py              the web app: FastAPI, error handlers, CORS, routes under /api/v1, /health, /mcp/
    bootstrap.py         the composition root: the one list of modules; builds the bus, the MCP server, the routers
    migrations.py        run / check the Alembic migrations from code
    core/                shared technical code, no business rules; never imports a module
      config.py          settings from .env; API_PREFIX, API_VERSION, MCP_PATH
      cqrs.py            Command, Query, MessageBus (also the unit of work)
      db.py              the engine (SQLite made transactional: DDL, savepoints), new_session(), RecordId, MAX_ID
      errors.py          NotFoundError, BusinessRuleError, ExternalServiceError -> RFC 9457 problem details;
                         the unexpected-error middleware
      clock.py           Clock (today, now), instead of date.today()
      dependencies.py    BusDep, ClockDep, IdPath for routes
      months.py          YearMonth: "2026-11", its range and arithmetic
      money.py           rupees <-> paise, CURRENCY_PATTERN, format_money
      logging.py         console logging for our own loggers ("app.*")
      llm/               the LLM port (port.py: LanguageModel, LlmStream, LlmError), neutral messages
                         (messages.py), the Gemini adapter (gemini.py: GeminiModel)
    modules/
      categories/        contracts.py, tables.py, commands.py, queries.py, api.py, module.py
      expenses/          the same, plus domain.py (rules) and repository.py (the write side's table access)
      conversations/     stored chat threads (provider-neutral messages); GET /threads/{id}
      assistant/         the agent: api.py, agui.py (AG-UI adapter), turns.py (use cases), agent.py (the loop),
                         tools.py (expense-tools port + MCP adapter), approvals.py, parse.py (the /parse use
                         case), a2ui/ (cards, forms),
                         events.py, protocol.py, schemas.py, tables.py (pending_approval)
      mcp/               MCP adapter: contracts.py (tool and argument names, typed results; all __init__ exports),
                         server.py, http.py (bearer token), module.py (for the composition root)
  migrations/            Alembic: env.py and versions/0001_baseline, 0002_neutral_conversations, 0003_expense_version
  scripts/               export_contracts.py (the contract for the web app)
  seed.py                sample data, through the bus
  mcp_stdio.py           the MCP server over stdio (Inspector, Claude Desktop)
```

### The rules

1. **Split by business domain**, never by technical layer. There is no app-wide `models/` or `routers/` folder.
2. **Each module lives in `backend/app/modules/<name>/`** and owns its tables, contracts and handlers:
   - `contracts.py`: commands, queries and the data they carry: everything other code may use;
   - `tables.py`: its tables, private;
   - `commands.py` / `queries.py`: one handler per message;
   - `domain.py`: business rules (if any);
   - `repository.py`: the write side's table access (if needed);
   - `api.py`: HTTP routes, which only translate HTTP into messages;
   - `module.py`: what the composition root plugs in (handlers, routes, tables).
3. **Modules talk only through contracts and the bus.** Another module's names come from its package
   (`from app.modules import categories` → `categories.GetCategory`), never from its files. Never query another
   module's tables.
4. **Commands return at most an id; queries change nothing.** A route that must answer with data sends the command,
   then asks a query. A query that tries to send a command is refused.
5. **Handlers never commit.** The bus does, once per outermost command. Repositories only stage changes.
6. **Links between modules are plain ids** with no database foreign key, checked through the other module's queries.
7. **`core/` never imports from `modules/`.**
8. **`bootstrap.py` is the composition root:** the only file that knows every module. `main.py`, `seed.py`,
   `mcp_stdio.py` and the migrations all build from it. Nothing registers itself just by being imported.
9. **Adapters translate, use cases decide.** REST routes, the MCP server and the AG-UI adapter are adapters over the
   same commands and queries. The assistant's use cases yield plain events; `agui.py` turns them into AG-UI.
10. **Ports for the outside world:** the LLM (`core/llm/port.py`: `LanguageModel`) and the expense tools
    (`assistant/tools.py`: `ExpenseTools`) are protocols with one adapter each (`GeminiModel`; `McpExpenseTools`,
    in-process by default). `bootstrap.build()` creates the adapters and injects them; nothing else imports a provider
    (D166).
11. **No magic strings:** protocol names, tool names, keys and limits are enums or constants, defined once and
    exported from the module that owns them.
12. **No slow work inside a unit of work.** A model call can take two minutes; it never runs while a database session
    is open (D164).

### Why each module owns its tables

If any module can query any table, that table's columns become a promise to everyone. Renaming a column or adding a
rule then means hunting down every place that reads it. When only `expenses` touches the expense table, it can rename
columns, add indexes or move to another database, and nobody else notices, as long as its contract keeps working.

That's also why `expense.category_id` has **no foreign key**. A foreign key would tie the two modules' tables together
at the database level. Instead, `CreateExpense`'s handler asks `categories.GetCategory` whether the category exists.

### Public interfaces today

| Module | Contract (`from app.modules import <name>`) | Used by |
|---|---|---|
| `categories` | `CategoryRead`, `CreateCategory`, `ListCategories`, `GetCategory`, `FindCategoryByName`, `CategoryId`, `MAX_NAME_LENGTH`, `UNKNOWN_CATEGORY`, `NO_CATEGORIES_YET` | expenses, mcp, assistant, seed |
| `expenses` | `ExpenseRead`, `ExpenseList`, `CreateExpense`, `UpdateExpense` + `ExpenseChanges`, `DeleteExpense` (with `expected_version`), `GetExpense`, `ListExpenses`, `GetMonthlySummary`, `GetMonthlyTrend` (+ their result types), `ExpenseId`, `MAX_LIST_LIMIT`, `PaymentMethod`, `PAYMENT_METHOD_LABELS` | mcp, assistant (`PaymentMethod`, labels), seed |
| `conversations` | `AppendTurn`, `GetLastTurn`, `GetHistory`, `GetThread`, `ThreadRead`, `ThreadId`, `THREAD_ID_MAX_LENGTH` | assistant |
| `mcp` | `ToolName`, `ResourceUri`, `SERVER_NAME`, the argument names (`EXPENSE_ID_ARGUMENT`, `CONFIRM_ARGUMENT`, `EXPECTED_VERSION_ARGUMENT`, `CLEAR_NOTE_ARGUMENT`), the typed results (`ExpenseView`, `ExpenseSaved`, `MonthSpending`, ...). The server itself (`create_server`, `create_http_app`) comes from `mcp/module.py`, for the composition root only | assistant |
| `assistant` | nothing (the composition root uses its `module.py`) | — |

Each module's `module.py` is what `bootstrap.py` plugs in: `register_handlers(bus)`, its router (or a function that
builds one), its `TABLES`. Only `bootstrap.py` and `main.py` import a `module.py`.

### Migrations

Tables are created and changed by **Alembic migrations** (`backend/migrations`), never by the app. `.\run.ps1` runs
`alembic upgrade head` before starting, and the app refuses to start on an out-of-date database. To change a table:
change its `tables.py`, then `.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini revision --autogenerate -m "..."`,
read the generated file, and run `upgrade head`.

An upgrade runs in **one transaction, schema changes included**: if any step fails, the database is left exactly as it
was (D163). Details of every table and migration: [database_schema.md](database_schema.md).

### Changes that can't be lost: versions

`expense.version` starts at 1 and every update raises it. `DeleteExpense` can carry an `expected_version`, checked in
the `DELETE` statement itself (`WHERE id = ? AND version = ?`). The assistant's Approve passes the version its card
showed, so an expense edited while the card waited is never deleted unseen (D162).

### Errors

Handlers raise `NotFoundError`, `BusinessRuleError` or `ExternalServiceError` (e.g. `LlmError`). `core/errors.py` turns
them, FastAPI's validation errors and its own 404/405 into one shape, RFC 9457 problem details:

```json
{"type": "urn:spendwise:problem:not-found", "title": "Not found", "status": 404,
 "detail": "Expense 14 not found", "instance": "/api/v1/expenses/14"}
```

Anything else (a bug) becomes a generic 500 problem in `UnexpectedErrorMiddleware`, which sits **inside** CORS so the
browser can still read it; the traceback goes only to the log. FastAPI's own errors keep their headers (`Allow` on a
405) (D165).

### How a request flows

`POST /api/v1/expenses`:

```
HTTP request
  -> expenses/api.py         FastAPI validates the body (the CreateExpense command) -> 422 problem if malformed
  -> bus.execute(command)    opens a session (the unit of work)
       -> expenses/commands.create_expense()
            -> domain.require_positive_amount()
            -> ctx.bus.ask(categories.GetCategory(...))   another module's query, in the same session
            -> repository.add()                          staged; flush assigns the id
       <- the bus commits
  -> bus.ask(GetExpense(id)) the answer, as a query
  <- 201, Location: /api/v1/expenses/{id}, the ExpenseRead
```

`POST /api/v1/agent` (AG-UI over Server-Sent Events; the chat panel uses this one):

```
HTTP request (RunAgentInput)
  -> assistant/api.py        a sync generator with EventSourceResponse (a worker thread; a ping every 15 s)
  -> agui.read_request       a dependency: checks the thread id and reads the run (a button click in
                             forwardedProps.a2uiAction, or the newest message); a bad run is a 422 before streaming
  -> assistant/agui.py       RUN_STARTED, then:
       Approve / Cancel  -> turns.Assistant.decide():  TakeApproval (the snapshot) -> agent.approval_turn(): no model;
                            the whole decision completes (or the card is put back) before anything streams
       a message or Save -> turns.Assistant.run_turn(): GetHistory -> agent.run() -> AppendTurn when it finishes
  -> assistant/agent.py      the loop (at most 5 model calls), yielding events:
       llm.stream_with_tools()          the model streams text and/or tool calls (neutral messages)
       tools.call()                     McpExpenseTools -> the MCP server (in-process) -> the bus
       a delete in the web panel        -> get_expense + RequestApproval -> ApprovalRequested (nothing deleted)
  <- agui.py translates:    TextDelta -> TEXT_MESSAGE_*; ToolStarted -> TOOL_CALL_START (metadata.labels) / ARGS / END;
                             ToolFinished -> TOOL_CALL_RESULT (metadata.ok), STATE_SNAPSHOT if data changed,
                             CUSTOM "a2ui" card; ApprovalRequested -> the Approve/Cancel card; FormRequested -> the form
  <- RUN_FINISHED, or RUN_ERROR on any failure (the turn isn't saved)
```

### Adding a module

1. `backend/app/modules/<name>/` with `contracts.py`, `tables.py`, `commands.py` / `queries.py`, `api.py`, `module.py`
   and an `__init__.py` that exports the contract.
2. Add it to `MODULES` (and its router to `api_routers`) in `bootstrap.py`.
3. If it has tables: write a migration (above).
4. `.\.venv\Scripts\python.exe backend\scripts\export_contracts.py`, then `npm run gen:api` in `web/`, so the web app
   sees the new API.

## The web app: feature slices

```
web/src/
  app/          the composition: main.tsx (root error boundary), providers.tsx (TanStack Query, theme, router,
                assistant), query-client.ts (the cache and the one refresh rule), pages.tsx (every page once),
                app.tsx (routes), layout/ (sidebar, top bar, the page area's and chat panel's error boundaries)
  features/     one folder per feature, each owning its components, hooks, API calls, types and constants:
    expenses/     the Expenses page, table, edit row, add and delete dialogs, filters; api.ts, queries.ts
    categories/   categories API and queries, CategorySelect, category names
    dashboard/    the Dashboard page, stat cards, charts, recent list; api.ts, queries.ts
    assistant/    the chat panel; model/ (useChat, AssistantProvider); api/ (the AG-UI stream); a2ui/ (renderer)
  shared/       knows no feature: ui/ (shadcn kit), api/ (typed HTTP client, generated contract), config/ (app name,
                env, routes, locale, data scopes), lib/ (formatting, guards, errors, ids), components/ (empty state,
                error boundary, section error, refresh notice, placeholder page), hooks/, theme/
```

### The rules

1. **A feature owns everything it needs.** Nothing about expenses lives outside `features/expenses/`.
2. **Other code imports a feature only through its `index.ts`** (`@/features/expenses`), never a file inside it.
   Inside a feature, imports are relative. Fewer cross-feature imports is better.
3. **`shared/` imports no feature and not `app/`. Only `app/` wires features together.** For example, a mutation only
   declares `meta: { changes: DATA_SCOPES.expenses }` and the assistant only reports "data changed"; one rule in
   `app/query-client.ts` (`refreshExpenseData`) decides that means reloading the expenses and Dashboard queries
   (D168).
4. **Server data goes through TanStack Query** (each feature's `queries.ts`): no fetching in effects, outdated requests
   cancelled, changes invalidate their keys.
5. **Nothing is copied from the backend by hand:** API types come from `schema.gen.ts`, protocol names and labels from
   `contracts.gen.ts` (both generated).
6. **Defined once:** the app's name (`APP_NAME`), the pages (`PAGES`, for both router and sidebar), the theme's boot
   script (generated from `theme-constants.ts` into `index.html` by a Vite plugin) (D169).
7. **A failure stays small:** error boundaries at the root, the page area, the chat panel and every A2UI card; a page
   keeps its data with a "couldn't refresh" notice when a reload fails.

`.oxlintrc.json` enforces rules 2 and 3 (`no-restricted-imports`, including relative imports out of `shared/` and deep
imports from `app/`); `npx oxlint` fails on a violation. It also runs the `jsx-a11y` accessibility rules.

Working guides: [backend_onboarding.md](backend_onboarding.md), [frontend_onboarding.md](frontend_onboarding.md).
The full review that shaped these rules: [architecture-review.md](architecture-review.md).

## The shared contract

```
backend  --export_contracts.py-->  web/openapi.json  --npm run gen:api-->  web/src/shared/api/schema.gen.ts
                                   web/src/shared/api/contracts.gen.ts
```

- `schema.gen.ts`: every REST request and response type, and enum values (openapi-typescript). The client
  (`shared/api/http.ts`, openapi-fetch) won't compile a request the API doesn't accept.
- `contracts.gen.ts`: what OpenAPI doesn't describe: A2UI catalogs and actions, AG-UI event names and keys, payment
  method labels, limits.

After changing an API or one of those values: run the export script, then `npm run gen:api`.

## Checking the rules

The web app's rules are checked by `npx oxlint` in `web/`. The backend has no automated check at the moment (the
architecture test was removed with the other tests, D64), so run these scans from the project folder:

```powershell
# 1. core/ never imports a module. Expect no output.
Get-ChildItem backend\app\core -Recurse -Filter *.py | Select-String -Pattern '^\s*(from|import)\s+app\.modules'

# 2. Imports of a module's files. Every line must be inside that same module's folder
#    (expenses/commands.py importing app.modules.expenses.repository is fine; anything else isn't).
Get-ChildItem backend\app\modules -Recurse -Filter *.py | Select-String -Pattern '^\s*from\s+app\.modules\.\w+\.'

# 3. Only the composition root imports a module.py. Expect bootstrap.py and main.py.
Get-ChildItem backend -Recurse -Filter *.py | Select-String -Pattern 'import module as' | Split-Path -Leaf | Sort-Object -Unique

# 4. Only bootstrap.py picks the LLM provider. Expect bootstrap.py, and gemini.py itself.
Get-ChildItem backend -Recurse -Filter *.py | Select-String -Pattern 'llm\.gemini|from google'
```
