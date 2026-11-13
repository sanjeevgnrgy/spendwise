# Architecture Review

A record of the architecture review of the whole codebase after Phase 18, the code reviews of the refactor that
followed, what each one found, and how each finding was resolved. Decisions are in [decisions.md](decisions.md)
(D139–D170); the refactor's learning notes in [phases/refactor-architecture.md](phases/refactor-architecture.md).

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
