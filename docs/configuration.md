# Configuration

Every setting SpendWise reads, where it comes from, and its default. Secrets never live in code: they go in `.env`
(git-ignored), and `.env.example` (committed) lists every name with no real values.

## How the backend reads settings

All backend settings are one Pydantic `Settings` class in `backend/app/infrastructure/config.py` (pydantic-settings):

- read from the **environment**, then from **`.env` in the project folder**; a real environment variable wins;
- names are case-insensitive (`GEMINI_MODEL` → `get_settings().gemini_model`);
- an empty value (`GEMINI_MODEL=`) counts as **not set**, so the default applies;
- unknown names in `.env` are ignored (it may hold settings for other tools);
- secrets are `SecretStr`, so printing the settings never shows the key;
- read **once**, by `get_settings()` on its first call (when the app is built, not when a file is imported), and
  kept for the process: after changing `.env`, restart the server.

## Backend settings (`.env`)

| Setting | Default | Used for |
|---|---|---|
| `GEMINI_API_KEY` | not set | The assistant (`/chat`, `/agent`) and `/parse`. Without it, those routes fail with a message saying the key is missing; everything else works. Get one at https://aistudio.google.com/apikey |
| `GEMINI_MODEL` | not set | Which Gemini model answers, e.g. `gemini-3.5-flash-lite`. Model ids and free-tier limits: [gemini.md](gemini.md) |
| `DATABASE_URL` | `sqlite:///<project>/backend/spendwise.db` | Any SQLAlchemy URL. Point it at a copy to experiment safely |
| `MODEL_REQUESTS_PER_MINUTE`, `MODEL_REQUESTS_PER_DAY` | `10`, `300` | How many requests to the routes that call the model (`/agent`, `/chat`, `/parse`; a receipt is read through `/agent`) each person may make per minute and per day (UTC); one more is a 429 (D194). Counted in memory, per server process |
| `SKILLS_DIR` | `<project>/skills` | The Agent Skills folder (D208): one folder per skill with its `SKILL.md`, read once, at the first turn (restart to pick up an edited skill). A skill's `scripts/*.py` are run by the server with the backend's own Python (D209) |
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
| `PUBLIC_URL` | `http://localhost:5173` | The origin people open the web app at (no path). The redirect URI is `<PUBLIC_URL>/api/v1/auth/callback` and signing out ends at `<PUBLIC_URL>/sign-in`: register both at the provider exactly. When it's `https://`, the backend's answers also carry HSTS (D193) |
| `SESSION_ENCRYPTION_KEYS` | `[]` | Fernet keys, a JSON list, newest first, that seal the ID token each session keeps. Rotate by putting a new one first and removing the old one 14 days later. Make one: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `COOKIE_SECURE` | `true` | The cookies' Secure flag and `__Host-` prefix. Browsers accept Secure cookies on `http://localhost`; turn it off only for one that doesn't, never in production |

Example `.env`:

```ini
GEMINI_API_KEY=AIza...your key...
GEMINI_MODEL=gemini-3.5-flash-lite
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

The browser code reads no settings: it calls the API on its own origin (`/api/v1/...`, D184). The Next.js server
has two, read in Node and never shipped to the browser (D188):

| Setting | Default | Used for |
|---|---|---|
| `API_PROXY_TARGET` | `http://127.0.0.1:8000` | Where Next.js forwards `/api/v1/...`: the backend. Read by `next.config.ts` when `next dev` starts, and **compiled into the build** by `next build`: for production, set it before building (`next start` doesn't read it) |
| `PUBLIC_URL` | `http://localhost:5173` | The address people open the app at: link previews, the sitemap and robots.txt are built on it (`app/_seo/seo.ts`). The same value as the backend's `PUBLIC_URL`; robots.txt and the sitemap are generated at build time, so set it before building too. When it's `https://`, the pages also get HSTS and `upgrade-insecure-requests` (D193); set it before `next build` |

Next.js reads `web/.env` (a real environment variable wins). Restart `npm run dev` after a change, and rebuild
for production. Anything in a `NEXT_PUBLIC_` variable would be baked into the JavaScript every visitor downloads, so
none is used, and a secret never goes in one.

App-wide constants, each defined once:

