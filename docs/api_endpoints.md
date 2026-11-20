# API Endpoints

Everything the backend exposes: the REST API, the assistant's AG-UI stream, and the MCP server. The interactive
version is Swagger UI at http://127.0.0.1:8000/docs; the machine-readable one is `/openapi.json` (the web app's types
are generated from it).

## Conventions

| | |
|---|---|
| **Base URL** | `http://127.0.0.1:8000/api/v1` for every REST route. `/health` and `/mcp/` stay at the root. A breaking change gets `/api/v2`. The web app reaches the same routes on its own origin (`http://localhost:5173/api/v1`, through the dev server's proxy, D184). |
| **Format** | JSON in and out. Field names are `snake_case` (AG-UI's stream uses `camelCase`, as its spec does). |
| **Money** | Requests take rupees as a decimal string (`"450.50"`, at most 2 decimals). Responses give both `amount_minor` (paise, an integer: exact, for arithmetic) and `amount` (rupees, a string: for display). |
| **Dates** | `YYYY-MM-DD`; months `YYYY-MM` (years 1900–2099); timestamps ISO 8601 in UTC. |
| **Ids** | positive integers up to 2⁶³−1; larger ones are a 422, not a crash. |
| **Language** | send `Accept-Language` (`hi`, `hi-IN,hi;q=0.9,en;q=0.5`): error `detail`s, and `/chat`'s and `/agent`'s texts (cards, chip labels, fixed replies, the model's reply), come in the best language the server speaks (English, Hindi), else English. Data (category names, merchants, notes) is never translated; problem `title`s stay English. |
| **Caching** | every API answer is `Cache-Control: no-store`: it's one person's data (D193) |
| **Unknown fields** | rejected (422), in bodies and query strings, so a typo like `merchnat` is an error, not a silent no-op. |
| **Auth** | every route below except `/health` and [Signing in](#signing-in) needs **a session cookie and `X-CSRF: 1`** (D186): without the header, 403; without a live session, 401. `/mcp/` takes a personal access token instead (`Authorization: Bearer <token>`, D191). **Everything is the signed-in
person's own** (D190): lists, totals and searches cover only their data, and an id that isn't theirs is a 404, exactly
like one that doesn't exist. No request names an owner: an `owner_id` in a body or query string is a 422. The API sends no CORS headers: in a browser, only pages on the API's own origin can read its answers (D184). |

## Errors: RFC 9457 problem details

Every error, from any route, has one shape and the media type `application/problem+json`:

```json
{
  "type": "urn:spendwise:problem:not-found",
  "title": "Not found",
  "status": 404,
  "detail": "Expense 14 not found",
  "instance": "/api/v1/expenses/14"
}
```

| Status | `type` (after `urn:spendwise:problem:`) | When |
|---|---|---|
| 404 | `not-found` | the resource in the URL doesn't exist, or isn't the signed-in person's (the same answer, D190) |
| 422 | `validation` | the request's shape is wrong; adds `errors: [{location, field, message}]` |
| 422 | `business-rule` | well-formed but against a rule: amount ≤ 0, unknown category, an expense that changed since it was shown |
| 400 | `invalid-token` | `POST /auth/backchannel-logout` with a logout token that fails a check |
| 401 | `unauthorized` | no live session ("Sign in to continue."), or `/mcp/` without a working personal access token |
| 429 | `too-many-requests` | the person's allowance for the routes that call the model (`/agent`, `/chat`, `/parse`, reading a receipt) is spent: `Retry-After` says when to try again (D194) |
| 403 | `forbidden` | a request the app didn't send: no `X-CSRF: 1`, a `Sec-Fetch-Site` from another site, or a sign-out link whose `sid` isn't this session's |
| 4xx | `http` | FastAPI's own (404 unknown URL, 405 wrong method with an `Allow` header) |
| 500 | `internal` | a bug; the details go to the server log only |
| 502 | `external-service` | Gemini failed: bad key, quota, overload |

The `detail` is always a text written for people, in the request's language. Nothing else's words reach the client
(D180): a bug's traceback, Gemini's own error message (a 502 says only that a service the app depends on failed),
a server's URL. Those are in the server log.

Validation example (`errors` says which values were wrong, for the client's developer; Pydantic's message, never the
value sent):

```json
{
  "type": "urn:spendwise:problem:validation", "title": "Invalid request", "status": 422,
  "detail": "Some of the values sent aren't valid.",
  "instance": "/api/v1/expenses",
  "errors": [
    {"location": "body", "field": "merchant", "message": "Field required"},
    {"location": "body", "field": "merchnat", "message": "Extra inputs are not permitted"}
  ]
}
```

## Health

### `GET /health`

`{"status": "ok"}` when the server is up and its database answers. Cheap: meant for monitors. Needs no session.

## Signing in

The accounts module's routes (Phase 22, D185–D187). `login`, `callback` and `logout` are **browser navigations**
answered with redirects (302, `Cache-Control: no-store`), not API calls; `options` and `user` are API calls and need
`X-CSRF: 1`. None of them needs a session to be reached.

### `GET /api/v1/auth/options`

The sign-in page's buttons, from `OIDC_LOGIN_OPTIONS`: `[{"key": "google", "label": "Google"}]`, or `[]` when the page
should offer the provider's own page (or sign-in isn't configured).

### `GET /api/v1/auth/login?option=google&return_to=/expenses`

Starts signing in: 302 to the provider's login page, with a short-lived login cookie (`__Host-spendwise-login`,
HttpOnly, Secure, SameSite=Lax, 10 minutes) that ties the sign-in to this browser. `option` (a button's key) skips to
that way of signing in; an unknown one is ignored. `return_to` is the page to come back to: only a path in the web
app is kept, anything else becomes `/`. A session this browser already has is ended first. If sign-in isn't
configured or the provider can't be reached: 302 to `/sign-in?error=unavailable`.

### `GET /api/v1/auth/callback?code=...&state=...`

The redirect URI registered at the provider; only the provider sends people here. On success: 302 to `return_to`,
with the session cookie (`__Host-spendwise-session`, HttpOnly, Secure, SameSite=Strict, 14 days). On failure: 302 to
`/sign-in?error=<code>`:

| `error` | Meaning |
|---|---|
| `cancelled` | the person cancelled at the provider, or it refused them |
| `expired` | the sign-in took over 10 minutes, was already used, or started in another browser |
| `rejected` | something in the provider's answer failed a check (state, signature, nonce, ...) |
| `not-allowed` | signed in, but may not use SpendWise (no required role, or the account is switched off) |
| `unavailable` | the provider couldn't be used (not configured, unreachable, an error) |

Either way the login cookie is cleared.

### `GET /api/v1/auth/user`

Who is signed in, and the link that signs this browser out (401 when nobody is):

```json
{"id": 1, "name": "Asha Rao", "email": "asha@example.com", "avatar_url": "https://...",
 "logout_url": "/api/v1/auth/logout?sid=4f1c...e2"}
```

### `GET /api/v1/auth/logout?sid=<handle>`

Signs this browser out: the session ends, the cookie is cleared, and 302 to the provider's sign-out page (with the ID
token as a hint, so it ends its own session too), or to `/sign-in` if it has none. `sid` must be this session's handle
(from `logout_url`): otherwise 403, so a link on another site can't sign anyone out. Without a session: 302 to
`/sign-in`.

### `POST /api/v1/auth/backchannel-logout`

The provider, server to server (OpenID Connect Back-Channel Logout 1.0): `application/x-www-form-urlencoded` with a
signed `logout_token`. Ends the sessions it names (the provider's session, else all of that user's). 200 with an empty
body; 400 `invalid-token` if the token fails a check.

### Calling the API from a script

A script needs what the browser has: the session cookie and the header. Sign in in the browser, copy the
`__Host-spendwise-session` cookie's value from the developer tools, then:

```powershell
curl.exe -H "X-CSRF: 1" -b "__Host-spendwise-session=<value>" http://localhost:5173/api/v1/categories
```

(`-b "name=value"` sends the cookie as it is. Treat the value like a password: it's the session.) The examples below
leave the cookie and header out for brevity. MCP clients use `/mcp/` and a personal access token instead.

## Account

The signed-in person's own sessions and personal access tokens, for the web app's Settings page (D191). A session
or token id that isn't theirs is a 404.

### `GET /api/v1/account/sessions`

Their live sessions (the browsers they're signed in on), most recently used first. `current` marks the one asking;
`user_agent` is the browser's own description at sign-in.

```json
[{"id": 7, "created_at": "2026-11-15T09:12:00Z", "last_active_at": "2026-11-15T10:01:00Z",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; ...) Edg/157.0", "current": true}]
```

### `DELETE /api/v1/account/sessions/{session_id}`

Signs that browser out: its cookie stops working at once. **204**. (This browser is better signed out with the
sign-out link, which also signs out at the provider.)

### `POST /api/v1/account/sessions/sign-out-others`

Signs out every other browser, keeping this one. **204**.

### `GET /api/v1/account/tokens`

Their personal access tokens, newest first: never the tokens themselves.

```json
[{"id": 3, "name": "Desktop assistant", "hint": "x9Qa", "created_at": "2026-11-15T09:20:00Z",
  "expires_at": "2027-02-13T09:20:00Z", "last_used_at": null, "expired": false}]
```

### `POST /api/v1/account/tokens`

Makes a token for MCP clients. **201** with the token's details and `token` itself: **the only time it's sent**
(`Cache-Control: no-store`).

```json
{"name": "Desktop assistant", "lifetime_days": 90}
```

`name`: 1–50 characters; `lifetime_days`: 30, 90 (default) or 365. More than 10 working tokens is a 422.

### `DELETE /api/v1/account/tokens/{token_id}`

Revokes the token: it stops working at once. **204**.

## Categories

### `GET /api/v1/categories`

Every category, in creation order.

```json
[{"id": 1, "name": "Food", "icon": "utensils"}, {"id": 2, "name": "Transport", "icon": "bus"}]
```

`icon` is a name the web app maps to a picture. Categories are created by `seed.py` (there's no REST route to create
one yet); names are unique ignoring letter case.

## Expenses

### The expense object (`ExpenseRead`)

```json
{
  "id": 14,
  "amount_minor": 45050,
  "amount": "450.50",
  "currency": "INR",
  "category_id": 1,
  "merchant": "Swiggy",
  "note": "Dinner",
  "spent_on": "2026-11-12",
  "payment_method": "upi",
  "created_at": "2026-11-13T09:14:02.511Z",
  "version": 1,
  "base_amount_minor": 45050,
  "base_amount": "450.50",
  "exchange_rate": "1",
  "rate_date": "2026-11-12"
}
```

- `payment_method`: one of `cash`, `upi`, `card`, `netbanking`, `wallet`, `other`.
- **Every expense is also kept in INR** (Phase 25, D204): `base_amount` (and `base_amount_minor`), the `exchange_rate`
  it was converted at (a decimal string; `"1"` for INR) and the rate's day `rate_date`. A $4.00 coffee on 19 Nov:
  `"amount": "4.00", "currency": "USD", "base_amount": "338.00", "exchange_rate": "84.5", "rate_date": "2026-11-19"`.
  All three are `null` only for an expense in another currency saved before Phase 25 (it's converted when edited).
- `version` goes up by one on every change (optimistic concurrency: see the MCP `delete_expense` tool).

### `POST /api/v1/expenses`

Records an expense for the signed-in person. **201 Created** with the expense, and
`Location: /api/v1/expenses/{id}`. The body is `NewExpense`; it has no owner (the session decides).

```json
{
  "amount": "450.50",
  "category_id": 1,
  "merchant": "Swiggy",
  "spent_on": "2026-11-12",
  "payment_method": "upi",
  "note": "Dinner",
  "currency": "INR"
}
```

| Field | Rules |
|---|---|
| `amount` | required; > 0; at most 12 digits, 2 after the point |
| `category_id` | required; the category must exist |
| `merchant` | required; 1–100 characters (spaces around it are trimmed) |
| `spent_on` | required date |
| `payment_method` | required; one of the six |
| `note` | optional; up to 500 characters |
| `currency` | optional; three capital letters, default `INR`. Any other currency is converted to INR by the currency agent before saving (D204): **422** `business-rule` if it has no rate for it ("SpendWise can't convert XYZ to INR yet"), **502** if it can't be reached; nothing is saved |

### `GET /api/v1/expenses`

Expenses, newest first (by date, then id), filtered on the server.

| Query parameter | Meaning |
|---|---|
| `start_date`, `end_date` | on or after / on or before (start must not be after end) |
| `category_id` | only this category |
| `merchant` | this exact merchant, any letter case |
| `search` | text in the merchant or the note (a `%` or `_` is searched literally) |
| `limit` | at most this many: 1–500, default 100 |
| `offset` | skip this many (for the next page) |

```json
{"items": [ /* ExpenseRead, ... */ ], "total": 37}
```

`total` counts every match; `items` holds at most `limit` of them.

### `GET /api/v1/expenses/{expense_id}`

One expense, or 404.

### `PATCH /api/v1/expenses/{expense_id}`

Changes only the fields you send; anything left out stays. Answers with the updated expense (its `version` raised).

```json
{"amount": "300", "note": null}
```

- Same rules as creating. A new `amount`, `currency` or `spent_on` converts the expense to INR again (other fields don't
  call the currency agent). `note` is the only field that can be `null` (it clears the note); `null` for any other field
  is a 422 ("leave a field out to keep it as it is").

### `DELETE /api/v1/expenses/{expense_id}`

Deletes for good. **204 No Content**, or 404. (The web app asks "are you sure?" first.)

## Summaries

### `GET /api/v1/summary?month=2026-11`

One month's spending in INR, biggest category first. Every expense counts, at its INR amount, whatever its currency
(D204; the `currency` parameter of D32 is gone).

```json
{
  "month": "2026-11", "currency": "INR",
  "expense_count": 12, "total_minor": 1024585, "total": "10245.85",
  "by_category": [
    {"category_id": 1, "category_name": "Food", "expense_count": 5, "total_minor": 377090, "total": "3770.90"}
  ]
}
```

A category that no longer exists shows as `"Unknown"`.

### `GET /api/v1/summary/trend?months=6`

Totals for the last `months` months (1–24, default 6), ending with the current month, oldest first. Months with no
spending are included with 0, so a chart has no gaps. In INR, like the summary.

```json
{"currency": "INR", "months": [{"month": "2026-06", "expense_count": 0, "total_minor": 0, "total": "0.00"}]}
```

## Budgets

A person's monthly limits, overall and per category (D210): each is a standing amount in INR, the same every month
until it's changed. Spending is the month's summary (every expense at its INR amount).

### `GET /api/v1/budgets?month=2026-11`

The month's spending against the budgets; without `month`, the current month. `month_elapsed_percent` is how much of
the month has gone by (100 for a past month, 0 for a future one). Every category has a line: those with a limit first
(most used first), then the others by spending. A line without a limit has only `spent`; `remaining` is negative once
over. `state` is `on_track` (below 80% of the limit), `near_limit` (80% up to the limit) or `over_limit`.

```json
{
  "month": "2026-11", "currency": "INR", "month_elapsed_percent": "66.7",
  "overall": {"spent": "5700.50", "limit": "10000.00", "remaining": "4299.50", "used_percent": "57.0", "state": "on_track"},
  "categories": [
    {"category_id": 3, "category_name": "Transport", "spent": "1200.50", "limit": "1000.00", "remaining": "-200.50",
     "used_percent": "120.1", "state": "over_limit"},
    {"category_id": 2, "category_name": "Travel", "spent": "300.00", "limit": null, "remaining": null,
     "used_percent": null, "state": null}
  ]
}
```

### `PUT /api/v1/budgets/overall`, `PUT /api/v1/budgets/categories/{category_id}`

Set (or change) a monthly limit: `{"limit": "8000"}`, above 0, at most two decimals. **204 No Content**. A bad limit or
an unknown field is a 422; a category that doesn't exist is a 422 `business-rule` problem.

### `DELETE /api/v1/budgets/overall`, `DELETE /api/v1/budgets/categories/{category_id}`

Remove a limit. **204**, or 404 if there was none (another person's budgets are never touched).

## Reports

A person's monthly report (D209). The figures are worked out by the monthly-report skill's script, which the server
runs on the person's own expenses (in INR, like the summary); the answer is checked before it's sent.

### `GET /api/v1/reports/monthly/{month}`

`month` is `YYYY-MM` (422 otherwise). The month's total against the month before (`change_percent` is null when the
month before had nothing), the daily average (over the days so far, for the running month), the totals by category
and by payment method with their share, biggest first, and the five biggest expenses. Amounts are rupees, as strings.

```json
{
  "month": "2026-11", "currency": "INR", "total": "4300.50", "previous_total": "1000.00", "change_percent": "330.1",
  "expense_count": 4, "days_counted": 20, "daily_average": "215.03",
  "by_category": [{"category": "Food", "total": "3650.50", "count": 3, "share_percent": "84.9"}],
  "by_payment_method": [{"payment_method": "upi", "total": "3850.00", "count": 3, "share_percent": "89.5"}],
  "biggest": [{"spent_on": "2026-11-12", "merchant": "Swiggy", "category": "Food", "amount": "1950.00"}]
}
```

**502** `external-service` if the report can't be made right now (the script failed or answered something unusable);
**422** `business-rule` for a month with more than 10,000 expenses.

### `GET /api/v1/reports/monthly/{month}/{format}`

The report as a file to save, in the request's language (`Accept-Language`), sent as an attachment
(`Content-Disposition: attachment; filename="spendwise-2026-11.csv"`):

| `format` | File |
|---|---|
| `csv` | `text/csv`: every expense of the month, oldest first: date, merchant, category, payment method, amount, currency, amount in INR, note. UTF-8 with a byte order mark; text from the person's data that starts with `=`, `+`, `-` or `@` gets a leading `'`, so a spreadsheet never runs it |
| `md` | `text/markdown`: the report: the total, compared with the month before, by category, by payment method, the biggest expenses, the daily average |

Errors as for the figures; another `format` is a 422.

## Receipts

### `POST /api/v1/receipts`

Uploads one receipt: `multipart/form-data` with the file in the `file` field. **201 Created** with the receipt, and
`Location: /api/v1/receipts/{id}`.

```powershell
curl.exe -F "file=@receipt.jpg" http://127.0.0.1:8000/api/v1/receipts
```

```json
{"id": 1, "media_type": "image/jpeg", "size_bytes": 182344, "created_at": "2026-11-14T09:30:00Z"}
```

- **What's accepted:** JPEG, PNG and WEBP photos, and PDFs, of 5 MB at most. The type is read from the file's first
  bytes, not its name or `Content-Type`, and `media_type` reports what was found.
- **422 `business-rule`:** an empty file, one over 5 MB, or any other kind of file. **422 `validation`:** no `file`
  field.
- Nothing is read here: the upload only keeps the file. A receipt is read when it's attached in the chat: the
  assistant sends it to the receipt agent (`POST /agent`, Phase 24).

### `GET /api/v1/receipts/{receipt_id}`

What's known about an uploaded receipt (the same object as above; not its bytes). 404 if the person has no such
receipt.

`POST /api/v1/receipts/{receipt_id}/extraction` was removed in Phase 24 (D199): reading a receipt is the receipt
agent's job now, reached only through the chat.

## The assistant

### `POST /api/v1/parse`

Reads a short note into an expense, **without saving it**. Needs the Gemini key.

```json
{"text": "Paid 450.50 at Swiggy yesterday via GPay"}
```

```json
{
  "expense": {"amount": "450.50", "currency": "INR", "category": "Food", "merchant": "Swiggy",
              "spent_on": "2026-11-12", "payment_method": "upi", "note": null},
  "missing_fields": []
}
```

`missing_fields` lists what `POST /expenses` needs that the note didn't say. `text`: 1–500 characters.

### `POST /api/v1/chat`

The agent, answering in one JSON response (no streaming, no cards or buttons). It can add, change and delete
expenses through its tools; deletes need you to confirm in words.

```json
{"message": "How much did I spend on food this month?", "thread_id": null}
```

```json
{
  "thread_id": "9f1c…",
  "reply": "You spent ₹3,770.90 on food in November.",
  "tool_calls": [{"name": "get_summary", "arguments": {"month": "2026-11"}, "ok": true}]
}
```

Send the `thread_id` back to continue the same conversation; a `thread_id` the person doesn't have is a 404. `message`: 1–2000
characters.

### `POST /api/v1/agent` (AG-UI over Server-Sent Events)

The same agent, streamed. The web app's chat panel uses this one. The request is AG-UI's `RunAgentInput`:

```json
{
  "threadId": "a3f9…", "runId": "7c21…",
  "state": {"dataVersion": 3},
  "messages": [{"id": "m1", "role": "user", "content": "Where did my money go this month?"}],
  "tools": [], "context": [], "forwardedProps": {}
}
```

- The client names the thread (1–32 characters); one the person doesn't have yet starts a new conversation (a
  thread is the person and its id together: another person's id is just a new one of their own). Only the newest user
  message is read: the server keeps the history.
- A button click (a form's Save, a card's Approve or Cancel) goes in `forwardedProps.a2uiAction` as an A2UI `action`
  message instead of a message.
- **A receipt** goes in the message's content, after its text (which may then be empty), as one `image` or
  `document` part pointing at a receipt uploaded first (`POST /receipts`). The run then reads it and answers with
  the expense form, pre-filled (no agent loop):

  ```json
  {"id": "m1", "role": "user", "content": [
    {"type": "text", "text": "team lunch"},
    {"type": "image",
     "source": {"type": "file", "value": "12", "provider": "spendwise-receipts", "mimeType": "image/jpeg"}}
  ]}
  ```

  Only this is accepted: one part, a `file` source with that provider, a valid receipt id. Several files, bytes sent
  inline or by URL, audio or video, or another provider's handle are a 422. A receipt the person doesn't have is a
  `RUN_ERROR` (`not-found`).
- Problems found before streaming starts (bad thread id, no message, an invalid action or attachment) are ordinary
  **422 problem** responses. Once streaming has started, a failure is a `RUN_ERROR` event.

The answer is `text/event-stream`, one AG-UI event per `data:` line, plus a `: ping` comment every 15 s:

| Event | Carries |
|---|---|
| `RUN_STARTED` / `RUN_FINISHED` | the thread and run ids |
| `TEXT_MESSAGE_START` / `_CONTENT` / `_END` | the reply, piece by piece |
| `TOOL_CALL_START` | the tool's name, and `metadata.labels` (`running` / `done` / `failed`) for its status chip |
| `TOOL_CALL_ARGS` / `TOOL_CALL_END` | the arguments' JSON; END means "complete", not "run" |
| `TOOL_CALL_RESULT` | that the tool ran, and `metadata.ok`; `content` is empty (the tool's text is for the model) |
| `STATE_SNAPSHOT` | `{"dataVersion": n}` after a tool changed data: the pages reload |
| `CUSTOM` named `a2ui` | an A2UI message: a card, a form (with `metadata.source`: `model`, `fallback` or `receipt`), or an Approve/Cancel card |
| `RUN_ERROR` | `message` (written for people, in the request's language) and `code`, the problem kind as in a problem's `type` (`external-service`, `not-found`, `business-rule`, `internal`) |

To watch it raw:

```powershell
curl.exe -N -X POST http://127.0.0.1:8000/api/v1/agent -H "Content-Type: application/json" `
  -d '{"threadId":"t1","runId":"r1","state":{},"messages":[{"id":"m","role":"user","content":"hi"}],"tools":[],"context":[],"forwardedProps":{}}'
```

The full event flow, cards and approvals: [assistant_architecture.md](assistant_architecture.md).

### `GET /api/v1/threads/{thread_id}`

A stored conversation, readable: user messages, replies, tool calls (`name({...})`) and tool results, oldest first.
The model's private reasoning is stored but not shown. 404 if the person has no such thread.

```json
{"thread_id": "9f1c…", "messages": [{"turn": 1, "kind": "user_text", "text": "hi", "created_at": "…"}]}
```

## MCP tools and resources

The MCP server named `spendwise`, over stdio (`backend\mcp_stdio.py`) or Streamable HTTP at `/mcp/`. **Every
request acts for one person** (D191): over HTTP, the owner of the personal access token in
`Authorization: Bearer <token>` (made in Settings; 401 without a working one); over stdio, the owner of the token in
the `SPENDWISE_TOKEN` environment variable. Host and Origin must be local. The tools and `expenses://recent` see and
change only that person's expenses. Every tool returns a typed result: its JSON Schema is the tool's
`outputSchema`, and the result arrives as `structuredContent`.

| Tool | Annotations | Arguments | Returns |
|---|---|---|---|
| `add_expense` | adds data | `amount`, `category` (name), `merchant`, `spent_on`, `payment_method`, `note?`, `currency?` | `{saved: ExpenseView, budget_alerts: [BudgetAlert]}` |
| `list_expenses` | read-only | `start_date?`, `end_date?`, `category?`, `merchant?`, `search?` | `{count, expenses: [ExpenseView] (≤ 50), truncated}` |
| `get_expense` | read-only | `expense_id` | `{expense: ExpenseView}` |
| `get_summary` | read-only | `month` (YYYY-MM), `currency?` | the month summary plus `previous_month` |
| `update_expense` | changes data | `expense_id`, any of `amount`, `category`, `merchant`, `spent_on`, `payment_method`, `currency`, `note`, `clear_note` | `{updated: ExpenseView, budget_alerts: [BudgetAlert]}` |
| `delete_expense` | destructive | `expense_id`, `confirmed` (must be exactly `true`), `expected_version?` | `{deleted: ExpenseView}` |
| `get_monthly_report` | read-only | `month` (YYYY-MM) | the month's report, as `GET /reports/monthly/{month}` (D209) |
| `get_budgets` | read-only | `month?` (YYYY-MM; empty: this month) | the budgets' status, as `GET /budgets` (D211) |
| `set_budget` | adds data | `limit` (rupees), `category?` (name; empty: overall) | this month's budgets' status |

- `ExpenseView`: `id`, `amount` (rupees), `currency`, `category` (name), `merchant`, `note`, `spent_on`,
  `payment_method`, `version`.
- `BudgetAlert`: `category` (null for the overall budget), `state` (`near_limit` or `over_limit`), `spent`, `limit`,
  `used_percent`: a budget the save moved near (80%) or over its monthly limit (D211; empty when none).
- Optional text arguments treat `""` as "not given".
- `delete_expense` deletes nothing unless `confirmed` is the boolean `true` (not `"true"` or `1`). With
  `expected_version`, it deletes only if the expense is still at that version: show the user the expense
  (`get_expense`), then pass its `version`.
- Expected problems (unknown category, amount ≤ 0, a missing expense) come back as tool errors with a clear message;
  unexpected ones as a generic error (details in the server log).

| Resource | Content |
|---|---|
| `expenses://categories` | the categories (`id`, `name`, `icon`) as JSON |
| `expenses://recent` | the 20 newest expenses (`ExpenseView`) as JSON |
