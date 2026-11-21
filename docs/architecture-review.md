# Architecture Review

A record of the architecture review of the whole codebase after Phase 18, the code reviews of the refactor that
followed, the SOLID review after that, what each one found, and how each finding was resolved. Decisions are in
[decisions.md](decisions.md) (D139–D174); the phase notes in [phases/refactor-architecture.md](phases/refactor-architecture.md)
and [phases/refactor-solid.md](phases/refactor-solid.md).

## The standards

The review measured the code against six requirements:

1. **No magic strings:** every name, key, label and limit defined once and referenced.
2. **No duplicated code or values.**
3. **A strict modular monolith with CQRS** in the backend.
4. **Strict feature slices** in the web app (plain feature folders, not the Feature-Sliced Design methodology).
5. **No tight coupling** in either.
6. **Industry best practice:** security, correctness, transactions, typing, migrations, accessibility.

## Verdict before and after

| Standard | Before (after Phase 18) | After |
|---|---|---|
| Modular monolith | Partly: imports respected boundaries, but `assistant` did everything and read MCP results as untyped JSON | Met: five modules with contracts, a composition root, typed tool results, enforced by a static check |
| CQRS | Not met: one service per module mixing reads and writes; a delete tool that was also a preview | Met: commands and queries through a bus that is the unit of work |
| Feature slices | Not met: folders by file type; one `api.ts` for everything | Met: `app/`, `features/*`, `shared/`, enforced by lint |
| No magic strings | Not met: tool names, events, routes, currency repeated in two languages | Met: enums and constants, and a generated contract for the web |
| No duplication | Partly: payment methods in 5 places, types copied by hand | Met: one definition each, generated across the stack |
| No tight coupling | Not met: Gemini's format in the database, AG-UI in the service, tool names in the UI | Met: ports and adapters, provider-neutral storage, labels from the backend |

## 1. The architecture review (after Phase 18)

### Backend

| # | Finding | Resolution |
|---|---|---|
| B1 | Cards and approvals read MCP results by dictionary key from JSON strings | Tools return typed Pydantic results (`outputSchema` / `structuredContent`); cards validate them (D144) |
| B2 | Chat history stored in Gemini's wire format | Provider-neutral messages in a new conversations module; migration 0002 converted the history, losslessly (D141) |
| B3 | The service built AG-UI events | Use cases yield plain events; `agui.py` is the adapter (D147) |
| B4 | `assistant` did everything | Conversations split out; layers inside the assistant (api, agui, turns, agent, tools, approvals, a2ui) |
| B5 | The app called its own HTTP port for tools | The MCP SDK's `Client` calls the server in-process; `MCP_URL` only for a separate server (D143) |
| B6 | Approvals in process memory | The `pending_approval` table (D146) |
| B7 | Tables registered by importing routers | `module.py` per module; `bootstrap.py` is the composition root (D140) |
| B8 | No command/query separation | `core/cqrs.py`: commands, queries, a bus (D139) |
| B9 | `delete_expense(confirmed=false)` was a preview: a read and a write in one | `get_expense` (query); `delete_expense` deletes, with a strict interlock (D145) |
| B10 | Repositories committed; one depended on an HTTP schema | The bus commits once per command; query handlers build their own SQL |
| B11 | Gemini's step and event names as literals | Enums inside the Gemini adapter (D142) |
| B12 | Tool and action names repeated | `ToolName`, `ActionName` enums |
| B13 | Protocol keys (`a2ui`, `a2uiAction`, `dataVersion`) repeated | `assistant/protocol.py`, exported to the web |
| B14 | Currency regex ×5, `"INR"`, `"₹"` | `CURRENCY_PATTERN`, `CurrencyCode`, `CURRENCY_SYMBOLS` |
| B15 | `"Unknown"`, a repeated message, a stale version, hand-typed logger names | `UNKNOWN_CATEGORY`, `NO_CATEGORIES_YET`, `API_VERSION`, `getLogger(__name__)` |
| B16 | Payment methods in five places | `PaymentMethod` + `PAYMENT_METHOD_LABELS`, generated for the web |
| B17 | Category lookup by name, twice | the `FindCategoryByName` query |
| B18 | `YYYY-MM` parsed and formatted in four places | the `YearMonth` value object |
| B19 | Result parsing repeated | gone with B1 |
| B20 | No migrations | Alembic, 0001–0003 (D148) |
| B21 | No auth; `/ask` an open proxy to Gemini | `/ask` removed; `/mcp/` behind a bearer token; user login deferred to the auth phase (D150, D161) |
| B22 | Two error shapes; no API version | RFC 9457 problem details; `/api/v1` (D149) |
| B23 | `date.today()` in four places | a `Clock` (D151) |
| B24 | User messages and tool arguments logged at INFO | DEBUG only (D152) |
| B25 | Weak typing (`dict` steps, bare `str` events, a lying `ExpenseUpdate`) | neutral message models, `TextDelta`, `ExpenseChanges` with a null check |

