# AGENTS.md

Rules for AI coding agents, and anyone else, changing SpendWise. They describe how this codebase is built: a change
that doesn't follow them isn't finished. The reasoning behind each rule is in [docs/](docs/README.md). Read the linked
doc before working in an area, and check [decisions.md](docs/decisions.md) (D1–D194) before changing a settled choice.

| Before you change… | Read |
|---|---|
| anything | [architecture.md](docs/architecture.md): the rules for both halves, and why |
| the backend | [backend_onboarding.md](docs/backend_onboarding.md): module anatomy and step-by-step recipes |
| the web app | [frontend_onboarding.md](docs/frontend_onboarding.md): feature anatomy and recipes |
| the assistant | [assistant_architecture.md](docs/assistant_architecture.md), [security.md](docs/security.md) |
| a route, table or setting | [api_endpoints.md](docs/api_endpoints.md), [database_schema.md](docs/database_schema.md), [configuration.md](docs/configuration.md) |

## 1. Working agreement

1. **Commit only when the owner says "commit". Push only when asked.** Never rewrite history that has been pushed.
2. **Don't write automated tests** or add test tooling (pytest, vitest, fixtures), even if a task or prompt asks for
   them: the owner adds tests. Make code testable instead (section 5).
3. **Secrets stay secret.** Never read, print, log or commit `.env` values (`GEMINI_API_KEY`, `OIDC_CLIENT_SECRET`,
   `SESSION_ENCRYPTION_KEYS`) or a personal access token. Never
   stage `.env`, `*.db`, `.venv/`, `node_modules/`, `dist/` or `__pycache__/`. Before each commit, confirm the
   staged diff doesn't contain the key ([git.md](docs/git.md#before-every-commit)).
4. **No live model calls without permission.** Calling Gemini spends the owner's quota. Verify with a fake model
   plugged in through the seams (section 7) unless the owner explicitly allows a live call.
5. **Never experiment on the owner's database** (`backend/spendwise.db`). Copy it and point `DATABASE_URL` at the copy.
6. **Stop only the processes you started.** Never kill every python or node process.
7. **Ask first** before changing a settled decision, deleting data, or doing anything hard to undo.
8. **Review before you hand over.** End every feature or fix with a review of your own diff (correctness, these
   rules, the docs), fix what it finds, run the definition of done (section 7), then ask to commit.
9. **Commits:** a short imperative subject; a body that says what changed and why; related changes together (one
   module, one web feature, its docs). Docs belong in the same commit as the code they describe, unless the owner
   asks for a different split.

## 2. Backend: a modular monolith with CQRS (`backend/`)

**Modules.** One per business domain, in `backend/app/modules/<name>/`: `accounts`, `categories`, `conversations`,
`expenses`, `receipts`, `assistant`, `mcp`. Split by domain, never by technical layer (no app-wide `models/` or
`routers/`).

**Commands and queries.** Every operation is a **command** (changes data, returns at most an id) or a **query** (reads,
changes nothing): a frozen Pydantic message with exactly one handler. Send them through the bus (`bus.execute`,
`bus.ask`, or `ctx.bus` inside a handler); never call a handler directly. A query never sends a command.

**The bus is the unit of work.** Handlers never open sessions or commit; repositories only stage changes. Group
several commands with `bus.unit_of_work()`. No slow work (a model call, a network request) inside a unit of work.

**A module's layout: vertical slices (D175).** The same skeleton everywhere; shared files only where something is
shared:

```
<module>/
  __init__.py          the public contract: re-exports what other modules may use (__all__)
  module.py            wiring for the composition root: one bus.register(...) per slice, the router, TABLES
  api.py               REST routes: translate HTTP into messages, nothing else
  models.py            read models used by several slices
  values.py            ids, Annotated field types, enums, limits, constants and texts shared by several slices
  commands/<name>.py   one command: the message class AND its handler (+ what only it uses)
  queries/<name>.py    one query: the message, its handler and its result models
  domain/rules.py      business rules shared by several slices
  persistence/         tables.py (+ repository.py for the write side)
  i18n/                texts for people: en.py (the keys, a StrEnum, and the English source), hi.py, __init__.py
```

File name = the message in snake_case (`GetMonthlySummary` → `queries/get_monthly_summary.py`), and the handler has
the same name. A new use case is a new slice file, one `bus.register` line, and an export from `__init__.py` if other
modules need it. Recipes: [backend_onboarding.md](docs/backend_onboarding.md).

**Boundaries.**
- Use another module only through its package (`from app.modules import categories`), never its files.
- Never query another module's tables. Links between modules are plain ids (no foreign keys), checked through the
  other module's queries.
