# Configuration

Every setting SpendWise reads, where it comes from, and its default. Secrets never live in code: they go in `.env`
(git-ignored), and `.env.example` (committed) lists every name with no real values.

## How the backend reads settings

All backend settings are one Pydantic `Settings` class in `backend/app/infrastructure/config.py` (pydantic-settings):

- read from the **environment**, then from **`.env` in the project folder**; a real environment variable wins;
- names are case-insensitive (`GEMINI_MODEL` → `settings.gemini_model`);
- an empty value (`MCP_URL=`) counts as **not set**, so the default applies;
- unknown names in `.env` are ignored (it may hold settings for other tools);
- secrets are `SecretStr`, so printing the settings never shows the key;
- read **once at startup**: after changing `.env`, restart the server.

## Backend settings (`.env`)

| Setting | Default | Used for |
|---|---|---|
| `GEMINI_API_KEY` | not set | The assistant (`/chat`, `/agent`) and `/parse`. Without it, those routes fail with a message saying the key is missing; everything else works. Get one at https://aistudio.google.com/apikey |
| `GEMINI_MODEL` | not set | Which Gemini model answers, e.g. `gemini-3.5-flash-lite`. Model ids and free-tier limits: [gemini.md](gemini.md) |
| `DATABASE_URL` | `sqlite:///<project>/backend/spendwise.db` | Any SQLAlchemy URL. Point it at a copy to experiment safely |
| `MCP_TOKEN` | not set | Turns on MCP over HTTP at `/mcp/`, guarded by this shared secret (`Authorization: Bearer <token>`). Not set: no `/mcp/` over HTTP. Make one: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `MCP_URL` | not set | Only if the expense tools run as a **separate** MCP server: its URL (keep the trailing slash). Not set: the assistant calls this app's own MCP server in-process. When set, `MCP_TOKEN` is sent to it |
| `UPLOADS_DIR` | `<project>/backend/uploads` | The folder uploaded receipts are kept in, by random names (created on the first upload; git-ignored). It goes with the database: a copy of one needs a copy of the other |

### Sign-in

Signing in through an OpenID Connect provider (Phase 22, D185). Until the issuer, client id, secret and an
encryption key are all set, **nobody can sign in, and every API route answers 401** (fail closed). Setting up a
provider, and the values each one needs: [identity_provider.md](identity_provider.md).