| Value | Where |
|---|---|
| the app's name and one-line description | `src/shared/config/app.ts` (also the pages' metadata, `app/_seo/seo.ts`) |
| page addresses | `src/shared/config/routes.ts` |
| the languages (English, Hindi), each one's locale for numbers and dates, writing direction and date picker locale, the default (and fallback) language, where the choice is saved (`spendwise-language`) | `src/shared/i18n/languages.ts` |
| theme storage key, the dark class, the boot script | `src/shared/theme/theme-constants.ts` (the root layout, `app/layout.tsx`, puts the boot script into `<head>`) |
| the proxy's timeout (`PROXY_TIMEOUT_MS = 180 s`), no compression | `next.config.ts` (D188) |
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

## The agents' settings (`.env`)

**On `main`, nothing:** the backend hosts the three A2A agents in its own process (D207), with its own model and
clock, and gives each a random key at startup. The settings below matter only to run an agent **on its own**
(`run-agent.ps1`), each with its own `AgentSettings` built on the agent kit's configuration
(`agents/agent_kit/settings.py`), read from the same `.env`. (On the `multi-server` branch the backend reaches the
agents as services, and also reads `RECEIPT_AGENT_URL`/`KEY`, `INSIGHTS_AGENT_URL`/`KEY` and `CURRENCY_AGENT_URL`/
`KEY`.)

| Setting | Default | Used for |
|---|---|---|
| `GEMINI_API_KEY`, `GEMINI_MODEL` | not set | The same as the backend's: the agent reads each receipt with one Gemini call |
| `RECEIPT_AGENT_KEY` | **required** | The key a client must send as `Authorization: Bearer <key>` (D197). At least 32 characters; the agent won't start without it, so it never runs open. It's yours to make: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `RECEIPT_AGENT_PORT` | `9001` | The port it listens on. The host is fixed: `127.0.0.1` only, so nothing outside this machine can reach it |
| `INSIGHTS_AGENT_KEY` | **required** (insights agent) | As above, for the insights agent (Phase 25), which uses the Gemini settings too |
| `INSIGHTS_AGENT_PORT` | `9002` | The insights agent's port |
| `CURRENCY_AGENT_KEY` | **required** (currency agent) | As above, for the currency agent; at least 32 characters |
| `CURRENCY_AGENT_PORT` | `9003` | The currency agent's port (keep `CURRENCY_AGENT_URL` in step). It needs no Gemini settings |

Fixed in code: the host (`agent_kit/settings.HOST`), the receipt agent's largest file (5 MB,
`contract.MAX_RECEIPT_BYTES`) and request (`agent_kit/http.request_limit`), how many tasks an agent remembers
(`agent_kit/task_store.MAX_KEPT_TASKS`, 20), and the currency agent's mock rates (`currency/rates.MOCK_INR_PER_UNIT`:
made-up values, D203).

## Run-time options

| | |
|---|---|
| `.\run-agent.ps1 receipt`, `insights`, `currency` | optional: runs one agent on its own, on `:9001`, `:9002` or `:9003` (the backend doesn't use it: it hosts its own); it needs its key |
| `.\run.ps1 --port 8001` | extra arguments go to uvicorn (then set `API_PROXY_TARGET=http://127.0.0.1:8001` in `web/.env`) |
| `npx next dev --port 5175` | the web dev server on another port (then set `PUBLIC_URL` on both sides, since sign-in sends people back to it) |
| `npm run build`, then `npm run start` | the production build, served on :5173 (`API_PROXY_TARGET` and `PUBLIC_URL` are taken when building) |

## MCP clients

MCP over HTTP (`/mcp/`) needs no setting: every request carries a **personal access token**, made on the Settings
page, and acts for its owner (D191). The stdio server (`backend\mcp_stdio.py`) reads its token from the environment
the MCP client starts it with, not from `.env`:

| Variable | Where | Used for |
|---|---|---|
| `SPENDWISE_TOKEN` | the MCP client's config for the stdio server (e.g. Claude Desktop's `env`) | the person the stdio server acts for; checked on every tool call, so a revoked or expired token stops it at once |

`MCP_TOKEN` and `MCP_URL` are gone (Phase 23): a line left in `.env` is ignored.
