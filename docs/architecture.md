# Architecture

SpendWise is **one backend** (FastAPI, a modular monolith with CQRS) and **one web app** (React, organised as feature
slices). Each half has strict boundaries, and the two share one contract that's generated from the backend.

## The backend: a modular monolith

**One app, deployed as one unit, with one database**, divided inside into **modules by business domain**:
categories, expenses, conversations, receipts, assistant, and an MCP adapter.

Think of an apartment building. Everyone shares the foundation (`core/`), the plumbing (`infrastructure/`) and the
entrance (`web/`). Each flat (module) has its own locked door. When you need something from a neighbour, you knock
(send a command or query through the bus, using their contract); you don't walk through the wall.

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
    main.py              the web app: create_app(services): error handlers, routes under /api/v1 (every module's
                         behind the X-CSRF and session checks, the sign-in routes not), /health, /mcp/ (uvicorn calls
                         it with --factory: nothing is built at import); no CORS (D184)
    bootstrap.py         the composition root: the one list of modules; build() makes the Services (clock, engine,
                         bus, LLM, expense tools, file store, MCP server, identity provider, sealer, session check,
                         cookies), each replaceable; auth_routers(services), api_routers(services)
    core/                shared building blocks: no I/O, no framework, no business rules; imports nothing else
      cqrs.py            Command, Query, MessageBus (also the unit of work)
      errors.py          NotFoundError, BusinessRuleError, ExternalServiceError, AuthenticationError (401),
                         ForbiddenError (403), TooManyRequestsError (429), each with its status and type
      rate_limit.py      RateLimiter: a minute's and a day's allowance per person (D194)
      ids.py             RecordId, MAX_ID, UserId (apart from the database, so a contract doesn't load it)
      clock.py           Clock (today, now), instead of date.today()
      files.py           FileStore: the port for uploaded files' bytes (save, read, delete by a key it makes up)
      identity.py        IdentityProvider: the sign-in port (D185), with VerifiedLogin, LogoutNotice, Principal
                         (who a request comes from), IdentityError and InvalidTokenError
      sealing.py         Sealer: the port for keeping a secret text unreadable where it's stored (seal, unseal)
      months.py          YearMonth: "2026-11", its range and arithmetic
      money.py           rupees <-> paise, CURRENCY_PATTERN, format_money (CLDR, in a language's locale)
      i18n/              Language and Accept-Language negotiation, define_catalog / text / Plural / Translatable
                         (texts for people, checked at startup), format_day and format_month (Babel's CLDR data)
      llm/               the LLM port (port.py: StructuredOutputModel, ToolCallingModel, LanguageModel = both,
                         LlmStream, LlmError, Attachment: a file the model reads), neutral messages (messages.py)
                         and the shared pieces of a structured-output schema (schema.py)
    infrastructure/      what talks to the outside world; imports only core/; only the composition root and the
                         entry points import it
      config.py          settings from .env; API_PREFIX, API_VERSION, MCP_PATH
      db.py              create_db_engine(url) (SQLite made transactional: DDL, savepoints; in-memory databases
                         share one connection), session_factory(), the default engine
      migrations.py      run / check the Alembic migrations from code
      logging.py         console logging for our own loggers ("app.*")
      files.py           LocalFileStore: the FileStore port as a folder (UPLOADS_DIR), files named by random keys
      identity/          the sign-in adapters: oidc.py (OidcIdentityProvider: standard OpenID Connect only),
                         documents.py (discovery and signing keys, cached), exchange.py (token and UserInfo
                         endpoints), tokens.py (checking ID and logout tokens), options.py (OIDC_LOGIN_OPTIONS),
                         unconfigured.py (refuses every sign-in while a setting is missing)
      sealing.py         FernetSealer: the Sealer port with Fernet (SESSION_ENCRYPTION_KEYS, rotatable)
      llm/               the Gemini adapter (gemini.py: GeminiModel, SDK calls and errors; gemini_wire.py: pure
                         translation to and from Gemini's wire format, and the stream's step assembly)
    web/                 the FastAPI plumbing every route shares; imports only core/
      dependencies.py    BusDep, ClockDep, IdPath, LanguageDep (the request's Accept-Language) for routes
      auth.py            the session cookie and the login cookie (SessionCookies), require_csrf (X-CSRF and
                         Sec-Fetch-Site), require_user / CurrentUserDep (the session check main.py puts on app.state)
      problems.py        RFC 9457 problem details for every error, the detail in the request's language: the
                         error handlers and the unexpected-error middleware
      rate_limits.py     MODEL_QUOTA: the per-person allowance on the routes that call the model (D194)
      security_headers.py  the headers on every answer; no-store under the API and MCP (D193)
      i18n/              the web layer's own texts (a bug's generic detail, "Sign in to continue.", a refused request)
    modules/
      accounts/          people, how they sign in, their sessions (D187); the same shape, plus domain/ (keys.py,
                         return_paths.py, rules.py) and application/ (sign_in.py: SignInFlow; sign_out.py:
                         SignOutFlow; sessions.py: SessionGate, the check behind every protected route), which call
                         the identity provider and so aren't bus messages
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
      budgets/           monthly limits, overall and per category (D210): commands/ (set_budget, remove_budget),
                         queries/get_budget_status.py (spending from the expenses module's summary against the
                         limits), domain/rules.py (the state, the share used, the month gone by), persistence/
      conversations/     stored chat threads (provider-neutral messages); GET /threads/{id}; the same shape,
                         without models.py, plus queries/thread_rows.py (what GetHistory and GetThread share)
      receipts/          uploaded receipt files, for their owner; the same shape, plus domain/file_types.py (what
                         may be uploaded, judged by the file's bytes) and application/ (upload_receipt.py:
                         ReceiptUploader; receipt_files.py: ReceiptFiles, an owner's file for the assistant), which
                         aren't bus messages: both use the FileStore. Reading a receipt is the receipt agent's
      reports/           a person's monthly report (D209), no tables of its own: application/monthly_reports.py
                         (MonthlyReports: reads expenses and categories through their queries, runs the monthly-report
                         skill's script, checks its answer), models.py (MonthlyReport), documents/ (markdown.py,
                         spreadsheet.py: the downloads, in the person's language), api.py, i18n/, values.py, module.py
      assistant/         the agent, one folder per role; imports run api/ -> application/ -> the rest:
                           api/          adapters: routes.py, schemas.py (bodies), agui_request.py (AG-UI in),
                                         agui_stream.py (AG-UI out), protocol.py (names on the wire)
                           application/  use cases: assistant.py (Assistant: run_turn, read_receipt, decide, chat),
                                         decisions.py (Approve/Cancel, no model), receipt_turn.py (an attached
                                         receipt offered as the form, no agent loop), expense_parser.py
                                         (ExpenseParser, POST /parse)
                           agent/        the loop: agent.py (Agent.run), surfaces.py (WebPanel, TextChat: what
                                         differs by surface), prompts.py (system instruction), tool_runs.py
                                         (running a tool), events.py (what a turn yields)
                           approvals/    delete cards: commands/ (request, take, restore: one slice each),
                                         models.py, store.py, persistence/tables.py (pending_approval)
                           tools/        port.py (the ExpenseTools port), mcp_adapter.py (McpExpenseTools)
                           receipt_agent/ port.py (the ReceiptReader port), agent_reader.py (AgentReceiptReader:
                                         the receipt agent through core/agents.RemoteAgents, D199, D201)
                           skills/       Agent Skills in the turn (D208): skill_tool.py (the catalog in the
                                         instruction, the load_skill tool and its handler)
                           delegation/   the other agents the model may hand requests to (D206): skills.py (what
                                         the server sends each), directory.py (cards read at startup, the
                                         delegate_to_agent tool), delegator.py (a call, and resuming a waiting task),
                                         models.py, commands/ and persistence/ (pending_delegation)
                           a2ui/         cards, forms
                           module.py     what the composition root plugs in
      mcp/               MCP adapter: contracts.py (tool and argument names, bearer scheme, typed results; all
                         __init__ exports), server.py (TOOL_REGISTRARS, create_server), tools/ (one file per tool,
                         plus support.py: argument types, error mapping, checks), resources.py, views.py (an
                         expense as tools show it), http.py (bearer token), module.py
  migrations/            Alembic: env.py and versions/0001_baseline, 0002_neutral_conversations, 0003_expense_version,
                         0004_conversation_turn_index, 0005_receipt_files, 0006_accounts, ... 0010_budgets
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
   - `i18n/`: its texts for people in every language (`en.py` holds the keys and the English source; D179);
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
7. **Outside the modules, shared code is grouped by concern** (D177). `core/` imports nothing else in the app;
   `infrastructure/` and `web/` import only `core/`. Modules never import `infrastructure/` (what it builds, the
   bus's sessions and the model, is passed in), and only their HTTP adapters (`api.py`, `accounts/account_api.py`,
   `assistant/api/routes.py`, `mcp/http.py`) import `web/`.
8. **`bootstrap.py` is the composition root:** the only file that knows every module. `main.py`, `seed.py`,
   `mcp_stdio.py` and the migrations all build from it. Nothing registers itself just by being imported.
9. **Adapters translate, use cases decide.** REST routes, the MCP server and the AG-UI adapter are adapters over the
   same commands and queries. The assistant's use cases yield plain events; `api/agui_stream.py` turns them into
   AG-UI.
10. **Ports for the outside world:** the LLM (`core/llm/port.py`), uploaded files (`core/files.py`: `FileStore`), the
    sign-in provider (`core/identity.py`: `IdentityProvider`), sealed secrets (`core/sealing.py`: `Sealer`) and the
    expense tools (`assistant/tools/port.py`: `ExpenseTools`) and the receipt reader
    (`assistant/receipt_agent/port.py`: `ReceiptReader`) are protocols with one adapter each (`GeminiModel` in
    `infrastructure/llm/`; `LocalFileStore` in `infrastructure/files.py`; `OidcIdentityProvider`, standard OpenID
    Connect, in `infrastructure/identity/`, D185; `FernetSealer` in `infrastructure/sealing.py`; `McpExpenseTools` in
    `assistant/tools/mcp_adapter.py`, in-process by default). **Remote agents** sit behind `core/agents.py`
    (`RemoteAgents`), whose one adapter, `A2AAgents` in `infrastructure/a2a/`, is the only code that uses the A2A SDK
    (D201); the modules' own adapters use the port: the assistant's `AgentReceiptReader` (ReceiptReader) and the
    expenses module's `CurrencyAgentRates` (ExchangeRates, D204).
    Each user depends only on what it calls: `/parse` and the receipt agent's reader on `StructuredOutputModel`, the
    agent on `ToolCallingModel`.
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
`expenses.GetMonthlySummary`, never a slice file. The trade-off: `__init__.py` re-exports the messages from their slice
files, so importing a module's package also loads its handlers and tables (not its routes, and not the database engine).
The earlier layout, where the package loaded only a `contracts.py`, gave the lighter import; co-location was judged
worth more. It can't cause an import cycle, because module dependencies run one way: expenses → categories; budgets →
expenses, categories; reports → expenses, categories; mcp → expenses, categories, reports; assistant → the rest;
accounts and receipts depend on none. The mcp package still exports only its `contracts.py` and loads no server code
(D166, D175).

### Why each module owns its tables

If any module can query any table, that table's columns become a promise to everyone. Renaming a column or adding a
rule then means hunting down every place that reads it. When only `expenses` touches the expense table, it can rename
columns, add indexes or move to another database, and nobody else notices, as long as its contract keeps working.

That's also why `expense.category_id` has **no foreign key**. A foreign key would tie the two modules' tables together
at the database level. Instead, `CreateExpense`'s handler asks `categories.GetCategory` whether the category exists.

### Public interfaces today

| Module | Contract (`from app.modules import <name>`) | Used by |
|---|---|---|
| `categories` | `CategoryRead`, `CreateCategory`, `ListCategories`, `GetCategory`, `FindCategoryByName`, `CategoryId`, `MAX_NAME_LENGTH`, `UNKNOWN_CATEGORY`, `CategoryText` (its texts' keys, e.g. `NO_CATEGORIES_YET`) | expenses, mcp, assistant, seed |
| `expenses` | `ExpenseRecorder` (saves an expense, fetching the rate to INR first for another currency, D204; the way REST and MCP save), `ExchangeRate`, `ExchangeRates`, `UnsupportedCurrencyError`, `RatesUnavailableError`, `ExpenseRead` (with the INR amount, rate and date), `ExpenseList`, `CreateExpense`, `UpdateExpense` + `ExpenseChanges`, `DeleteExpense` (with `expected_version`), `GetExpense`, `ListExpenses`, `GetMonthlySummary`, `GetMonthlyTrend` (+ their result types), `ExpenseId`, `MAX_LIST_LIMIT`, `MAX_NOTE_LENGTH`, `PaymentMethod`, `payment_method_label(method, language)`, `ExpenseText` | mcp, assistant (`PaymentMethod`, labels, the note's limit), seed |
| `conversations` | `AppendTurn`, `GetLastTurn`, `GetHistory`, `GetThread`, `ThreadRead`, `ThreadId`, `THREAD_ID_MAX_LENGTH`, `ConversationText` (e.g. `THREAD_NOT_FOUND`) | assistant |
| `mcp` | `ToolName`, `ResourceUri`, `SERVER_NAME`, `acting_for` and `act_for_process` (who a request acts for, D191), the argument names (`EXPENSE_ID_ARGUMENT`, `CONFIRM_ARGUMENT`, `EXPECTED_VERSION_ARGUMENT`, `CLEAR_NOTE_ARGUMENT`), the typed results (`ExpenseView`, `ExpenseSaved`, `MonthSpending`, ...). The server itself (`create_server`, `create_http_app`) comes from `mcp/module.py`, for the composition root only | assistant |
| `receipts` | `ReceiptFiles` (an owner's receipt file: `content(owner_id, receipt_id)` → `ReceiptContent`, bytes and media type), `ReceiptContent`, `ReceiptRead`, `ReceiptId`, `ReceiptMediaType`, `MAX_RECEIPT_BYTES`, `ReceiptText`. Its `module.py` gives the composition root `create_files(bus, files)` and `create_router(bus, files)` | the assistant (sends a receipt attached in the chat to the receipt agent), the export script |
| `assistant` | nothing for other modules; its `module.py` gives the composition root `create_router` (which builds the receipt reader around the remote agents), the `ExpenseTools` port type and `McpExpenseTools` | — |
| `accounts` | `UserId`, `CurrentUser`, `SignedInUser`, `SignInFailure`, `SignInParam`, `SIGN_IN_PAGE`, `CALLBACK_PATH`, `SESSION_LIFETIME`, `LOGIN_ATTEMPT_TTL`. Its `module.py` gives the composition root `create_session_gate(bus, identity, clock)` (the check main.py puts on `app.state.authenticate`), `create_router(bus, identity, sealer, config)` and `SignInConfig` | the composition root, the export script; Phase 23's per-user data will use `UserId` |

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

Handlers raise `NotFoundError`, `BusinessRuleError` or `ExternalServiceError` (e.g. `LlmError`), from
`core/errors.py`, which knows nothing of HTTP. They carry a catalogued text (a `Translatable`), and `web/problems.py`
writes it in the request's language (its `Accept-Language`, else English); it turns them, FastAPI's validation errors
and its own 404/405 into one shape, RFC 9457 problem details:

```json
{"type": "urn:spendwise:problem:not-found", "title": "Not found", "status": 404,
 "detail": "Expense 14 not found", "instance": "/api/v1/expenses/14"}
```

Anything else (a bug) becomes a generic 500 problem in `UnexpectedErrorMiddleware`, the middleware closest to the
routes, so anything added around it sees an ordinary response; the traceback goes only to the log. FastAPI's own
errors keep their headers (`Allow` on a 405) (D165, D184).

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

Every module's route, before any of the above (`main.py` puts these in front of each one; D186):

```
  -> web/auth.py require_csrf  no X-CSRF: 1, or Sec-Fetch-Site from another site -> 403 problem
  -> web/auth.py require_user  the session cookie's key -> app.state.authenticate (accounts' SessionGate):
                               GetSession(hash of the key, today's issuer) -> none live -> 401 problem;
                               renewed (RenewSession) if last renewed over 12 h ago -> the Principal
```

Signing in (`accounts/`; the provider is the `IdentityProvider` port, D185):

```
GET /auth/login?option&return_to   application/sign_in.py begin: ends this browser's old session; asks the provider
                                   for its authorization URL (state, nonce, PKCE challenge); StartLogin stores the
                                   attempt -> 302 to the provider + the login cookie
   ... the person signs in at the provider (Google, GitHub) ...
GET /auth/callback?code&state      finish: TakeLoginAttempt (the login cookie's; once) -> state matches -> the
                                   provider: code -> tokens, every check on the ID token, UserInfo -> role rule ->
                                   SignIn (find or add the user by issuer and subject, a new session, the ID token
                                   sealed) -> 302 to return_to + the session cookie; any failure -> 302 /sign-in?error
GET /auth/logout?sid=<handle>      sign_out.py: EndSession -> 302 to the provider's sign-out page (ID token as hint)
```

The provider is asked outside any database transaction (D164): the attempt is stored before the browser leaves,
taken when it comes back, and the session written only after the provider has answered.

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
| **Open/closed** | New command or query: a slice file plus one `bus.register` line. New MCP tool: a file in `mcp/tools/` with its registrar, plus one entry in `TOOL_REGISTRARS`. New card: one entry in `a2ui/cards.py`'s `_CARDS`. New language: one entry in `Language` and `LANGUAGES` and a `hi.py`-like file per catalog (`define_catalog` names any that's missing). New surface: a class with the `Surface` methods. New module: an entry in `MODULES` |
| **Liskov substitution** | Every adapter can stand in for its port: `McpExpenseTools` in-process or remote, any `LanguageModel`, any `Clock`, any engine |
| **Interface segregation** | `StructuredOutputModel` and `ToolCallingModel` instead of one wide model interface; a module's contract exports only what others use |
| **Dependency inversion** | Use cases depend on protocols (`ExpenseTools`, the model ports, `Clock`); `bootstrap.build()` is the only place that picks implementations |

### Testability

Everything a test would want to replace can be passed in, without patching modules:

- `bootstrap.build(clock=..., llm=..., tools=..., engine=..., files=..., identity=..., sealer=..., agents=...)`
  builds the app's
  services around fakes, and `main.create_app(services)` serves them over HTTP (FastAPI's `TestClient` works directly
  on it; with `base_url="https://localhost"` it keeps the Secure session cookie). A fake identity provider signs a
  test in through the real routes; the OIDC adapter itself takes `transport=httpx2.MockTransport(...)` to talk to a
  fake provider, so the token checks run with no network.
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

## Agent Skills (`skills/`)

**Skills are instructions the model loads when it needs them** (D208). Each is a folder in the repository's `skills/`
(agentskills.io format): a `SKILL.md` with a short `name` and `description` in its frontmatter, then the instructions,
and perhaps `references/` and `assets/` files. The assistant shows them a level at a time (progressive disclosure):

1. every skill's name and description are always in the system instruction (`assistant/skills/SkillTool.rules`);
2. `load_skill(name)` returns the skill's body when the model decides a task matches it;
3. `load_skill(name, file)` returns one of its listed files when the skill says to read it.

The port is `core/skills.SkillLibrary`; its adapter `infrastructure/skills.FolderSkillLibrary` reads the folder once,
keeps only skills that follow the format, and reads only files it listed (never a path the model sends). A skill's
text is the app's own, so it's given to the model as instructions, the one exception to "tool results are data".

**A skill's scripts are run by the server, never by the model** (D209). `SkillLibrary.run_script(name, script,
payload)` runs one of the skill's listed `scripts/*.py` in a child process (`python -I`, no shell, from the skill's
folder), with the payload as JSON on stdin and a 10-second limit, and returns the JSON object it prints. The model has
no tool that runs code and never sees a script: the `monthly-report` skill tells it to call `get_monthly_report`, and
the reports module runs `scripts/compute_report.py` on the person's own expenses and checks the answer
(`reports.MonthlyReport`) before the model or the person sees it. A use case runs a script outside any unit of work.

## The agents (`agents/`), hosted by the backend

**The A2A agents are their own code, outside the monolith's modules** (D12, D195), **and on `main` the backend hosts
them in its own process** (D207): `app/agents_host.py`, part of the composition root, builds each agent's web app with
the backend's model and clock and a random per-process key, and the A2A client reaches them through httpx's ASGI
transport, in memory: no socket, no port, nothing in `.env`. They're still A2A agents (cards, skills, tasks,
input-required), so the backend speaks to them exactly as it would to services. The `multi-server` branch runs each as
its own service on the port below; `run-agent.ps1 <name>` runs one alone on either branch.

| Agent | Port (alone) | Skill | Model | Used by |
|---|---|---|---|---|
| `agents/receipt` (Phase 24) | 9001 | `extract_receipt` | Gemini, one call | the assistant, for a receipt attached in the chat |
| `agents/insights` (Phase 25) | 9002 | `analyze_spending` | Gemini, one call (the tips; the numbers are code) | the assistant, when the model delegates to it (D206); it may stop input-required to ask which month (D205) |
| `agents/currency` (Phase 25) | 9003 | `convert_currency` | none: a `RateProvider` (mock rates for now, D203) | the expenses module, to store every expense in INR too (D204) |

**What they share is the agent kit** (`agents/agent_kit/`, D202): `AgentGate` (the key check, the request limit,
no-store), `ForgetfulTaskStore`, `start_task`/`reject`/`fail`, the settings rules (one `.env`, `127.0.0.1` only, keys of
32+ characters) and `build_agent_app`/`serve`. An agent is then only its contract, its work, its card and its
settings.

**The backend reaches them through one port**, `core/agents.RemoteAgents` (D201): `send(agent, skill, parts,
artifact)` returns the finished task (its id, outcome, the artifact's data, the agent's message). `A2AAgents`
(`infrastructure/a2a/`) fetches each agent's card, refuses one that doesn't offer the skill at the configured
address, and sends the agent's key; it also reads an agent's skills (`skills(agent)`) and resumes a task that stopped
to ask something (`send(..., resume=TaskRef)`). Every call runs on one background event loop (`a2a/loop.py`), where the
hosted agents' state belongs.

**The assistant is the orchestrator** (D206). At startup it reads the insights and currency agents' cards and offers
the model one more tool, `delegate_to_agent(agent, skill, request, month?)`, whose description is the cards' skills
and whose choices are those names. The model decides; the server builds what the agent is sent (the person's data
for insights, the request's line for currency), shows a chip with the A2A task id, and gives the model the checked
answer as data. An agent's question is relayed by the model; the person's next message in that conversation resumes
the same task.

- **A remote agent, not a module.** It has no database, no bus and no person: a client agent (the assistant's
  `AgentReceiptReader`, D199) sends a task (a receipt and the choices it may pick from), the agent works on it and
  answers with an artifact. Whatever the person's data
  needs (who owns the receipt, which categories exist, today's date) stays in the monolith and travels as data.
- **Layout of an agent:** `contract.py` (what travels on the wire), its work (`reader.py`, the model call;
  `rates.py`, the rate provider; `analysis.py`, `months.py` and `tips.py`, the insights), `executor.py` (the
  AgentExecutor: task states and the artifact), `card.py`, `settings.py`, and `server.py`, its composition root
  (`build_app(...)` takes its collaborators, a model or a rate provider and a clock, so a check runs it with fakes).
- **What they may import from the backend** (D196): `app.core` (the LLM port, the schema helpers, money and its
  conversion rule, the clock) and, in a `server.py` only, the Gemini adapter and `setup_logging` from
  `app.infrastructure`. Never a module, `web/`, `bootstrap`, `main` or the backend's settings: those are the
  monolith's, and an agent that needed them would really be a module. In `backend/`, only the composition root's
  `agents_host.py` imports the agents (to host them, D207); no module does.
- **Its own settings** (`AgentSettings` on the kit's configuration, the same `.env`), its own logger (`receipt.*`,
  `currency.*`); `run-agent.ps1` puts `backend` and `agents` on `PYTHONPATH`.

## The web app: Next.js and feature slices

A Next.js 16 app (App Router, D188). The routes and their metadata are rendered on the server; everything signed-in
is drawn in the browser, behind one client boundary.

```
web/
  next.config.ts  the API rewrite (D184), its proxy settings, no compression
  security-headers.ts  the pages' security headers, applied by next.config.ts (D193)
  src/
  app/          Next's route folder and the composition. At its top only Next's files:
                  layout.tsx       the root document: metadata, the theme boot script, the stylesheet (server)
                  not-found.tsx    every unknown address: a real 404, with "Page not found" in the browser
                  robots.ts, sitemap.ts   for search engines: only public pages (today /sign-in)
                  (client)/        the pages drawn in the browser: layout.tsx renders ClientRoot; (app)/ holds the
                                   signed-in routes (page.tsx files, each exporting its metadata) and their layout.tsx
                                   (the session check, then the frame); sign-in/ is the public sign-in page
                and the rest in private folders (a leading "_" is never a route):
                  _shell/          client-root.tsx (starts i18next, then the root error boundary and the providers),
                                   providers.tsx, query-client.ts (the cache and the one refresh rule), namespaces.ts
                                   (the texts loaded at boot), app-crashed.tsx
                  _frame/          app-layout.tsx, app-sidebar.tsx (the frame), pages.tsx (the menu's entries)
                  _views/          client-pages.ts (the client boundary the route files draw pages through),
                                   placeholder-pages.tsx
                  _i18n/           the frame's own texts
                  _seo/            seo.ts: site address (PUBLIC_URL), the public pages, metadata for public and
                                   signed-in pages
                  _styles/         index.css
  features/     one folder per feature, each owning its components, hooks, API calls, types, constants and texts
                (i18n/: en.ts, hi.ts, the namespace and its useTexts hook):
    expenses/     the Expenses page; components/ grouped into table/, dialogs/, filters/, fields/; api.ts, queries.ts
    categories/   categories API and queries, CategorySelect, category names
    dashboard/    the Dashboard page, stat cards, charts, recent list; api.ts, queries.ts
    assistant/    the chat panel; model/ (useChat, AssistantProvider); api/ (the AG-UI stream); a2ui/ (renderer)
    auth/         the sign-in page, AuthGate (the session check in front of the signed-in pages), the user menu
    account/      the Settings page: profile, sessions (sign out one or all others), personal access tokens
  shared/       knows no feature: ui/ (shadcn kit), api/ (typed HTTP client, generated contract), config/ (app name,
                routes, data scopes), i18n/ (the languages and their locales, the i18next setup, the language
                menu, shared/'s "common" texts), lib/ (formatting, guards, errors, ids), components/ (empty state,
                error boundary, section error, refresh notice, placeholder page, labeled field), hooks/, theme/
```

### The rules

1. **A feature owns everything it needs.** Nothing about expenses lives outside `features/expenses/`.
2. **Other code imports a feature only through its `index.ts`** (`@/features/expenses`), never a file inside it.
   Inside a feature, imports are relative. Fewer cross-feature imports is better.
3. **`shared/` imports no feature and not `app/`. Only `app/` wires features together.** For example, a mutation only
   declares `meta: { changes: DATA_SCOPES.expenses }` and the assistant only reports "data changed"; one table in
   `app/_shell/query-client.ts` (`STALE_AFTER`, applied by `refreshAfter`) decides that means reloading the expenses and
   Dashboard queries (D168, D172).
4. **Server data goes through TanStack Query** (each feature's `queries.ts`): no fetching in effects, outdated requests
   cancelled, changes invalidate their keys.
5. **Nothing is copied from the backend by hand:** API types come from `schema.gen.ts`, protocol names and labels from
   `contracts.gen.ts` (both generated).
6. **Defined once:** the app's name (`APP_NAME`) and description, the menu (`PAGES`; the routes are their files),
   the theme's boot script (generated from `theme-constants.ts`, put into `<head>` by the root layout) (D169, D188).
7. **A failure stays small:** error boundaries at the root, the page area, the chat panel and every A2UI card; a page
   keeps its data with a "couldn't refresh" notice when a reload fails; code that fails to load can be retried
   (`lazyWithRetry`).
8. **Logic outside components:** what can be a pure function is one (the chat transcript and run progress, SSE
   framing, A2UI actions and chart data, query status), and components and hooks stay small: a file under about 150
   lines of code, a component or hook under about 60. The A2UI renderer draws from catalog tables (`catalogs.ts`), not
   a switch (D172).
9. **Load on demand:** each feature's `index.ts` exports its page through `lazyWithRetry`; the chat panel is loaded the
   same way, in the background, so the first page doesn't wait for code it doesn't need (D174).
10. **Every text from a namespace, loaded with what uses it** (D178). Each feature (and `app/`, and `shared/` as
    "common") owns its texts in `i18n/`: English in `en.ts` is the source, and each other language is a file with
    the same keys. Every file is its own chunk: a page's (or the chat panel's) load together with its code, from its
    lazy loader, and "common", the frame's and the auth feature's texts load when the app boots (their English
    bundled, so the frame, with its session check and user menu, can always be drawn). Keys are typed, so a
    misspelt key or a translation missing one fails the build. A language switch loads the new language for the
    namespaces in use, then redraws; numbers and dates follow the language's locale. The app speaks English and Hindi.

11. **Server and browser apart** (D188). A route file is a server component: it exports `metadata` and draws a page
    from `_views/client-pages.ts`, the client boundary. Under `(client)/`, `ClientRoot` draws nothing on the server,
    so browser-only code (saved language and theme, window width) never runs there; a page that should be fully
    rendered on the server (a landing page) goes outside `(client)/`.

12. **Signed in, or sent to sign in** (D189). Every route in `(client)/(app)/` is behind `AuthGate`, which asks the
    server who is signed in (`GET /auth/user`; its 401 means nobody). Any other request's 401 makes the query client
    ask again, so the rule lives in one place and features never handle a 401. Signing in and out are navigations to
    the backend's routes; the browser holds no token. A page never outlives its person (D192): when the session ends
    or someone else signs in in another tab, the page is unloaded, so nothing of one person stays on screen for the
    next.

`.oxlintrc.json` enforces rules 2 and 3 (`no-restricted-imports`, including relative imports out of a feature at
every folder depth, relative imports out of `shared/` and deep imports from `app/`); `npx oxlint` fails on a
violation. It also runs the `jsx-a11y` accessibility rules. Route files (`page.tsx`, `layout.tsx`, `not-found.tsx`)
may export `metadata` beside their component (Next's convention), so the fast-refresh rule is off for them only.

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

## One origin

The browser reaches the API on the web app's own address (D184). The web app calls relative URLs (`/api/v1/...`;
`api` has no base URL, and the assistant's stream uses a relative path), and whatever serves the page forwards them
to the backend:

```
browser --> http://localhost:5173/            Next.js serves the web app (npm run dev, or npm run start)
        --> http://localhost:5173/api/v1/...  Next's rewrite (next.config.ts) --> http://127.0.0.1:8000/api/v1/...
production: one reverse proxy in front of both: pages to Next.js, /api/v1/ to Next.js too (or straight to uvicorn)
```

- **No CORS.** The API sends no `Access-Control-*` headers, so no other website can read its answers in a browser,
  and a cross-origin preflight fails. There's no allow-list to keep in step with the web app's address.
- **Next's rewrite runs before the routes** (`beforeFiles`), so no page can claim `/api/v1/`. Its proxy needs two
  settings: `compress: false` (it would gzip the assistant's Server-Sent Events and hold them back) and
  `experimental.proxyTimeout` of 180 s (its default 30 s of silence would cut off `/parse` and receipt reading,
  which wait up to 2 × 60 s on Gemini). The target (`API_PROXY_TARGET`) is compiled into the build.
- **Next's proxy sends the backend's own address as `Host`** (the browser's goes in `X-Forwarded-Host`), so URLs
  the backend builds, such as a new expense's `Location`, name the backend's address. The web app never reads them.
- **When the backend can't be reached, the server in front answers for it:** Next.js with 500 in plain text, a
  reverse proxy with 502, 503 or 504. The backend's own errors are always problems, so `ApiError.fromProblem` reads
  any 5xx that isn't one as "can't reach SpendWise".
- **Why:** the sign-in of Phase 22 keeps the session on the server and gives the browser one HttpOnly cookie. On one
  origin that cookie can be `SameSite=Strict` with the `__Host-` prefix, and needs no CORS credentials (the Duende BFF
  pattern).
- MCP clients, Swagger UI (`/docs`) and `curl` still talk to `http://127.0.0.1:8000` directly.

## Checking the rules

The web app's rules are checked by `npx oxlint` in `web/`. The backend has no automated check at the moment (the
architecture test was removed with the other tests, D64), so run these scans from the project folder:

```powershell
# 1. Shared code grouped by concern (D177). Expect no output from any of the four: core/ imports nothing else in
#    the app; infrastructure/ and web/ import only core/; no module imports infrastructure/.
Get-ChildItem backend\app\core -Recurse -Filter *.py |
  Select-String -Pattern '^\s*(from|import)\s+app\.(modules|infrastructure|web|bootstrap|main)\b'
Get-ChildItem backend\app\infrastructure -Recurse -Filter *.py |
  Select-String -Pattern '^\s*(from|import)\s+app\.(modules|web|bootstrap|main)\b'
Get-ChildItem backend\app\web -Recurse -Filter *.py |
  Select-String -Pattern '^\s*(from|import)\s+app\.(modules|infrastructure|bootstrap|main)\b'
Get-ChildItem backend\app\modules -Recurse -Filter *.py | Select-String -Pattern 'app\.infrastructure\b'

# 2. Imports of a module's files. Every line must be inside that same module's folder (expenses/commands/
#    create_expense.py importing app.modules.expenses.persistence.repository is fine; anything else isn't).
Get-ChildItem backend\app\modules -Recurse -Filter *.py | Select-String -Pattern '^\s*from\s+app\.modules\.\w+\.'

# 3. Only the composition root imports a module.py. Expect bootstrap.py and main.py.
Get-ChildItem backend -Recurse -Filter *.py | Select-String -Pattern 'import module as' | Split-Path -Leaf | Sort-Object -Unique

# 4. Only a composition root picks the LLM provider. Expect bootstrap.py, the adapter (infrastructure/llm/gemini.py)
#    and the receipt and insights agents' server.py (the currency agent uses no model).
Get-ChildItem backend, agents -Recurse -Filter *.py | Select-String -Pattern 'llm\.gemini|from google'

# 5. Inside the assistant, imports run api/ -> application/ -> agent/, approvals/, tools/, receipt_agent/,
#    delegation/, skills/, a2ui/, never back.
#    Expect only module.py, which builds the router and the use cases.
$assistant = Get-ChildItem backend\app\modules\assistant -Recurse -Filter *.py
$assistant | Where-Object FullName -NotMatch '\\assistant\\api\\' | Select-String -Pattern 'assistant\.api\b'
$assistant | Where-Object FullName -NotMatch '\\assistant\\(api|application)\\' |
  Select-String -Pattern 'assistant\.application\b'

# 6. Each module package imports on its own, in a fresh interpreter. Expect no output. An error here usually means
#    an import cycle between modules (importing a package also loads its slices, D175).
foreach ($m in "accounts", "categories", "conversations", "expenses", "budgets", "mcp", "receipts", "reports",
             "assistant") {
  .\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); import app.modules.$m"
}

# 7. Only a module's HTTP adapters import web/. Expect api.py (accounts, budgets, categories, conversations,
#    expenses, receipts, reports), account_api.py (accounts), http.py (mcp) and routes.py (the assistant's api/).
Get-ChildItem backend\app\modules -Recurse -Filter *.py | Select-String -Pattern 'app\.web\b' | Split-Path -Leaf |
  Sort-Object -Unique

# 8. No identity provider's name in the code (D185): the provider is configuration. Expect no output.
Get-ChildItem backend\app, web\src -Recurse -Include *.py,*.ts,*.tsx | Select-String -Pattern 'zitadel'

# 9. A person's data is never looked up by its id alone (D190): the owner goes in the same statement. Expect only
#    take_approval.py, which compares the owner on the next line.
Get-ChildItem backend\app\modules\expenses, backend\app\modules\budgets, backend\app\modules\conversations,
  backend\app\modules\receipts, backend\app\modules\assistant -Recurse -Filter *.py |
  Select-String -Pattern 'session\.get\(' | Split-Path -Leaf

# 10. The agents (and the kit) use only the backend's core/, and the Gemini adapter and logging in a server.py (D196);
#     in the backend only agents_host.py imports them (D207). Expect no output from the first two, and agents_host.py
#     alone from the third.
Get-ChildItem agents -Recurse -Filter *.py |
  Select-String -Pattern '^\s*(from|import)\s+app\.(modules|web|bootstrap|main|infrastructure\.config)\b'
Get-ChildItem agents -Recurse -Filter *.py | Where-Object Name -NE server.py |
  Select-String -Pattern '^\s*(from|import)\s+app\.infrastructure\b'
Get-ChildItem backend -Recurse -Filter *.py |
  Select-String -Pattern '^\s*(from|import)\s+(receipt|insights|currency|agent_kit)\b' | Split-Path -Leaf |
  Sort-Object -Unique

# 11. The agents import and compile on their own. Expect no output.
$env:PYTHONPATH = "backend;agents"
.\.venv\Scripts\python.exe -c "import receipt.server, insights.server, currency.server"
Remove-Item Env:PYTHONPATH
.\.venv\Scripts\python.exe -m compileall -q agents

# 12. Only infrastructure/a2a uses the A2A SDK in the backend (D201): modules use core/agents.RemoteAgents. Expect
#     agents.py alone.
Get-ChildItem backend\app -Recurse -Filter *.py | Select-String -Pattern '^\s*(from|import)\s+a2a\b' |
  Split-Path -Leaf | Sort-Object -Unique
```