### Web

| # | Finding | Resolution |
|---|---|---|
| W1 | Not feature-sliced | `app/`, `features/{expenses,categories,dashboard,assistant}`, `shared/`, lint-enforced (D153) |
| W2 | `api.ts` held everything | `shared/api/http.ts` + each feature's `api.ts` |
| W3 | Pages synced through a version counter in effects | TanStack Query with invalidation (D154) |
| W4 | The tool chip knew MCP tool names and arguments | labels sent by the backend (D157) |
| W5 | The layout owned the chat state | `AssistantProvider` in the assistant feature |
| W6 | Route strings repeated | `ROUTES` and one `PAGES` list |
| W7 | Protocol names, locale and magic numbers as literals | the generated contract, `shared/config`, named constants |
| W8 | Backend types and labels copied by hand; duplicated chart configs and helpers | generated types (D155); shared config and helpers |
| W9 | Money formatted two ways | one rule on both sides (D159) |
| W10 | Network data trusted by cast | openapi-fetch typed client; AG-UI events validated with `@ag-ui/core` (D156) |
| W11 | No error boundary | boundaries around cards and the page (D158) |
| W12 | No cancellation; no Stop | abort signals; a Stop button (D158) |
| W13 | Dependencies on `^` ranges | exact pins (D160) |
| X1 | No shared contract | `export_contracts.py` + `npm run gen:api` (D155) |

## 2. The code reviews of the refactor

Two independent reviews read the refactored code, one per side, and reproduced what they could with scratch scripts.

### Backend

| # | Finding | Severity | Resolution |
|---|---|---|---|
| 1 | Approve's check and the delete were separate steps: an edit in between would be deleted unseen | bug | `expense.version` + `DeleteExpense.expected_version`, checked in the `DELETE` statement itself (D162) |
| 2 | Migration 0002 wasn't atomic on SQLite: one bad row left the database stuck | bug | SQLite made transactional (DDL included); migrations run in one transaction (D163) |
| 3 | Every database error reported as "busy" | bug | only lock errors are "busy"; `mcp_stdio.py` migrates on import |
| 4 | Timestamps declared without time zone in migrations | latent bug | `DateTime(timezone=True)` in tables and migrations |
| 5 | `/parse` held a database connection during the model call | bug | a use case: categories read first, the model called with no session open (D164) |
| 6 | A 500 response had no CORS headers | bug | an error middleware inside CORS (D165) |
| 7 | FastAPI's own errors lost their headers (a 405's `Allow`) | bug | headers kept |
| 8 | Putting a card back depended on garbage collection, and reset its age | bug | the decision completes before streaming; `RestoreApproval` keeps the original time (D164) |
| 9 | The MCP bearer scheme was case-sensitive | bug | case-insensitive, per RFC 9110 |
| 10 | `/agent` validated its input inside the stream | bug | a dependency checks it first: 422 before streaming (D167) |
| 11 | Nested commands had no savepoint | latent bug | `begin_nested()` for a command inside a command |
| S1 | `TakeApproval`, a command, returns data | standard | kept on purpose and documented: take-and-read must be one step, like a queue |
| S2 | The LLM port was tied to Gemini and not injected | standard | `LanguageModel` protocol; `GeminiModel` built in `bootstrap.py` and passed in (D166) |
| S3 | Directly imported packages not pinned | standard | `sqlalchemy`, `starlette`, `httpx2` pinned |
| S4 | MCP argument names typed twice | standard | descriptions built from the contract's names; a start-up check of each tool's parameters |
| S5 | Duplicated values (id bounds ×4, a copied length, form fields ×2, a second problem body, a second MCP server) | standard | `RecordId`/`IdPath`, `MAX_NAME_LENGTH`, `FIELD_DESCRIPTIONS`, `problem_response()`, `bootstrap.build().mcp_server` |
| S6 | Importing the mcp contract loaded the server; the assistant stored another module's DTO | standard | the mcp package exports only its contract (server via `module.py`); approvals store their own `ExpenseSnapshot` (D166) |