- Outside `modules/`, shared code is grouped by concern (D177): `core/` (the bus, errors, values, the LLM port)
  imports nothing else in the app; `infrastructure/` (settings, database, migrations, logging, Gemini) and `web/`
  (route dependencies, problem responses) import only `core/`. Modules never import `infrastructure/` (what it builds
  is passed in); only their HTTP adapters (`api.py`, `accounts/account_api.py`, `assistant/api/routes.py`,
  `mcp/http.py`) import `web/`.
- Only `bootstrap.py` and `main.py` import a `module.py`.
- Module dependencies stay one-way: expenses → categories; mcp → expenses, categories; assistant → the rest;
  accounts and receipts depend on none. A new dependency must not create a cycle; if two modules
  need each other, redesign (an event, or a third module).
- Inside the assistant, imports run `api/` → `application/` → `agent/`, `approvals/`, `tools/`, `receipt_agent/`,
  `a2ui/`, never back.
- **A2A agents live outside the monolith**, in `agents/<name>/`, each its own process, built on the shared agent kit
  (`agents/agent_kit/`: the key check, the task store, the app, D202). An agent imports only `app.core`, plus the Gemini
  adapter and `setup_logging` in a `server.py` (D196); never a module, `web/` or the backend's settings. The backend
  never imports an agent: it talks to one over A2A. An agent knows no person: the owner is checked in the monolith
  before anything is sent, and the agent refuses requests without its key (D197).

**Composition root.** `bootstrap.build(clock, llm, tools, engine, files, identity, sealer, agents)` creates
everything replaceable;
`main.create_app(services)` serves it; nothing is built at import (uvicorn runs with `--factory`).

