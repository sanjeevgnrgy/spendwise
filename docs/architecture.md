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

Each is a small frozen Pydantic model with exactly one handler, and the two live in one file (a vertical slice, see
rule 2). Nobody calls a handler directly: everything goes through the **bus** (`core/cqrs.py`):
`bus.execute(command)`, `bus.ask(query)`.

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
    main.py              the web app: create_app(services): error handlers, CORS, routes under /api/v1, /health,
                         /mcp/ (uvicorn calls it with --factory: nothing is built at import)
    bootstrap.py         the composition root: the one list of modules; build() makes the Services (clock, engine,
                         bus, LLM, expense tools, MCP server), each replaceable; api_routers(services)
    migrations.py        run / check the Alembic migrations from code
    core/                shared technical code, no business rules; never imports a module
      config.py          settings from .env; API_PREFIX, API_VERSION, MCP_PATH
      cqrs.py            Command, Query, MessageBus (also the unit of work)
      db.py              create_db_engine(url) (SQLite made transactional: DDL, savepoints; in-memory databases
                         share one connection), session_factory(), the default engine
      ids.py             RecordId, MAX_ID (apart from db.py, so a contract doesn't load the database)
      errors.py          NotFoundError, BusinessRuleError, ExternalServiceError -> RFC 9457 problem details;
                         the unexpected-error middleware
      clock.py           Clock (today, now), instead of date.today()
      dependencies.py    BusDep, ClockDep, IdPath for routes
      months.py          YearMonth: "2026-11", its range and arithmetic
      money.py           rupees <-> paise, CURRENCY_PATTERN, format_money
      logging.py         console logging for our own loggers ("app.*")
      llm/               the LLM port (port.py: StructuredOutputModel, ToolCallingModel, LanguageModel = both,
                         LlmStream, LlmError), neutral messages (messages.py), the Gemini adapter (gemini.py:
                         GeminiModel, SDK calls and errors; gemini_wire.py: pure translation to and from Gemini's
                         wire format, and the stream's step assembly)
    modules/
      categories/        a domain module, as vertical slices (rule 2):
                           commands/     one file per command: the message and its handler (create_category.py)
                           queries/      one file per query: the message, its handler and its result
                                         (get_category.py, list_categories.py, find_category_by_name.py)
                           values.py     ids, Annotated field types, limits, fixed texts the slices share
                           models.py     read models several slices return (CategoryRead)
                           persistence/  tables.py: its table, private
                           api.py, module.py, __init__.py (the contract: re-exports the public names)
      expenses/          the same, plus domain/rules.py (rules the commands share), persistence/repository.py
                         (the write side's table access) and queries/month_range.py (the summary's and trend's filter)
      conversations/     stored chat threads (provider-neutral messages); GET /threads/{id}; the same shape,
                         without models.py, plus queries/thread_rows.py (what GetHistory and GetThread share)
      assistant/         the agent, one folder per role; imports run api/ -> application/ -> the rest:
                           api/          adapters: routes.py, schemas.py (bodies), agui_request.py (AG-UI in),
                                         agui_stream.py (AG-UI out), protocol.py (names on the wire)
                           application/  use cases: assistant.py (Assistant: run_turn, decide, chat), decisions.py
                                         (Approve/Cancel, no model), expense_parser.py (ExpenseParser, POST /parse)
                           agent/        the loop: agent.py (Agent.run), surfaces.py (WebPanel, TextChat: what
                                         differs by surface), prompts.py (system instruction), tool_runs.py
                                         (running a tool), events.py (what a turn yields)
                           approvals/    delete cards: commands/ (request, take, restore: one slice each),
                                         models.py, store.py, persistence/tables.py (pending_approval)
                           tools/        port.py (the ExpenseTools port), mcp_adapter.py (McpExpenseTools)
                           a2ui/         cards, forms
                           module.py     what the composition root plugs in
      mcp/               MCP adapter: contracts.py (tool and argument names, bearer scheme, typed results; all
                         __init__ exports), server.py (TOOL_REGISTRARS, create_server), tools/ (one file per tool,
                         plus support.py: argument types, error mapping, checks), resources.py, views.py (an
                         expense as tools show it), http.py (bearer token), module.py
  migrations/            Alembic: env.py and versions/0001_baseline, 0002_neutral_conversations, 0003_expense_version,
                         0004_conversation_turn_index
  scripts/               export_contracts.py (the contract for the web app)
  seed.py                sample data, through the bus
  mcp_stdio.py           the MCP server over stdio (Inspector, Claude Desktop)
```

### The rules

1. **Split by business domain**, never by technical layer. There is no app-wide `models/` or `routers/` folder.
   Inside a module, files are grouped by use case and by role (rule 2; the assistant's `api/`, `application/`, ...).
2. **Each module lives in `backend/app/modules/<name>/`** and owns its tables, contracts and handlers, organised as
   **vertical slices**:
   - `commands/<command>.py`, `queries/<query>.py`: one file per message, holding the message class and its handler
     (named like the file: `queries/get_monthly_summary.py` holds `GetMonthlySummary` and `get_monthly_summary`),
     plus anything only that message uses;
   - `values.py`: ids, `Annotated` field types, enums, limits and fixed texts the slices share;
   - `models.py`: read models several slices return (if any);
   - `domain/rules.py`: business rules several commands share (if any);
   - `persistence/tables.py`: its tables, private; `persistence/repository.py`: the write side's table access (if
     needed);
   - `api.py`: HTTP routes, which only translate HTTP into messages;
   - `module.py`: what the composition root plugs in (handlers, routes, tables);
   - `__init__.py`: the contract: it re-exports, from the files above, the names other code may use.
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
   same commands and queries. The assistant's use cases yield plain events; `api/agui_stream.py` turns them into
   AG-UI.
10. **Ports for the outside world:** the LLM (`core/llm/port.py`) and the expense tools (`assistant/tools/port.py`:
    `ExpenseTools`) are protocols with one adapter each (`GeminiModel`; `McpExpenseTools` in
    `assistant/tools/mcp_adapter.py`, in-process by default).
    Each user depends only on what it calls: `/parse` on `StructuredOutputModel`, the agent on `ToolCallingModel`.
    `bootstrap.build()` creates the adapters and injects them; nothing else imports a provider (D166, D172).
11. **No magic strings:** protocol names, tool names, keys and limits are enums or constants, defined once and
    exported from the module that owns them.
12. **No slow work inside a unit of work.** A model call can take two minutes; it never runs while a database session
    is open (D164).
13. **Small units with one job.** A file stays under about 180 lines of code and a function under about 50; a new tool,
    card, catalog component or surface is added by writing it and adding one entry to a table, not by editing a
    switch (D172). A new command or query is a new slice file plus one `bus.register` line in `module.py` (D175).

### Why vertical slices

A command or query and its handler change together: a new filter on `ListExpenses` needs a matching condition in
the code that handles it. So they live in one file, `queries/list_expenses.py`, and each use case is one file to
open, not a message in one file and its handler in another. Adding one is a new file, one `bus.register` line in
`module.py`, and an export from `__init__.py` if other modules use it. Only what several slices share sits beside
them, in a file or folder named for its role (`values.py`, `models.py`, `domain/`, `persistence/`), and a slice
never imports another slice's handler: it sends that slice's message through the bus.

A module's public contract is still its package: other modules write `from app.modules import expenses` and use
`expenses.GetMonthlySummary`, never a slice file. The trade-off: `__init__.py` re-exports the messages from their
slice files, so importing a module's package also loads its handlers and tables (not its routes, and not the
database engine). The earlier layout, where the package loaded only a `contracts.py`, gave the lighter import;
co-location was judged worth more. It can't cause an import cycle, because module dependencies run one way:
expenses → categories; mcp → expenses, categories; assistant → the rest. The mcp package still exports only its
`contracts.py` and loads no server code (D166, D175).

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
| `conversations` | `AppendTurn`, `GetLastTurn`, `GetHistory`, `GetThread`, `ThreadRead`, `ThreadId`, `THREAD_ID_MAX_LENGTH`, `THREAD_NOT_FOUND` | assistant |
| `mcp` | `ToolName`, `ResourceUri`, `SERVER_NAME`, `AUTHORIZATION_HEADER` and `BEARER_SCHEME` (how `/mcp/` is authenticated), the argument names (`EXPENSE_ID_ARGUMENT`, `CONFIRM_ARGUMENT`, `EXPECTED_VERSION_ARGUMENT`, `CLEAR_NOTE_ARGUMENT`), the typed results (`ExpenseView`, `ExpenseSaved`, `MonthSpending`, ...). The server itself (`create_server`, `create_http_app`) comes from `mcp/module.py`, for the composition root only | assistant |
| `assistant` | nothing for other modules; its `module.py` gives the composition root `create_router` and the `ExpenseTools` port type | — |

Each module's `module.py` is what `bootstrap.py` plugs in: `register_handlers(bus)`, its router (or a function that
builds one), its `TABLES`. Only `bootstrap.py` and `main.py` import a `module.py`.

### Migrations

Tables are created and changed by **Alembic migrations** (`backend/migrations`), never by the app. `.\run.ps1` runs
`alembic upgrade head` before starting, and the app refuses to start on an out-of-date database. To change a table:
change its `persistence/tables.py`, then
`.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini revision --autogenerate -m "..."`,
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
       -> commands/create_expense.py      create_expense(), the handler, in the same file as its command
            -> domain/rules.py              require_positive_amount()
            -> domain/rules.py              require_category_exists(): ctx.bus.ask(categories.GetCategory(...)),
                                            another module's query, in the same session
            -> persistence/repository.py    add(): staged; flush assigns the id
       <- the bus commits
  -> bus.ask(GetExpense(id)) the answer, as a query (queries/get_expense.py)
  <- 201, Location: /api/v1/expenses/{id}, the ExpenseRead
```

`POST /api/v1/agent` (AG-UI over Server-Sent Events; the chat panel uses this one). Paths are under `assistant/`:

```
HTTP request (RunAgentInput)
  -> api/routes.py           a sync generator with EventSourceResponse (a worker thread; a ping every 15 s)
  -> api/agui_request.py     read_request, a dependency: checks the thread id and reads the run (a button click in
                             forwardedProps.a2uiAction, or the newest message); a bad run is a 422 before streaming
  -> api/agui_stream.py      RUN_STARTED, then:
       Approve / Cancel  -> application/assistant.py: Assistant.decide(): TakeApproval (the snapshot) ->
                            application/decisions.py: approval_turn(): no model; the whole decision completes
                            (or the card is put back) before anything streams
       a message or Save -> application/assistant.py: Assistant.run_turn(): GetHistory ->
                            Agent.run(surface=WebPanel) -> AppendTurn
  -> agent/agent.py          the loop (at most 5 model calls), yielding events (agent/events.py):
       llm.stream_with_tools()          the model streams text and/or tool calls (neutral messages); the system
                                        instruction and the tool list come from the surface (agent/surfaces.py)
       a call the surface handles       WebPanel: a delete -> get_expense + RequestApproval -> ApprovalRequested
                                        (nothing deleted); show_expense_form -> the form (both surfaces)
       any other call                   agent/tool_runs.py: run_and_report() -> tools/mcp_adapter.py:
                                        McpExpenseTools -> the MCP server (mcp/tools/) -> the bus
  <- api/agui_stream.py translates: TextDelta -> TEXT_MESSAGE_*; ToolStarted -> TOOL_CALL_START (metadata.labels)
                             / ARGS / END; ToolFinished -> TOOL_CALL_RESULT (metadata.ok), STATE_SNAPSHOT if data
                             changed, CUSTOM "a2ui" card; ApprovalRequested -> the Approve/Cancel card;
                             FormRequested -> the form
  <- RUN_FINISHED, or RUN_ERROR on any failure (the turn isn't saved)
```

### Adding a module

1. `backend/app/modules/<name>/` with `commands/` and `queries/` (one file per message: the message and its
   handler), `values.py`, `persistence/tables.py` if it stores data, `api.py`, `module.py` (one `bus.register` per
   message, its router, its `TABLES`) and an `__init__.py` that re-exports the contract. Add `models.py`, `domain/`
   or `persistence/repository.py` when several slices need them. The skeleton:
   [backend_onboarding.md](backend_onboarding.md#recipe-add-a-module).
2. Add it to `MODULES` (and its router to `api_routers`) in `bootstrap.py`.
3. If it has tables: write a migration (above).
4. `.\.venv\Scripts\python.exe backend\scripts\export_contracts.py`, then `npm run gen:api` in `web/`, so the web app
   sees the new API.

### SOLID, in this code

| Principle | Where it shows |
|---|---|
| **Single responsibility** | One handler per message, in one file with its message (a vertical slice). The assistant's loop (`agent/agent.py`), what differs by surface (`agent/surfaces.py`), the prompt (`agent/prompts.py`), running a tool (`agent/tool_runs.py`) and Approve/Cancel (`application/decisions.py`) are separate. Reading AG-UI input (`api/agui_request.py`) and writing it (`api/agui_stream.py`) are separate. The Gemini adapter keeps SDK calls (`gemini.py`) apart from pure format translation (`gemini_wire.py`) |
| **Open/closed** | New command or query: a slice file plus one `bus.register` line. New MCP tool: a file in `mcp/tools/` with its registrar, plus one entry in `TOOL_REGISTRARS`. New card: one entry in `a2ui/cards.py`'s `_CARDS`. New surface: a class with the `Surface` methods. New module: an entry in `MODULES` |
| **Liskov substitution** | Every adapter can stand in for its port: `McpExpenseTools` in-process or remote, any `LanguageModel`, any `Clock`, any engine |
| **Interface segregation** | `StructuredOutputModel` and `ToolCallingModel` instead of one wide model interface; a module's contract exports only what others use |
| **Dependency inversion** | Use cases depend on protocols (`ExpenseTools`, the model ports, `Clock`); `bootstrap.build()` is the only place that picks implementations |

### Testability

Everything a test would want to replace can be passed in, without patching modules:

- `bootstrap.build(clock=..., llm=..., tools=..., engine=...)` builds the app's services around fakes, and
  `main.create_app(services)` serves them over HTTP (FastAPI's `TestClient` works directly on it).
- `migrations.upgrade_to_latest(engine)` migrates any engine, including an in-memory SQLite one (which shares a
  single connection, so every thread sees the same database).
- Nothing is built as a side effect of importing: uvicorn calls `create_app` (`--factory`), and each module's
  `values.py` gets its id rules from `core/ids.py`, not from the database module. Importing a module's package
  loads its handlers and tables, but never creates the database engine.
- A handler is a plain function in its slice file, `handler(ctx, message)`; `Context` is a dataclass (session, bus,
  clock), so a handler can be called with any of them, or reached through a bus built by `bootstrap.build()`.
- Use cases take their ports in their constructors: `Assistant(bus, tools, llm)`, `ExpenseParser(bus, llm)`,
  `Agent(llm, tools)`; `GeminiModel(api_key, model, client_factory=...)` takes a fake SDK client.
- Pure functions need no setup at all: the prompt builder, `gemini_wire`'s translation and `StepAssembler`, MCP's
  `to_view`, A2UI's card builders.
- Time comes from the injected `Clock`, never `date.today()`; tables have no timestamp defaults of their own.

The repository has no automated tests yet. Behaviour-preserving refactors are verified by recording every AG-UI event,
REST response and model call for a fixed set of scenarios, with a scripted fake model plugged in through these seams,
before and after the change (D173; the folder restructure was checked the same way, D175).

### Scalability

| Done | Why |
|---|---|
| `conversation_message` is indexed on `(thread_id, turn)` (migration 0004) | every read of a thread filters on both; the old one-column index was dropped as redundant |
| The `/parse` schema's base is built once and copied per request | it was rebuilt from the model on every request |
| MCP's `get_expense` names the expense's category with one lookup | it used to load every category |
| The web app loads each page, the chat panel and the chart library on demand | the JavaScript loaded at start fell from 1,252 kB to 541 kB |
| No in-process state between requests | approval cards live in the database, so several workers or processes can share it |
| Each command, query and MCP tool is its own file | the code grows by adding files, not by growing shared ones, so two changes to different use cases rarely touch the same file (D175) |

Known limits, to address when the load calls for it (D174):

- **Threads and connections:** sync routes and open `/agent` streams share anyio's default pool of 40 worker threads,
  and the SQLite engine's connection pool is 5 + 10 overflow. Size them together if many streams run at once.
- **SQLite writers:** transactions start with a deferred `BEGIN`, so two commands that read and then write at the
  same moment can fail with "database is locked". `BEGIN IMMEDIATE` for writing units of work plus WAL mode, or
  Postgres (already supported through `DATABASE_URL`), removes that.
- **Long threads:** `GET /threads/{id}` returns a whole thread, unpaged; the model's history is capped by turns, not size.
- **Remote MCP:** with `MCP_URL` set, every tool call opens a new MCP session (D74).

## The web app: feature slices

```
web/src/
  app/          the composition: main.tsx (root error boundary), providers.tsx (TanStack Query, theme, router,
                assistant), query-client.ts (the cache and the one refresh rule), pages.tsx (every page once),
                app.tsx (routes), layout/ (sidebar, top bar, the page area's and chat panel's error boundaries)
  features/     one folder per feature, each owning its components, hooks, API calls, types and constants:
    expenses/     the Expenses page; components/ grouped into table/, dialogs/, filters/, fields/; api.ts, queries.ts
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
   declares `meta: { changes: DATA_SCOPES.expenses }` and the assistant only reports "data changed"; one table in
   `app/query-client.ts` (`STALE_AFTER`, applied by `refreshAfter`) decides that means reloading the expenses and
   Dashboard queries (D168, D172).
4. **Server data goes through TanStack Query** (each feature's `queries.ts`): no fetching in effects, outdated requests
   cancelled, changes invalidate their keys.
5. **Nothing is copied from the backend by hand:** API types come from `schema.gen.ts`, protocol names and labels from
   `contracts.gen.ts` (both generated).
6. **Defined once:** the app's name (`APP_NAME`), the pages (`PAGES`, for both router and sidebar), the theme's boot
   script (generated from `theme-constants.ts` into `index.html` by a Vite plugin) (D169).
7. **A failure stays small:** error boundaries at the root, the page area, the chat panel and every A2UI card; a page
   keeps its data with a "couldn't refresh" notice when a reload fails; code that fails to load can be retried
   (`lazyWithRetry`).
8. **Logic outside components:** what can be a pure function is one (the chat transcript and run progress, SSE
   framing, A2UI actions and chart data, query status), and components and hooks stay small: a file under about 150
   lines of code, a component or hook under about 60. The A2UI renderer draws from catalog tables (`catalogs.ts`), not
   a switch (D172).
9. **Load on demand:** each feature's `index.ts` exports its page through `lazyWithRetry`; the chat panel is loaded the
   same way, in the background, so the first page doesn't wait for code it doesn't need (D174).

`.oxlintrc.json` enforces rules 2 and 3 (`no-restricted-imports`, including relative imports out of a feature at
every folder depth, relative imports out of `shared/` and deep imports from `app/`); `npx oxlint` fails on a
violation. It also runs the `jsx-a11y` accessibility rules.

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

# 2. Imports of a module's files. Every line must be inside that same module's folder (expenses/commands/
#    create_expense.py importing app.modules.expenses.persistence.repository is fine; anything else isn't).
Get-ChildItem backend\app\modules -Recurse -Filter *.py | Select-String -Pattern '^\s*from\s+app\.modules\.\w+\.'

# 3. Only the composition root imports a module.py. Expect bootstrap.py and main.py.
Get-ChildItem backend -Recurse -Filter *.py | Select-String -Pattern 'import module as' | Split-Path -Leaf | Sort-Object -Unique

# 4. Only bootstrap.py picks the LLM provider. Expect bootstrap.py, and gemini.py itself.
Get-ChildItem backend -Recurse -Filter *.py | Select-String -Pattern 'llm\.gemini|from google'

# 5. Inside the assistant, imports run api/ -> application/ -> agent/, approvals/, tools/, a2ui/, never back.
#    Expect only module.py, which builds the router and the use cases.
$assistant = Get-ChildItem backend\app\modules\assistant -Recurse -Filter *.py
$assistant | Where-Object FullName -NotMatch '\\assistant\\api\\' | Select-String -Pattern 'assistant\.api\b'
$assistant | Where-Object FullName -NotMatch '\\assistant\\(api|application)\\' |
  Select-String -Pattern 'assistant\.application\b'

```
