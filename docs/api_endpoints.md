# API Endpoints

Everything the backend exposes: the REST API, the assistant's AG-UI stream, and the MCP server. The interactive
version is Swagger UI at http://127.0.0.1:8000/docs; the machine-readable one is `/openapi.json` (the web app's types
are generated from it).

## Conventions

| | |
|---|---|
| **Base URL** | `http://127.0.0.1:8000/api/v1` for every REST route. `/health` and `/mcp/` stay at the root. A breaking change gets `/api/v2`. |
| **Format** | JSON in and out. Field names are `snake_case` (AG-UI's stream uses `camelCase`, as its spec does). |
| **Money** | Requests take rupees as a decimal string (`"450.50"`, at most 2 decimals). Responses give both `amount_minor` (paise, an integer: exact, for arithmetic) and `amount` (rupees, a string: for display). |
| **Dates** | `YYYY-MM-DD`; months `YYYY-MM` (years 1900–2099); timestamps ISO 8601 in UTC. |
| **Ids** | positive integers up to 2⁶³−1; larger ones are a 422, not a crash. |
| **Language** | send `Accept-Language` (`hi`, `hi-IN,hi;q=0.9,en;q=0.5`): error `detail`s, and `/chat`'s and `/agent`'s texts (cards, chip labels, fixed replies, the model's reply), come in the best language the server speaks (English, Hindi), else English. Data (category names, merchants, notes) is never translated; problem `title`s stay English. |
| **Unknown fields** | rejected (422), in bodies and query strings, so a typo like `merchnat` is an error, not a silent no-op. |
| **Auth** | none yet for REST (single-user, local; login arrives with the auth phase). `/mcp/` requires a bearer token. Browsers can only call the API from the origins in `CORS_ORIGINS`. |

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
| 404 | `not-found` | the resource in the URL doesn't exist |
| 422 | `validation` | the request's shape is wrong; adds `errors: [{location, field, message}]` |
| 422 | `business-rule` | well-formed but against a rule: amount ≤ 0, unknown category, an expense that changed since it was shown |
| 401 | `unauthorized` | `/mcp/` without the right bearer token |
| 4xx | `http` | FastAPI's own (404 unknown URL, 405 wrong method with an `Allow` header) |
| 500 | `internal` | a bug; the details go to the server log only |
| 502 | `external-service` | Gemini (or a remote MCP server) failed: bad key, quota, overload |

Validation example:

```json
{
  "type": "urn:spendwise:problem:validation", "title": "Invalid request", "status": 422,
  "detail": "merchant: Field required; merchnat: Extra inputs are not permitted",
  "instance": "/api/v1/expenses",
  "errors": [
    {"location": "body", "field": "merchant", "message": "Field required"},
    {"location": "body", "field": "merchnat", "message": "Extra inputs are not permitted"}
  ]
}
```

## Health

### `GET /health`

`{"status": "ok"}` when the server is up and its database answers. Cheap: meant for monitors.

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
  "version": 1
}
```

- `payment_method`: one of `cash`, `upi`, `card`, `netbanking`, `wallet`, `other`.
- `version` goes up by one on every change (optimistic concurrency: see the MCP `delete_expense` tool).

### `POST /api/v1/expenses`

Records an expense. **201 Created** with the expense, and `Location: /api/v1/expenses/{id}`.

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
| `currency` | optional; three capital letters, default `INR` |

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

- Same rules as creating. `note` is the only field that can be `null` (it clears the note); `null` for any other field
  is a 422 ("leave a field out to keep it as it is").

### `DELETE /api/v1/expenses/{expense_id}`

Deletes for good. **204 No Content**, or 404. (The web app asks "are you sure?" first.)

## Summaries

### `GET /api/v1/summary?month=2026-11&currency=INR`

One month's spending in one currency (totals can't mix currencies), biggest category first.

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

### `GET /api/v1/summary/trend?months=6&currency=INR`

Totals for the last `months` months (1–24, default 6), ending with the current month, oldest first. Months with no
spending are included with 0, so a chart has no gaps.

```json
{"currency": "INR", "months": [{"month": "2026-06", "expense_count": 0, "total_minor": 0, "total": "0.00"}]}
```

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

Send the `thread_id` back to continue the same conversation; an unknown `thread_id` is a 404. `message`: 1–2000
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

- The client names the thread (1–32 characters); an unknown one starts a new conversation. Only the newest user
  message is read: the server keeps the history.
- A button click (a form's Save, a card's Approve or Cancel) goes in `forwardedProps.a2uiAction` as an A2UI `action`
  message instead of a message.
- Problems found before streaming starts (bad thread id, no message, an invalid action) are ordinary **422 problem**
  responses. Once streaming has started, a failure is a `RUN_ERROR` event.

The answer is `text/event-stream`, one AG-UI event per `data:` line, plus a `: ping` comment every 15 s:

| Event | Carries |
|---|---|
| `RUN_STARTED` / `RUN_FINISHED` | the thread and run ids |
| `TEXT_MESSAGE_START` / `_CONTENT` / `_END` | the reply, piece by piece |
| `TOOL_CALL_START` | the tool's name, and `metadata.labels` (`running` / `done` / `failed`) for its status chip |
| `TOOL_CALL_ARGS` / `TOOL_CALL_END` | the arguments' JSON; END means "complete", not "run" |
| `TOOL_CALL_RESULT` | what the tool returned, and `metadata.ok` |
| `STATE_SNAPSHOT` | `{"dataVersion": n}` after a tool changed data: the pages reload |
| `CUSTOM` named `a2ui` | an A2UI message: a card, a form (with `metadata.source`: `model` or `fallback`), or an Approve/Cancel card |
| `RUN_ERROR` | `message` (meant for people) and `code` |

To watch it raw:

```powershell
curl.exe -N -X POST http://127.0.0.1:8000/api/v1/agent -H "Content-Type: application/json" `
  -d '{"threadId":"t1","runId":"r1","state":{},"messages":[{"id":"m","role":"user","content":"hi"}],"tools":[],"context":[],"forwardedProps":{}}'
```

The full event flow, cards and approvals: [assistant_architecture.md](assistant_architecture.md).

### `GET /api/v1/threads/{thread_id}`

A stored conversation, readable: user messages, replies, tool calls (`name({...})`) and tool results, oldest first.
The model's private reasoning is stored but not shown. 404 for an unknown thread.

```json
{"thread_id": "9f1c…", "messages": [{"turn": 1, "kind": "user_text", "text": "hi", "created_at": "…"}]}
```

## MCP tools and resources

The MCP server named `spendwise`, over stdio (`backend\mcp_stdio.py`) or Streamable HTTP at `/mcp/` (only when
`MCP_TOKEN` is set; send `Authorization: Bearer <token>`; Host and Origin must be local). Every tool returns a typed
result: its JSON Schema is the tool's `outputSchema`, and the result arrives as `structuredContent`.

| Tool | Annotations | Arguments | Returns |
|---|---|---|---|
| `add_expense` | adds data | `amount`, `category` (name), `merchant`, `spent_on`, `payment_method`, `note?`, `currency?` | `{saved: ExpenseView}` |
| `list_expenses` | read-only | `start_date?`, `end_date?`, `category?`, `merchant?`, `search?` | `{count, expenses: [ExpenseView] (≤ 50), truncated}` |
| `get_expense` | read-only | `expense_id` | `{expense: ExpenseView}` |
| `get_summary` | read-only | `month` (YYYY-MM), `currency?` | the month summary plus `previous_month` |
| `update_expense` | changes data | `expense_id`, any of `amount`, `category`, `merchant`, `spent_on`, `payment_method`, `currency`, `note`, `clear_note` | `{updated: ExpenseView}` |
| `delete_expense` | destructive | `expense_id`, `confirmed` (must be exactly `true`), `expected_version?` | `{deleted: ExpenseView}` |

- `ExpenseView`: `id`, `amount` (rupees), `currency`, `category` (name), `merchant`, `note`, `spent_on`,
  `payment_method`, `version`.
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