**Ports and adapters.** The model sits behind `core/llm` ports: depend on the narrowest one you call
(`StructuredOutputModel` or `ToolCallingModel`). Only `bootstrap.py` imports the Gemini adapter
(`infrastructure/llm/`). The expense tools sit behind `ExpenseTools`, uploaded files' bytes behind `FileStore`
(`core/files.py`; never a path built from a user's file name), the A2A agents behind `RemoteAgents`
(`core/agents.py`; only `infrastructure/a2a/` imports the A2A SDK, D201, and every answer is checked as outside data,
D199), the sign-in provider behind
`IdentityProvider` (`core/identity.py`) and sealed secrets behind `Sealer` (`core/sealing.py`). Time comes from the injected clock
(`ctx.clock`, `ClockDep`), never `date.today()` or `datetime.now()`.

**Signing in (D185–D187).**
- The provider is configuration: speak only OpenID Connect through `IdentityProvider`. Never write a provider's name,
  SDK or special case into `backend/app` or `web/src` (scan 8 in architecture.md); a difference between providers
  is a setting (`OIDC_LOGIN_OPTIONS`, `OIDC_ROLE_CLAIM`).
- Every module's routes are behind `require_csrf` and `require_user` (`main.py`); only the accounts module's sign-in
  routes and `/health` aren't. A route that needs the person takes `principal: CurrentUserDep` (`web/auth.py`).
- No token or session data reaches the browser: the session cookie holds a random key only, the server stores its
  hash, and the ID token is kept sealed. Never log a key, a token or a cookie.
- A user is found by their identity (issuer, subject), never by email. Other modules will point at `UserId`, never at
  a provider's subject.

**Each person's own data (D190, D191).**
- Every command and query about a person's data carries `owner_id: UserId` (`core/ids.py`), and the handler puts it
  in the same statement as the id (`WHERE id = ? AND owner_id = ?`): never `session.get(Table, id)` on such a table
  (scan 9). Another person's object is a `NotFoundError`, identical to a missing one.
- The owner comes only from the server's side: `principal.user_id` in a route, `current_caller()` in an MCP tool, the
  run in the assistant (`ExpenseTools.acting_for`). A REST body or query string is its own model without an owner
  (`NewExpense`, `ExpenseFilters`); never make an owned message a route's body. Never give the model an owner argument.
- Categories are shared. A new table holding a person's data gets an indexed `owner_id`.

**Files the model reads are data.** A receipt (or any attachment) goes to the model through `ask_for_json(...,
attachments=...)`, in a call without tools; its type is judged by its bytes, the instruction says its text is never
an instruction, and the answer is checked before anyone sees it. Nothing read from a file is saved until a person
confirms it (D182).

**Money** is stored as integer paise; it's `Decimal` rupees at the edges (`rupees_to_paise`, `format_money`). Never
`float`. Every expense is also stored in INR (D204): save through `ExpenseRecorder`, which fetches the rate first;
totals add up the INR amounts; a conversion rounds only in `core.money.convert_minor`.

**Errors.** Raise `NotFoundError`, `BusinessRuleError` or `ExternalServiceError` (`core/errors.py`, no HTTP in it).
An error a person may read carries a catalogued text: `BusinessRuleError(translatable(ExpenseText.X, **values))`; one
only MCP clients and the model see (the MCP tools' own) stays an English string. Never catch them in routes:
`web/problems.py` turns every error into an RFC 9457 problem, its detail in the request's language.

**Nothing but texts for people reaches the client (D180).** Never put an outside service's words, an exception's
text, a URL, a class name or a tool's output into a detail, a `RUN_ERROR`, a reply or any other text a person reads,
not even as a placeholder value. Log them (user data only at DEBUG) and send a catalogued text. A plain-string
`AppError` is never shown: people get a generic text for its kind.

**Texts for people, in the request's language (D179).**
- What a person reads (error details, the assistant's cards, chips and fixed replies, payment labels) lives in the
  module's `i18n/` catalog: `define_catalog` refuses, at startup, a language missing a key or using a placeholder
  English doesn't. Write texts with `text(language, key, **values)`, counts with `Plural`, money and dates with
  `format_money` / `format_day` / `format_month` (`core/i18n`, CLDR through Babel), never `strftime`.
- The web app sends `Accept-Language`; a route that writes texts takes `language: LanguageDep` and passes it down.
- Stay English: everything the model reads (prompts, tool descriptions, tool results), logs, codes and protocol
  values. User data (category names, merchants, notes) is never translated.

**API.** Routes live under `/api/v1`. Inputs are validated by contract types: `RecordId`, `IdPath`, `Annotated`
limits, `extra="forbid"`. A route that calls the model takes `dependencies=[MODEL_QUOTA]` (`web/rate_limits.py`, D194).
Every API and MCP answer is sent with `Cache-Control: no-store` and the security headers (`web/security_headers.py`,
D193): don't remove them, and don't let a route cache a person's data.

**Database changes** only through Alembic migrations (`backend/migrations`):
- Change `persistence/tables.py`, autogenerate a migration, and read and fix it.
- Give it a working `downgrade()`. Write data conversions out in the migration; never import them from app code.
- On a copy of the database: upgrade, downgrade, upgrade, then `alembic check`.

**MCP tools.**
- One file per tool in `mcp/tools/`, registered in `TOOL_REGISTRARS`. Its order is the order the model sees.
- Arguments are typed `Annotated` with descriptions.
- A destructive tool needs a strict interlock (`confirmed`).
- A tool function's name, signature and docstring are runtime data: the MCP SDK builds the schema from them.
- A tool acts for `current_caller()` (`mcp/caller.py`), set by the transport from a personal access token or the
  signed-in run; it never takes a person as an argument.

**What the model sees is behaviour.** Prompts, tool declarations and the `/parse` schema decide what the model does.
Changing them is a feature change, to be designed and verified as one.

**Size.** Files under about 180 lines of code; functions under about 50. Extend through tables, protocols and new
files, not new branches in shared code.

**The web app's contract.** After changing an API, a limit, a label, or an A2UI or AG-UI name, run
`backend\scripts\export_contracts.py`, then `npm run gen:api` in `web/`, and commit the generated files.

## 3. Web: Next.js, feature slices (`web/`)

- **Next.js 16, App Router (D188).** This version differs from older ones: check the docs bundled in
  `web/node_modules/next/dist/docs/` before using a Next.js API.
  - `src/app/` holds only Next's own files at its top (`layout.tsx`, `not-found.tsx`, `robots.ts`, `sitemap.ts`);
    the composition lives in private folders (`_shell/`, `_frame/`, `_views/`, `_i18n/`, `_seo/`, `_styles/`).
    Never leave a loose file there.
  - Routes are `page.tsx` files under `src/app/(client)/`; a route file is a server component that exports its
    `metadata` (`privatePage` or `publicPage` from `_seo/seo.ts`) and draws its feature's page from `_views/`.
  - Signed-in pages go in `(client)/(app)/`, behind the session check (`AuthGate`, D189); a public page goes beside
    it, uses `publicPage` and is added to `PUBLIC_PATHS` (`_seo/seo.ts`: robots.txt and the sitemap).
  - A page never outlives its person (D192): when the session ends or someone else signs in, `AuthGate` unloads it.
    Never keep a person's data where a reload wouldn't clear it (browser storage).
  - Everything under `(client)/` is drawn in the browser only (`ClientRoot`); don't read `window` or `localStorage`
    in a server component. A page meant to be rendered on the server for search engines goes outside `(client)/`.
- **Plain feature slices** (not Feature-Sliced Design):
  - `src/app` composes the app.
  - `src/features/<name>` owns everything for one feature.
  - `src/shared` knows no feature.
  - Only `app/` wires features together.
- **Imports.**
  - Another feature is imported only through its `index.ts`.
  - Inside a feature, imports are relative and never leave it.
  - `shared/` imports no feature and nothing from `app/`.
  - `npx oxlint` enforces all three.
- **Server data** goes through TanStack Query, in the feature's `queries.ts`:
  - keys sit under the feature's root key;
  - pass the query's `signal`;
  - never fetch in a `useEffect`.
- **Mutations** only declare what they changed (`meta: { changes: DATA_SCOPES.x }`). The `STALE_AFTER` table in
  `app/_shell/query-client.ts` decides what reloads.
- **API calls** go through `api` (openapi-fetch) with `unwrap` or `unwrapEmpty`, and types come from `Schemas[...]`.
  - The API is on the page's own origin (D184): call relative paths (`/api/v1/...`), never an absolute API address;
    Next.js's rewrite (`next.config.ts`) forwards them. The backend sends no CORS headers.
  - Every call carries `apiHeaders()` (the language and `X-CSRF`, D186): `api` adds them itself; anything that calls
    `fetch` directly (the assistant's stream) spreads them in. Never store a token or session data in the browser.
  - Never hand-copy a backend type or value: use `schema.gen.ts` and `contracts.gen.ts`.
  - Never edit `*.gen.ts` or `openapi.json`.
- **Pages** are exported from their feature's `index.ts` through `lazyWithRetry` (their code and texts load together),
  re-exported by `app/_views/client-pages.ts`, drawn by their route file, and listed in the menu once in `PAGES`
  (`app/_frame/pages.tsx`).
- **Logic that doesn't need React** goes in pure functions in their own files.
- **Texts** (D178): everything a person sees or hears comes from a namespace of texts, never a literal in a component.
  - Each feature owns `i18n/`: `en.ts` (the source, a default-exported plain object), one file per other language
    typed `Translation<typeof en>` (a missing key is a compile error), and `index.ts` (`defineNamespace` with a loader
    per language, `export const useTexts = xTexts.useTexts`, and its `ResourceNamespaceMap` entry, typed by
    `import type en from "./en"`).
  - Every language's file is a chunk of its own, loaded with what uses it: a feature's from its page's or panel's lazy
    loader, `Promise.all([import(page), loadNamespaces(...)])`, so nothing is drawn before its texts are in. `common`
    (shared/), `app` (the frame) and `auth` (the session check and the user menu) load when the app boots
    (`app/_shell/namespaces.ts`), their English bundled so the frame can always be drawn.
  - Components call `const { t } = useTexts()`. Code outside React calls `i18n.t(key, { ns })` when it needs the
    text. Never keep a text in a module-level constant (store its key), and never build a sentence from pieces: one
    key per sentence, with `{{placeholders}}`, and `_one`/`_other` keys for counts.
  - Numbers and dates go through `shared/lib/format.ts`, which follows the language's locale (`LANGUAGES`).
  - Not translated in the browser: user data, and text the server sends (cards, chip labels, error details,
    payment labels), which the server will write in the chosen language.
- **Size.** Files under about 150 lines of code, and components or hooks under about 60. A folder past about eight
  files gets sub-folders by area (e.g. `components/table/`, `dialogs/`).
- **Network data is untrusted.** Check it with guards or schemas, never with `as` casts.
- **The A2UI renderer's safety rules** are never weakened ([security.md](docs/security.md)): the allow-list is
  `CATALOGS`, lookups are own-property only, and size and depth limits apply.
- **Failures stay small.**
  - Error boundaries wrap the app, the page area, the chat panel and every A2UI card.
  - A page keeps its data when a refresh fails (`RefreshNotice`).
  - Code that fails to load can be retried.
- **Errors show only texts for people (D180).** Show an error with `messageOf`: only a `UserFacingError`'s message
  (`ApiError`, `AgentRunError`, our own texts) is shown, anything else as a generic text. Throw `UserFacingError` with
  a text from a namespace, never a raw `Error` meant to be read.
- **Accessibility.**
  - Every control has a label.
  - Sortable headers set `aria-sort`.
  - Live regions announce changes.
  - jsx-a11y rules must pass.
- **shadcn/ui** components live in `src/shared/ui` (generated; add them with `npx shadcn@latest add <name>`).

## 4. Code rules for both halves

- **No magic strings or numbers.**
  - Names, keys, limits, labels and texts are constants or enums, defined once in the module or feature that owns
    them.
  - Values shared with the web app go through the generated contract.
- **No duplication:** one definition, referenced everywhere.
- **Dependencies:** pin every new one to an exact version (`requirements.txt`, `package.json`). Prefer adding none.
- **No hidden dependencies:** no globals read inside logic, no work done at import time, no `date.today()`.

## 5. Testability (there are no automated tests yet, D173)

Everything outside a unit can be passed in, so the owner's future tests (and your checks) need no monkeypatching:

```python
engine = create_db_engine("sqlite://")                  # in memory, or a copy of the database
migrations.upgrade_to_latest(engine)
services = bootstrap.build(clock=FixedClock(), llm=FakeModel(), engine=engine,
                           identity=FakeIdentityProvider(), sealer=FernetSealer([Fernet.generate_key().decode()]))
client = TestClient(create_app(services), base_url="https://localhost")   # https: the cookies are Secure
# The A2A agents: pass agents= a fake core.agents.RemoteAgents, or A2AAgents({name: AgentEndpoint(url, key)},
# {name: httpx.ASGITransport(app=<the agent's build_app(...)>)}) for the real agents in-process.
# Sign in through the real routes: GET /api/v1/auth/login, then /auth/callback with the state the fake was given.
# Send X-CSRF: 1 on every API call. A fake provider implements core/identity.IdentityProvider; the OIDC adapter
# itself takes httpx2.MockTransport (transport=...) to talk to a fake provider without a network.
```

Use cases take their ports in their constructors. Keep it that way: new code gets its collaborators passed in, and
logic that can be a pure function is one.

## 6. Inline documentation (D171)

- **Every file starts with a header**: a module docstring, or a `//` block in TypeScript. It says what the file is
  for, its layer, and who uses it.
- **Every function, method, class, component, hook and exported type is documented**: what it's for, what it returns
  or raises, and the rule it enforces. A one-liner is enough for a small helper.
- **Business rules are explained where they're applied**, saying why.
- **Python:** Pydantic models (commands, queries, results, tables), enums, FastAPI route functions and MCP tool
  functions get `#` comments above them. Never add or change their docstrings: they become OpenAPI, MCP or Gemini
  schema text.
- **TypeScript:** `/** */` on exports (VS Code shows it on hover), `//` for logic, no comments inside JSX.
- **Style:** plain English, professional tone, lines no longer than 120 characters.
- **Keep comments true:** when you change code, fix the comments around it.

## 7. Definition of done

Run these before asking to commit (PowerShell, from the repo root):

```powershell
# Backend compiles, and the module rules hold: run every scan in docs/architecture.md, "Checking the rules"
# (they include each module package importing on its own, which catches import cycles).
.\.venv\Scripts\python.exe -m compileall -q backend agents

# Migrations, on a COPY of the database
Copy-Item backend\spendwise.db $env:TEMP\spendwise-check.db
$env:DATABASE_URL = "sqlite:///$($env:TEMP -replace '\\','/')/spendwise-check.db"
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini check     # "No new upgrade operations detected."
Remove-Item Env:DATABASE_URL

# After any change to an API, limit, label or protocol name: regenerate the web app's contract
.\.venv\Scripts\python.exe backend\scripts\export_contracts.py; cd web; npm run gen:api; cd ..

# Web
cd web; npx tsc -b; npx oxlint; npm run build; cd ..       # oxlint: warnings only inside src/shared/ui
```

**Behaviour.**
- Exercise the change through the HTTP API with a fake model (section 5), not the real one.
- For a refactor, record the observable behaviour before and after and compare: events, responses, and what the
  model is sent.
- For a small, low-risk UI tweak to an already-verified feature (sizing, spacing, wording), the type-check, lint and
  build above are enough: don't start servers or drive a browser unless the owner asks.

**Docs, in the same change.**
- A phase note (`docs/phases/`), or a "Later changes" note on the phase it affects.
- A decision in `decisions.md`. It's append-only: old entries get "Updated by" or "Superseded by" lines, never edits.
- Updates to `architecture.md`, `api_endpoints.md`, `database_schema.md`, `configuration.md` and `security.md` where
  the change touches them.
- `sources.md` for any fact taken from external docs or a library's code (with the link or path).
- `troubleshooting.md` for any problem that took real effort.
- Full list: [docs/README.md](docs/README.md#keeping-these-docs-current).

**Review.** Re-read your whole diff against this file, fix what you find, then hand over with a short summary of what
changed, how it was verified, and anything left open.