| Setting | Default | Used for |
|---|---|---|
| `OIDC_ISSUER` | not set | The provider's issuer URL (its discovery document is at `<issuer>/.well-known/openid-configuration`). Changing it ends every session (a session remembers its issuer) |
| `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` | not set | This app's registration at the provider, a confidential web client. The secret never leaves the server |
| `OIDC_SCOPES` | `openid profile email` | Scopes every sign-in asks for, space-separated |
| `OIDC_LOGIN_OPTIONS` | `[]` | The sign-in page's buttons, a JSON list of `{"key", "label", "extra_scopes", "extra_params"}`: what each adds to the request so the provider skips to that way of signing in. A parameter the flow sets itself (`state`, `redirect_uri`...) is refused at startup. Empty: one button, the provider's own page |
| `OIDC_ROLE_CLAIM`, `OIDC_REQUIRED_ROLE` | not set | Where the tokens list roles (a claim's name or a dotted path) and the role a person must have. Unset: anyone the provider lets sign in may |
| `PUBLIC_URL` | `http://localhost:5173` | The origin people open the web app at (no path). The redirect URI is `<PUBLIC_URL>/api/v1/auth/callback` and signing out ends at `<PUBLIC_URL>/sign-in`: register both at the provider exactly |
| `SESSION_ENCRYPTION_KEYS` | `[]` | Fernet keys, a JSON list, newest first, that seal the ID token each session keeps. Rotate by putting a new one first and removing the old one 14 days later. Make one: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `COOKIE_SECURE` | `true` | The cookies' Secure flag and `__Host-` prefix. Browsers accept Secure cookies on `http://localhost`; turn it off only for one that doesn't, never in production |

Example `.env`:

```ini
GEMINI_API_KEY=AIza...your key...
GEMINI_MODEL=gemini-3.5-flash-lite
# MCP_TOKEN=change-me-to-a-long-random-string
OIDC_ISSUER=https://spendwise-abc.zitadel.cloud
OIDC_CLIENT_ID=...
OIDC_CLIENT_SECRET=...
SESSION_ENCRYPTION_KEYS=["...a Fernet key..."]
```

## Fixed in code (change the constant, not `.env`)

These are deliberate design values, each defined once, next to the code it governs.

| Value | Where | What it controls |
|---|---|---|
| `API_PREFIX = "/api/v1"`, `API_VERSION = "1.0.0"`, `MCP_PATH = "/mcp"` | `infrastructure/config.py` | URLs and the OpenAPI version |
| Gemini timeout 60 s, 2 attempts, retry only on 5xx | `infrastructure/llm/gemini.py` | how long a model call may hang ([gemini.md](gemini.md#timeouts-and-retries)) |
| `MAX_STEPS = 5` | `assistant/agent/agent.py` | model round trips per message |
| `REASONING_EFFORT = low` | `assistant/agent/agent.py` | how hard the model thinks (deeper is slower) |
| `MAX_HISTORY_TURNS = 10` | `assistant/application/assistant.py` | earlier turns resent with each message (cost vs memory) |
| `TTL_MINUTES = 15`, `MAX_PENDING = 200` | `assistant/approvals/models.py` | how long a delete card works, and how many are kept |
| `TIMEOUT_SECONDS = 15` | `assistant/tools/mcp_adapter.py` | how long a tool call may take |
| `MAX_ROWS = 50`, `RECENT_ROWS = 20` | `mcp/tools/list_expenses.py`, `mcp/resources.py` | rows an MCP list returns (each costs tokens) |
| `DEFAULT_LIST_LIMIT = 100`, `MAX_LIST_LIMIT = 500` | `expenses/values.py` | `GET /expenses` page size |
| `DEFAULT_TREND_MONTHS = 6`, `MAX_TREND_MONTHS = 24` | `expenses/values.py` | the trend's length |
| `MAX_MESSAGE_LENGTH = 2000` | `assistant/api/schemas.py` | one chat message (also the web text box's limit) |
| `MAX_RECEIPT_MB = 5`, `ReceiptMediaType` (JPEG, PNG, WEBP, PDF), `MAX_LINE_ITEMS = 50` | `receipts/values.py` | what may be uploaded as a receipt, and how many lines the model may list |
| `DEFAULT_CURRENCY = "INR"`, `CURRENCY_SYMBOLS` (a chart's unit) | `core/money.py` | the currency assumed; amounts are written in their currency's CLDR format (Babel) |
| the server's languages (English, Hindi), each one's CLDR locale and English name (for the model) | `core/i18n/languages.py` | which `Accept-Language` the server answers in; the web app's table is typed against them |
| Log level `INFO` for `app.*` | `infrastructure/logging.py` | message text and tool arguments appear only at `DEBUG` |
| `SESSION_IDLE = 1 day`, `SESSION_LIFETIME = 14 days`, `RENEW_AFTER = 12 h` | `accounts/values.py` | when a session ends unused, when it ends anyway, how often its renewal is written |
| `LOGIN_ATTEMPT_TTL = 10 min`, `MAX_LOGIN_ATTEMPTS = 500` | `accounts/values.py` | how long a sign-in may take at the provider, how many unfinished ones are kept |
| `SIGN_IN_PAGE = "/sign-in"`, `CALLBACK_PATH = "/auth/callback"` | `accounts/values.py` | where failed sign-ins and sign-outs end; the callback's path (shared with the web app) |
| `CSRF_HEADER = "X-CSRF"`, the cookies' names (`__Host-spendwise-session`, `__Host-spendwise-login`) | `web/auth.py` | the header every API call carries; the cookies the browser holds |
| `CLOCK_SKEW = 60 s`, `ALLOWED_ALGORITHMS` (RS, PS, ES, EdDSA) | `infrastructure/identity/tokens.py` | how far the provider's clock may be off; which token signatures are accepted |
| `METADATA_TTL = 1 h`, `KEYS_REFETCH_INTERVAL = 1 min`, `HTTP_TIMEOUT_SECONDS = 10` | `infrastructure/identity/` | how long the provider's metadata is trusted, how often its keys may be fetched again, how long a call to it may take |

## Web settings (`web/.env`)

The browser code reads no settings: it calls the API on its own origin (`/api/v1/...`, D184). The dev server has one:

| Setting | Default | Used for |
|---|---|---|
| `API_PROXY_TARGET` | `http://127.0.0.1:8000` | Where the dev server (`npm run dev`, also `npm run preview`) forwards `/api/v1/...`: the backend. Read by `vite.config.ts`, in Node; never shipped to the browser |

`vite.config.ts` reads `web/.env` when the dev server starts (a real environment variable wins): restart
`npm run dev` after a change. Anything in a `VITE_` variable would be baked into the JavaScript every visitor
downloads, so none is used, and a secret never goes in one.

App-wide constants, each defined once:

| Value | Where |
|---|---|
| the app's name | `src/shared/config/app.ts` (also put into `index.html`'s `<title>` at build time) |
| page addresses | `src/shared/config/routes.ts` |
| the languages (English, Hindi), each one's locale for numbers and dates, writing direction and date picker locale, the default (and fallback) language, where the choice is saved (`spendwise-language`) | `src/shared/i18n/languages.ts` |
| theme storage key, the dark class, the boot script | `src/shared/theme/theme-constants.ts` (the boot script is injected into `index.html` by `vite.config.ts`) |
| what kinds of data a change touches | `src/shared/config/data-scopes.ts` |

## The generated contract

Values the backend and the web app must agree on are **generated from the backend**, never typed twice:

| File | Holds | Regenerate with |
|---|---|---|
| `web/openapi.json` | the REST API's OpenAPI document | `.\.venv\Scripts\python.exe backend\scripts\export_contracts.py` |
| `web/src/shared/api/contracts.gen.ts` | API prefix, problem media type, currency, payment-method labels, "Unknown", limits, A2UI catalogs / components / chart types / actions, AG-UI event names and keys, sign-in's header, page, query parameters and failure codes (`AUTH`) | the same script |
| `web/src/shared/api/schema.gen.ts` | TypeScript types for every route, plus enum value lists | `npm run gen:api` in `web/` (openapi-typescript 7.13, run through `npx`) |

Run both after changing an API, a label or a limit, and commit the results with the change. A forgotten
regeneration shows up as a TypeScript error, or a value that doesn't match.

## Run-time options

| | |
|---|---|
| `.\run.ps1 --port 8001` | extra arguments go to uvicorn (then set `API_PROXY_TARGET=http://127.0.0.1:8001` in `web/.env`) |
| `npm run dev -- --port 5175` | the web dev server on another port; nothing else to change (the API is reached through it) |
