# Security

What protects SpendWise today, why, and what's still missing before it could run anywhere but your own machine.

**Scope today:** one person, one machine. The backend listens on `127.0.0.1`, the web app on `localhost`, and
there are no user accounts yet. The measures below are chosen for that setting; the last section lists what a
deployment would need.

## Secrets

| Measure | How |
|---|---|
| Kept out of code and git | `GEMINI_API_KEY` and `MCP_TOKEN` live in `.env`, which is git-ignored; `.env.example` holds only names |
| Never printed | settings hold them as `SecretStr` (masked when printed); the key is passed to the Gemini client explicitly and nowhere else |
| Never in the browser | the web app has no secrets; anything in a `VITE_` variable would ship to every visitor, so none is used for secrets |
| Checked before commits | each commit is checked so that the key's value doesn't appear in the staged changes, and no `.env` or `*.db` is staged |

## The browser and the API

- **CORS allow-list:** only the origins in `CORS_ORIGINS` (the Vite dev server by default) may read API responses
  from a browser. Any other website you visit can't use the API through your browser. Allowed methods and headers are
  listed explicitly. Even an unexpected error's 500 response carries the CORS headers (the error middleware sits
  inside CORS), so the web app reads the problem instead of guessing.
- **No cookies, no sessions:** there's nothing for cross-site request forgery to ride on.
- **Input validation everywhere:** unknown fields and query parameters are rejected, text has length limits, ids are
  bounded (no driver overflow), months are limited to 1900–2099, amounts to 2 decimals and > 0. See
  [api_endpoints.md](api_endpoints.md).
- **No internals in errors:** an unexpected error becomes a generic 500 problem; the traceback goes only to the server
  log.

## MCP

| Transport | Protection |
|---|---|
| stdio (`mcp_stdio.py`) | only the program that starts it (Inspector, Claude Desktop) can talk to it |
| HTTP (`/mcp/`) | **off unless `MCP_TOKEN` is set**. Then: every request needs `Authorization: Bearer <token>`, compared in constant time (no timing leaks), scheme case-insensitive; and the SDK's **DNS-rebinding protection** refuses Host and Origin headers that aren't local (421/403), so a web page can't reach the tools through your browser |
| in-process (the assistant) | no network at all: the assistant calls the MCP server object directly |

The MCP spec requires Streamable HTTP servers to validate `Origin` and recommends authentication
([sources.md](sources.md#10-mcp-python-sdk-230-in-process-clients-structured-output-http-security-refactor)).

## The AI assistant

An LLM can be confused, or steered by text it reads (prompt injection). So the design never relies on the model
behaving:

| Risk | Defence |
|---|---|
| The model deletes something you didn't mean to | In the web panel it **can't delete**: its delete becomes an Approve/Cancel card, and only your click deletes (server-enforced) |
| A forged or replayed Approve | The server decides what's deleted from its own record of the card; each card works once, only in its own conversation, for 15 minutes; the browser's other data is ignored |
| The expense changes between the card and Approve | Approve deletes only the **version** the card showed; the check is part of the `DELETE` statement itself |
| A client sending `confirmed: "true"`, `1` or the old `confirmed=false` "preview" | The MCP tool requires `confirmed` to be the boolean `true`; anything else (or nothing) deletes nothing |
| A model-written form with a button that approves a delete | Model-written forms may only contain `save_expense` buttons and form components; otherwise the built-in form is used |
| Instructions hidden in a merchant name, note or tool result | The system instruction says tool results are data; `/parse` treats the note as data and can only answer the schema; form values are sent labelled as data |
| The model inventing a category | `/parse` gives the categories as an enum; tools reject unknown categories with the valid list |
| Runaway cost or hangs | at most 5 model calls per message, 60 s × 2 attempts per call, no retry on quota errors, 15 s per tool call, input length limits |

## The A2UI renderer

Cards and forms are data from the server (partly written by the model), drawn by the browser. The renderer treats
them as untrusted:

- no HTML or code: only an allow-list of components mapped to the app's own; text is rendered by React (escaped);
- unknown catalogs and components become a harmless "Can't show …" note;
- server values are only used as lookup keys (class names, icons, chart colours from a fixed list), never pasted into
  styles; shadcn's chart writes its config into a `<style>` tag, so that config is fixed;
- data-model paths refuse `__proto__`, `prototype` and `constructor` (no prototype pollution);
- a card that would draw over 300 components, nest deeper than 12 or contain itself is refused before drawing;
- every card has its own error boundary: a broken card can't take the app down.

Every AG-UI event is validated with `@ag-ui/core`'s schemas before it's used.

## Logging and privacy

- INFO logs record what happened (message length, tool names, ok or error, token counts), never the content: message
  text and tool arguments are financial data and appear only at DEBUG.
- Gemini is called with `store=False`, so Google doesn't keep the conversation for later retrieval. On the free tier,
  Google's data-use terms still apply to what's sent ([gemini.md](gemini.md)).
- The database is a local file, git-ignored.

## Dependencies

Every backend and web dependency is pinned to an exact version (`requirements.txt`, `package.json`, plus
`package-lock.json`), so an install can't silently pull a new release.

## Not done yet: before running anywhere but your own machine

| Gap | Why it matters | What to add |
|---|---|---|
| **No login** for the REST API and the web app | anyone who can reach the port can read and change everything | user accounts and authentication (the planned auth phase); then per-user data |
| **No HTTPS** | traffic, including any future tokens, would be readable | TLS at a reverse proxy |
| **No security headers** | no Content-Security-Policy, HSTS, `X-Content-Type-Options`, `frame-ancestors` | set them at the proxy or in a middleware; a CSP also limits the damage of any future injection |
| **No rate limiting** | the model-backed routes (`/chat`, `/agent`, `/parse`) spend your Gemini quota | per-user/IP limits on those routes |
| **SQLite file** | one machine, file permissions only | Postgres with a least-privilege database user |
| **No audit trail** | can't tell who changed what | record changes (who, when, before/after) once users exist |
