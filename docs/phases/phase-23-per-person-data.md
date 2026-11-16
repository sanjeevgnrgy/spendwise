# Phase 23: Each person's own data

**Goal:** everyone who signs in has their own expenses, conversations and receipts, and nobody can read, change, or
even detect anyone else's, through any door: the REST API, the assistant (whatever the model is told), MCP clients,
or a guessed id. This is protection against **broken object level authorization (BOLA)**, OWASP's first API risk:
an API that checks *who you are* but not *whether this object is yours*.

**The owner's choices** (asked before building):

- **The data from before sign-in is deleted.** It belonged to nobody, so it could never be shown again. Migration
  0007 deletes it; the receipt files stay on disk (see [Migration 0007](#migration-0007)).
- **Categories stay shared** and read-only: one list, created by `seed.py`, the same for everyone.
- **MCP clients use personal access tokens**, made by each person in Settings. The single `MCP_TOKEN` is gone, and
  so is `MCP_URL` (a remote tools server can't know who is signed in here).
- Also in this phase: an account page (sessions and tokens, Part 3), security headers, and rate limits on the
  model-backed routes (Part 4).
- The live identity provider (Phase 22, Part 4) is still to be configured, later.

## Part 1: the owner on the server (D190)

**Every object belongs to someone, and the owner is checked where the object is read.**

- `expense`, `conversation_message`, `pending_approval` and `receipt_file` have a NOT NULL `owner_id`: SpendWise's
  user id (`core.ids.UserId`), with no foreign key (the users table is the accounts module's, D13).
- **Every command and query about a person's data carries `owner_id`**, and it always comes from the server's side:
  the session (`principal.user_id`), a personal access token, or the signed-in run. Never from a request.
- **REST inputs are separate models from the messages**, so an owner can't be sent: the body of `POST /expenses` is
  `NewExpense` (the command is `CreateExpense(owner_id, expense)`), and the query string of `GET /expenses` is
  `ExpenseFilters` (the query is `ListExpenses(owner_id, filters)`). `extra="forbid"` turns an `owner_id` in a body
  or query string into a 422.
- **The owner is part of the same SQL statement** as the id: `WHERE id = :id AND owner_id = :owner` for reads,
  updates and deletes (including the delete's version check), and every list, search, count and total filters on
  the owner first.
- **Another person's object is a 404, exactly like one that doesn't exist**: same status, type and text. Ids are
  sequential, so they're easy to guess; the check makes guessing useless, and the identical answer means a guess
  doesn't even reveal that the object exists.
- **A thread is its owner and its id together.** The browser names AG-UI threads, so two people may pick the same
  id: each gets their own conversation, and neither can read or continue the other's. `POST /chat` with a thread id
  the person doesn't have is a 404.
- **Delete cards** are taken only by their owner, in their thread; at most 200 are kept *per person*, so one
  person's unanswered cards can't push out another's.
- **The assistant's tools act for the signed-in person** (`ExpenseTools.acting_for(owner)`, bound per run). Whatever
  the model asks for, say an id from text injected into a message or a receipt, it reads and changes only that
  person's expenses.

### Every door, and what guards it

| Door | What someone would try | What stops it |
|---|---|---|
| `GET`, `PATCH`, `DELETE /expenses/{id}` | another person's id | owner in the same statement: 404, identical to a missing id |
| `GET /expenses?search=...`, `/summary`, `/summary/trend` | find, count or total another person's rows | every list, count and total filters on the owner first |
| `POST /expenses`, `PATCH`, `GET /expenses?owner_id=` | name an owner | the inputs have no owner field: 422 (`extra="forbid"`) |
| `GET /receipts/{id}`, `POST /receipts/{id}/extraction` | read, or have the model read, someone's receipt | owner-checked lookup: 404, and the model is never shown the file |
| a receipt attached in the chat | attach another person's receipt id | the run reads it as the signed-in person: `RUN_ERROR` not-found, no model call |
| `GET /threads/{id}`, `POST /agent` with a known `threadId` | read or continue someone's conversation | threads are (owner, id): another person's id is a new, empty conversation of one's own |
| `POST /chat` with a `thread_id` | continue someone's conversation | 404 (not continued, not revealed) |
| Approve on a delete card | press another person's card (its real id, in their thread id) | the card is taken only by its owner: nothing deleted, no details shown |
| the model's tool calls | `get_expense`, `update_expense`, `delete_expense` with another person's id, or an invented `owner_id` | tools act for the run's person: "not found"; unknown arguments are ignored |
| MCP over HTTP | no token, a made-up one, a session cookie, a revoked or expired token | 401; a working token acts only for its owner |
| MCP over stdio | no token, or one revoked while the server runs | every tool call checks the token again: refused |
| `GET`, `DELETE /account/tokens/{id}`, `/account/sessions/{id}` | list, revoke or sign out someone else's | lists are the person's own; another person's id is a 404 |

## Part 2: MCP acts for a person (D191)

**Personal access tokens.** Each person makes tokens in Settings (`POST /account/tokens`): a name, and a lifetime of
30, 90 (default) or 365 days. A token is `spw_` plus 256 random bits; it's shown once, and only its SHA-256 is
stored, with its last four characters as a hint. At most 10 working tokens per person. Revoking deletes it, and it
stops working at once; an expired token, or one whose owner is switched off, stops working too.

**The caller** (`mcp/caller.py`) is who an MCP request acts for: a context variable, set by whatever received the
request from something the request itself can't forge, and read by every tool (`current_caller()`):

| Transport | Sets the caller from |
|---|---|
| HTTP (`/mcp/`, `http.py`) | `Authorization: Bearer <token>`: resolved to its owner, around the request; 401 without a working token |
| stdio (`mcp_stdio.py`) | `SPENDWISE_TOKEN` in the process's environment (the MCP client's config sets it), checked again on every tool call |
| in-process (the assistant) | the signed-in person of the run (`McpExpenseTools.acting_for`) |

Nothing in an MCP message (arguments, `_meta`) names a caller. Without one, or once the token stops working, every
tool refuses ("isn't signed in"); `expenses://recent` too. Categories are readable by anyone signed in. Asyncio tasks
and anyio's worker threads copy the context they start in, so the value set around a request reaches the tool's
thread, and two requests at once each see their own ([sources.md](../sources.md#30-who-an-mcp-request-acts-for-context-variables-across-tasks-and-threads-phase-23)).

**`MCP_URL` and `MCP_TOKEN` are gone.** A remote tools server couldn't know who is signed in here, and a single
shared token couldn't say whose data a client may touch. The assistant always calls this app's MCP server
in-process.

**The account routes** (`accounts/account_api.py`, behind the session and `X-CSRF` checks like every module's):
the person's live sessions (with the browser each signed in from: `user_session.user_agent`), signing one out or
every other one, and their tokens. Sessions and tokens are listed only for their owner.

## Part 3: the web app (D192)

**A page never outlives its person.** The server decides what each person may see; the browser must not undo that on
screen. A page that has shown someone's data holds it in memory: the query cache, the chat, half-typed forms.

| When | The page that showed someone's data |
|---|---|
| the session ends (expired, signed out in another tab, ended by the provider) | leaves for the sign-in page with a full navigation, which drops everything it held, and remembers the page it was on |
| someone else signs in, in another tab of the same browser | reloads, and starts again for them |
| a page that never showed anyone's data (the session check's spinner) | moves to the sign-in page inside the app |

`AuthGate` does it (`use-session-boundary.ts`). It hears of a change from its own requests (a 401 asks again who is
signed in) and from the browser's other tabs (`use-session-sync.ts`): a page that learns who is signed in posts an
empty `BroadcastChannel` message, and the other tabs ask the server again. The message is never trusted: what a
tab does depends on the server's answer alone. The sign-in page listens too, so signing in in another tab takes it on.

**Links from the server or the address are checked:** the sign-out link and `?return_to=` lead only to paths on this
site (`ownSitePath`, `afterSignIn`); `https://evil.example`, `//evil.example` and `javascript:` go to the start page.

**The Settings page** (`/settings`, `features/account/`):

- **Profile:** picture or initials, name and email, from the identity provider.
- **Where you're signed in:** each live session, its browser and system read from its User-Agent ("Edge on
  Windows"), when it signed in and was last active, "This browser" marked; Sign out on any other row; Sign out
  everywhere else (after confirming).
- **Access tokens:** each token's name, last characters, dates and last use ("Expired" when the server says so).
  New token asks for a name and a lifetime, then shows the token once, with Copy; Done forgets it (it lives only in
  that dialog's state, never in browser storage). Revoke asks first.

## Part 4: security headers and rate limits (D193, D194)

**Headers.** Every page gets a Content-Security-Policy (this site's scripts, styles, fonts and requests only;
pictures from this site or `https:`; no plugins, no framing, no `<base>` or form hijacking), `X-Frame-Options: DENY`,
nosniff, `Referrer-Policy: same-origin`, a Permissions-Policy refusing camera and microphone, and, over https, HSTS
(`web/security-headers.ts`). The backend's answers get nosniff, `DENY` and `same-origin`, and under `/api/v1` and
`/mcp`, **`Cache-Control: no-store`** (a person's data must never sit in a shared cache) and a CSP that allows
nothing (`web/security_headers.py`). The pages' CSP allows inline scripts, since Next.js writes its bootstrap inline;
D193 records why.

**Rate limits.** The four routes that call the model (`/agent`, `/chat`, `/parse`, reading a receipt) allow each
person `MODEL_REQUESTS_PER_MINUTE` (10) a minute and `MODEL_REQUESTS_PER_DAY` (300) a day. One more is a 429 problem
with `Retry-After`, in the person's language, and never reaches the model (`core/rate_limit.py`,
`web/rate_limits.py`). Counted in memory, per server process.

## Migration 0007

`0007_owners` first **deletes the rows made before sign-in existed** (expenses, conversations, delete cards and
receipts: they belong to nobody), then adds the `owner_id` columns and their indexes, `access_token`, and
`user_session.user_agent`. Categories and the accounts tables are kept.

- The receipt files stay in `UPLOADS_DIR`: a migration doesn't touch files (a check run against a copy of the
  database must never delete the real uploads). Nothing points at them any more; delete the folder's contents by
  hand if you like.
- Downgrade removes the new columns, indexes and table and restores the old indexes. It can't bring the deleted
  rows back.
- **It runs the next time `.\run.ps1` starts the backend.** Copy `backend\spendwise.db` first if you want to keep
  the old data somewhere.

## What was built (Parts 1 and 2)

| Where | What |
|---|---|
| `core/ids.py`, `core/clock.py` | `UserId`; `as_utc` and `UtcDateTime` (times read back from SQLite get their zone, so the JSON carries it) |
| `modules/expenses/` | `owner_id` on the table and every message; `NewExpense` (the POST body) and `ExpenseFilters` (the query string); the repository and every query filter on the owner; index (owner_id, spent_on) |
| `modules/conversations/` | `owner_id` on every message; threads are (owner, id); index (owner_id, thread_id, turn) |
| `modules/receipts/` | `owner_id`; `GetReceipt`, the uploader and `ReceiptExtractor.extract(owner_id, ...)` owner-checked |
| `modules/assistant/` | approvals per owner (and per-person cap); the use cases take the owner; `ExpenseTools.acting_for`; `McpExpenseTools` in-process only |
| `modules/mcp/` | `caller.py`; every tool and `expenses://recent` act for `current_caller()`; `http.py`'s `AccessTokenAuth` |
| `modules/accounts/` | `access_token` table; `CreateAccessToken`, `RevokeAccessToken`, `TouchAccessToken`, `SignOutSession`, `SignOutOtherSessions`; `ListAccessTokens`, `FindTokenOwner`, `ListSessions`, `FindUsersByEmail`; `AccessTokens` (make, resolve); `account_api.py`; `i18n/` (its first texts); `user_session.user_agent` |
| `bootstrap.py`, `main.py`, `infrastructure/config.py` | `access_tokens` in the services; `/mcp/` always mounted, behind tokens; `MCP_URL` and `MCP_TOKEN` removed |
| `mcp_stdio.py`, `seed.py` | the stdio server acts with `SPENDWISE_TOKEN`; `seed.py --sample-for EMAIL` (categories alone without it) |
| `migrations/versions/0007_owners.py` | the deletion, the owner columns, `access_token`, `user_agent` |
| `scripts/export_contracts.py` | `ACCOUNT` in the web contract: token name length, the most tokens, the lifetimes |
| `web/src/features/expenses/api.ts` | the body type is `Schemas["NewExpense"]` |

| Where (Part 3) | What |
|---|---|
| `web/src/features/auth/use-session-boundary.ts`, `use-session-sync.ts` | the page leaves when its person changes; tabs keep each other in step |
| `features/auth/` (`sign-in-urls.ts`, `auth-gate.tsx`, `user-menu.tsx`, `sign-in-page.tsx`, `user-avatar.tsx`, `index.ts`) | `ownSitePath`, `afterSignIn`; the gate uses the boundary; the sign-out link is checked; avatar sizes; `useSignedInUser` and `UserAvatar` public |
| `features/account/` | the Settings page: `api.ts`, `queries.ts`, `device-name.ts`, `token-form.ts`, `components/` (profile, `sessions/`, `tokens/`, section card, confirm dialog), `i18n/` |
| `app/(client)/(app)/settings/page.tsx`, `app/_views/client-pages.ts`, `app/_shell/query-client.ts`, `app/_i18n/` | the route; the page; sessions and tokens in `STALE_AFTER`; "coming soon" gone |
| `shared/config/data-scopes.ts`, `shared/lib/format.ts`, `shared/components/labeled-field.tsx` | the `sessions` and `accessTokens` scopes; `formatDateTime`; `LabeledField` moved here from the expenses feature |

| Where (Part 4) | What |
|---|---|
| `backend/app/web/security_headers.py`, `main.py` | the backend's headers, outside the error handling; `no-store` and an empty CSP under the API and MCP |
| `core/rate_limit.py`, `web/rate_limits.py`, `core/errors.py`, `web/problems.py`, `web/i18n/` | the allowance, `MODEL_QUOTA`, `TooManyRequestsError` (429, `Retry-After`), its two texts |
| `infrastructure/config.py`, `bootstrap.py`, `assistant/api/routes.py`, `receipts/api.py` | `MODEL_REQUESTS_PER_MINUTE`, `MODEL_REQUESTS_PER_DAY`; the limiter in the services; the four routes limited |
| `web/security-headers.ts`, `next.config.ts`, `src/shared/config/site.ts`, `app/_seo/seo.ts` | the pages' headers; `PUBLIC_URL`'s name and default in one place (HSTS needs it too) |

## Run it

```powershell
Copy-Item backend\spendwise.db backend\spendwise-before-phase-23.db   # optional: keep the old data
.\run.ps1                                                              # applies 0007: the old rows are deleted
.\.venv\Scripts\python.exe backend\seed.py --sample-for you@example.com   # after signing in once
```

An MCP client over HTTP sends a token made in Settings; Claude Desktop's stdio server gets it in its config:

```json
"spendwise": {
  "command": "C:\\path\\to\\project\\.venv\\Scripts\\python.exe",
  "args": ["C:\\path\\to\\project\\backend\\mcp_stdio.py"],
  "env": { "SPENDWISE_TOKEN": "spw_..." }
}
```

> **How Parts 1 and 2 were checked:** offline, through the real HTTP API, with fakes at the ports (a scripted model,
> a fake identity provider, a movable clock, an in-memory database). No call to a real provider or to Gemini.
> - **Two people, one database** (102 checks): every door in the table above, tried with the other person's ids and
>   with forged owners; the answers to another person's id and to a missing id compared field by field; the model
>   scripted to call every tool on another person's expense, and to invent an `owner_id`; a delete card approved by
>   another person; MCP over HTTP with no token, a made-up one, a session cookie, each person's token, an expired
>   token (by the clock), a revoked one and a switched-off owner's; the stdio path with a working, a broken and no
>   token; tokens' limits, hashing, expiry and last use; sessions listed, signed out one by one and all but this one;
>   `FindUsersByEmail` finding both of two accounts with one email. Plus the rate limit and the headers (Part 4).
> - **Nothing else changed for one person:** signed in, the 51 recorded scenarios of Part 2 (REST, problems in both
>   languages, uploads, the `/agent` stream and every model call) answer with the same status and body. The OpenAPI
>   document gained the five account routes and their schemas; `CreateExpense` became `NewExpense`.
> - Part 2's 42 adapter checks and 71 route checks still pass.
> - Migration 0007 upgrades, downgrades and upgrades again on a copy of the database (13 expenses and 268 messages
>   deleted, 8 categories kept); `alembic check` is clean.
>
> **The new Hindi texts were written by an AI** and need a native speaker's review.

> **How Part 3 was checked:** in headless Edge, against the production build (`next start`) and a backend with two
> people and fakes at the ports (33 checks):
> - two tabs of one browser: Ravi signing in in tab B reloads tab A, left open on Asha's expenses, for him, with
>   nothing of hers left and only his data in its requests; signing out in B takes A to the sign-in page by a full
>   navigation, remembering `/expenses`; signing in again in B takes A on to it;
> - signed in, `/sign-in?return_to=` with `https://evil.example/x`, `//evil.example/x`, `/\evil.example/x` and
>   `javascript:alert(1)` all stay on the site;
> - Settings: the profile; this browser named from its User-Agent; a second client of the same person listed,
>   signed out from its row and then with Sign out everywhere else (its cookie refused each time);
> - tokens: Create waits for a name; the token shown once, working for an MCP client as its owner only, then listed
>   by name and hint and found nowhere in the page or the browser's storage; Revoke asks first, and the token is
>   refused at once;
> - the Settings page in Hindi; no uncaught exceptions or console errors in either tab;
> - the earlier checks still pass: the sign-in pages (33) and the Next.js migration (15).
>
> **How Part 4 was checked:** the rate limit and headers are part of the two-person run (limits of 3 a minute and 5 a
> day, a movable clock; every API answer, a problem, the stream, the docs page and MCP's), and the browser runs read
> the pages' headers and found no CSP refusals in the console.
>
> The browser checks' backend uses a database file: an in-memory SQLite database is one shared connection, and two
> tabs' parallel requests collided on it (a test-harness limit, not the app's).

## Design questions

**1. Why 404 for another person's expense, not 403?**

<details><summary>Answer</summary>

A 403 says "it exists, but it isn't yours": with sequential ids, anyone could map which ids belong to someone. A 404
that's identical to a missing id's (status, type, text) gives nothing away. There's no case where a person needs to
know that someone else's object exists.
</details>

**2. Why put the owner in the SQL statement, rather than load the object and compare?**

<details><summary>Answer</summary>

Loading first and comparing after works only if every caller remembers to compare; one forgotten check is a leak.
With the owner in the same statement as the id, there's nothing to forget: the row that isn't yours never leaves
the database. It's also one round trip, and the check can't drift from the read.
</details>

**3. Why can't the owner be an argument the model passes to a tool?**

<details><summary>Answer</summary>

The model can be told anything: by a message, by text printed on a receipt, by a note someone else wrote. Whatever
it reads must never decide whose data it touches. So the person comes from the run (the session), set around the
tool call where the model can't reach it, and the tools have no owner argument at all.
</details>

**4. Why personal tokens rather than one shared `MCP_TOKEN`?**

<details><summary>Answer</summary>

A shared token says "a trusted program", not "which person": with per-person data, the server must know whose
expenses a client may touch. A personal token is that person, and it can be revoked alone, expires by itself, and
shows when it was last used. Storing only its hash means a copy of the database can't be used to call the tools.
</details>

**5. Why reload the page when someone else signs in, rather than clear the caches?**

<details><summary>Answer</summary>

Clearing means knowing every place that holds a person's data: the query cache, the chat's transcript and thread,
a form half filled in, a token on screen. Each new feature would add one, and a forgotten one would show the last
person's data to the next. A reload drops all of it at once, by construction, and costs a second.
</details>