### Web

| # | Finding | Severity | Resolution |
|---|---|---|---|
| 1 | A form could be sent twice if a run broke off while a tool ran | bug | it stays locked when the server *may* have changed data |
| 2 | Saving one row closed another being edited | bug | save state and closing are per row |
| 3 | Assistant text messages joined without a break | not a bug | the backend already starts text after a tool call with a paragraph break |
| 4 | Category loading and errors were invisible ("Unknown", empty dropdowns) | bug | names blank while loading; the dropdown shows loading or error; the Dashboard waits for categories |
| 5 | A failed refresh replaced a loaded Dashboard with an error card | bug | data stays with a "couldn't refresh" notice; Retry only refetches what failed (D168) |
| 6 | Raw or wrong error messages (bad JSON reported as "backend down") | bug | only a network error is "can't reach"; a lost stream says so plainly |
| 7 | Enter during IME composition saved the edit row | bug | ignored while composing |
| 8 | The delete dialog flashed "Delete 0 expenses?"; double deletes possible | bug | keeps its content while closing; delete buttons disabled during a delete |
| 9 | The A2UI size check could overflow the stack on a deep chain | bug | a depth limit inside the check |
| 10 | A2UI limits, chart types and component names hard-coded | standard | generated from the backend; the spec's vocabulary named once (`basic-catalog.ts`) (D169) |
| 11 | "Expenses changed" wired in two places | standard | mutations declare `meta.changes`; one rule in `app/query-client.ts` (D168) |
| 12 | Lint gaps (no `app/` rule, relative escapes from `shared/`, no a11y plugin) | standard | added and verified with deliberate violations |
| 13 | Accessibility gaps | standard | labelled controls, `aria-sort`, a `role="log"` transcript, readable failure reasons, native list and status elements |
| 14 | Currency text, page titles and the app name repeated | standard | `DEFAULT_CURRENCY`, `PAGES`, `APP_NAME` |
| 15 | Theme rules written twice (`index.html` and React) | standard | one module; Vite injects the boot script (D169) |
| 16 | The category dropdown reimplemented; client-side chip labels duplicated | standard | `CategorySelect` with an "All" option; the client keeps only a bare fallback |
| 17 | `/agent` path built by hand; thread-id length assumed | standard | `AGENT_PATH satisfies keyof paths`; `LIMITS.threadIdLength` |
| 18 | `VITE_API_URL` typed as `any` | standard | `vite-env.d.ts` |
| 19 | No error boundary outside the page area | standard | boundaries at the root and around the chat panel (D168) |

## 3. Deliberately not changed

| Item | Why |
|---|---|
| Login for the REST API and the web app | a feature with its own phase (auth), not a refactor; see [security.md](security.md) |
| Two runs on one thread at once storing the same turn number | the panel sends one message at a time; revisit with multiple devices |
| Every bubble re-rendering on each streamed token | fine at chat sizes; memoize if long chats feel slow |
| Splitting the bundle by page | the assistant, always loaded, already pulls in the chart library |
| `TakeApproval` returning data | take-and-read must be atomic (S1) |
| A 405's `Allow` lists only one method | that's how Starlette matches per-method routes; the header now reaches the client |
| The `dark` class name also in `index.css` | Tailwind's `@custom-variant` lives in CSS and can't import TypeScript; the comment points to the constant |

## 4. How it was verified

- **Migrations** up, down and up again on a copy of the real database; the chat history converted both ways with the
  original rows reproduced exactly; a failing upgrade left the database untouched.
- **Backend** on temporary databases: the bus (rollback, unit of work, savepoints, nested queries), every REST route
  and problem response, MCP over the real protocol (in-process and HTTP, token, Host and Origin checks), and every
  agent flow with a scripted fake model (cards, approvals including stale, foreign, edited and replayed cards, forms,
  text-mode deletes).
- **Web** loaded through Vite's SSR loader against that backend: API calls, the validated stream, cards, Stop, and both
  pages rendered with TanStack Query data; `tsc -b`, `oxlint` and `npm run build` clean.
- **Static checks:** no `core/` import of a module, no reach into another module's files, no wiring import outside the
  composition root; no leftover literals outside their definitions.

## 5. The SOLID review

A review against single responsibility and the other SOLID principles, clean code, god files, testability and
scalability, with no change to what the app does. Decisions D172–D174.

### Backend

| # | Finding | Resolution |
|---|---|---|
| B1 | `assistant/agent.py` did four jobs (prompt, web-panel tool filtering, the loop, Approve/Cancel), switched by a `rich_ui` flag; the turn's ending was written twice | `prompts.py`, `surfaces.py` (`WebPanel`, `TextChat`), `tool_runs.py`, `decisions.py`; `Agent.run(surface)` with one `_Turn` |
| B2 | `mcp/server.py`: one 185-line `create_server`; one expense's category found by loading all of them | registrars in `read_tools.py` / `write_tools.py` / `resources.py`, `TOOL_REGISTRARS`, `views.py`; one lookup |
| B3 | fakes couldn't reach the HTTP app; the tools adapter and the engine were hidden | `build(clock, llm, tools, engine)`, `create_app(services)`, `create_db_engine` |
| B4 | the Gemini adapter read global settings, kept a singleton client and mixed SDK calls with pure reassembly | `GeminiModel(api_key, model, client_factory)`; `gemini_wire.py` (pure) |
| B5 | `agui.py` read input and wrote output | `agui_request.py` |
| B6 | the model port was wider than its users; `/parse` reached into the assistant | `StructuredOutputModel`, `ToolCallingModel`; `ExpenseParser`; its schema cached |
| B7 | the tools adapter switched on type in two places; categories read untyped | a connector chosen once; a typed reader |
| B8 | unused A2UI types; two tables stamped their own time | removed; time only from the clock |
| B9 | scalability limits (thread and connection pools, SQLite writers, unpaged threads, remote MCP sessions) | documented ([architecture.md](architecture.md#scalability)); a (thread_id, turn) index added (0004) |

### Web

| # | Finding | Resolution |
|---|---|---|
| W1 | `use-chat.ts`: a god hook (types, list operations, the run, the event switch, decoding, the unlock rule) | `chat-types.ts`, `transcript.ts`, `run-progress.ts`, `use-agent-run.ts`, `api/agent-events.ts`; the stream function injected |
| W2 | `expenses-table.tsx`: a god component; a sortable header copied five times | columns, sort button, toolbar, editor hook; one `sortableHeader` |
| W3 | the A2UI renderer was a set of switches | `CATALOGS` registry; components, actions and chart data in their own files |
| W4 | every keystroke and streamed token redrew every card | the composer holds its own text; memoised bubbles and surfaces |
| W5 | one 1.25 MB bundle; a `lazy()` in `app/` would split nothing | pages and the chat panel load on demand from each feature's index: 541 kB at start |
| W6 | `agent-stream.ts` mixed fetching, SSE framing and validation | `sse.ts` |
| W7 | form plumbing copied between the dialog and the edit row | `useExpenseDraft`, `LabeledField` |
| W8 | the Dashboard's retry rule written inline | `shared/lib/query-status.ts` |
| W9 | the refresh rule was one `if` per data scope | `STALE_AFTER`, checked by the compiler |

### Reviews of the result

Two more independent reviews read the finished code against the old. Neither found a behaviour regression; the
new abstractions (surfaces, the split port, the registries) were judged justified, not needless indirection.

| Finding | Resolution |
|---|---|
| `lazyWithRetry` swapped in a fresh load the moment one failed; React draws again on failure, so it retried forever behind a blank area | the failed load stays (the error boundary shows it) until **Try again** renews it; checked in headless Edge with the chunk blocked |
| Migrations could only target `DATABASE_URL`; an in-memory engine gave each thread its own database | `upgrade_to_latest(engine)`; `StaticPool` for in-memory SQLite |
| With a remote MCP server just restarted, Approve could report an error after its delete was saved (it was already so before the refactor) | `changes_data` assumes "may have changed" when the tool list can't be fetched |
| Importing `app.main` built the whole app; importing a contract created the database engine | uvicorn's factory mode; `core/ids.py` |
| Comments left behind by moved constants; `new_session` unused; one parse written twice; two misleading comments in the chat | fixed |
| Found while implementing: concurrent row saves lost toasts; ids needed `crypto.randomUUID`; an unused `API_URL`; a duplicated "thread not found" text; the bearer scheme spelled in two places | fixed |
| Kept on purpose: two `react/static-components` suppressions (the renderer comes from a fixed table; the alternative calls hooks in a varying order) | recorded in the code |

### How it was verified

- **Backend behaviour:** 22 scenarios through the HTTP API, with a scripted fake model plugged in at the model port,
  recorded before and after: every AG-UI event, REST response and model call, the MCP tool listing and the OpenAPI
  document. Identical, after every change, including the review fixes.
- **Backend edges:** the old and new agent loop side by side on paths the scenarios miss; the old and new Gemini
  adapter fed the same SDK events (15 cases); migrations up, down, up and check; migrating injected file and
  in-memory engines and serving them over HTTP; uvicorn's factory mode.
- **Web:** `tsc -b`, `oxlint`, `npm run build`; then headless Edge against the backend with the fake model: both pages
  render with data; the chat panel loads on demand, draws the insight card's chart, and an approved delete is carried
  out; a blocked page and a blocked chat panel each show the error and recover with Try again.

## 6. The code review of 2026-11-21

A review of the whole codebase (336 Python files, 190 TypeScript files) for god files, industry practice, SOLID and
DRY, magic strings, clean code, structure and coupling, measured by scripts (file, function and folder sizes, repeated
code, literals, imports, the dependency graph) before reading the hot spots. Decisions: D212, D213. What changed:
[phases/refactor-code-quality.md](phases/refactor-code-quality.md).

| # | Finding | Resolution |
|---|---|---|
| 1 | Two long-lived branches kept in step by hand | Kept: the owner's choice; `multi-server` gets this review separately |
| 2 | The verification scripts live outside the repo | Open: AGENTS.md rule 2 leaves tests to the owner; the scripts are offered as material |
| 3 | No CI, no Python linter, formatter or type checker; rule scans copied by hand | Fixed: Ruff, Pyright, Prettier, `check_rules.py`, `check.py`, CI (D213) |
| 4 | Budget warnings only on the assistant's save path | Fixed: `SaveWatcher` port, notices on the REST saves (D212) |
| 5 | Docs drifted (decision range, the composition root's signature) | Fixed; the range is no longer written down |
| 6 | Adding a module touches the composition root in several places | Kept: an explicit composition root is pure DI, readable in one place |
| 7 | Folders past the eight-file rule (web `a2ui/`) | Fixed: `renderers/`, `buttons/` |
| 8 | The agents' card builders repeated | Fixed: `agent_kit.card` |
| 9 | `Agent.run` did two jobs; `export_contracts.main` 71 lines | Fixed: split |
| 10 | Chat roles and statuses as literals | Fixed: named constants, a style table |
| 11 | Two large files (A2UI models, the assistant's texts) | Fixed: split into packages |
| 12 | Machine-quality Hindi | Open: needs a native speaker |
| C1 | Settings and the database engine built at import | Fixed: `get_settings()`, `default_engine()` |
| C2 | A business rule (budget alerts) in the MCP adapter | Fixed: moved into budgets (D212) |
| C3 | Import-time `assert`s | Fixed: explicit checks that raise |

The tools then found what reading hadn't: two annotations naming something not imported (one new, one older), a
protocol its implementations didn't satisfy, untyped construction of messages from untrusted input, and more (D213).
The coupling scan found the module and feature graphs exactly as allowed: no cycles, no reach into another module's
files, nothing in `shared/` that knows a feature.
