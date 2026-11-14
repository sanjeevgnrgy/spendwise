# Phase 22: Signing in

**Goal:** only people you allow can use SpendWise. They sign in through an **identity provider** (ZITADEL to begin
with, offering Google and GitHub) on its own hosted login page, and the backend keeps the session. Built in four parts,
by the owner's choice:

- **Part 1:** one origin. The web app reaches the API on its own address, through a proxy, and CORS is removed.
  Decision: D184. (This file, so far.)
- **Part 2:** the backend. A provider-neutral sign-in port and a standard OpenID Connect adapter, the `accounts`
  module (users, their identities, server-side sessions, login attempts), the sign-in routes, every other route
  locked, and the `X-CSRF` header.
- **Part 3:** the web app. The sign-in page, a gate around the pages, the user menu, sign-out.
- **Part 4:** a real provider. The ZITADEL setup guide, a live sign-in with Google and GitHub, back-channel logout if
  the provider supports it, and a production checklist.

Until Phase 23 makes data per-user, everyone signed in shares one set of expenses, so access is limited to people the
provider has granted it.

> **How Part 1 was checked:** offline with a fake model, and through the real Vite proxy.
> - **The backend, recorded before and after** (D173): 17 HTTP scenarios, each with no `Origin`, the web app's
>   origin and a foreign one, plus every model call and the OpenAPI document. Every status and body is identical.
>   The only differences are the removed `Access-Control-*` and `Vary: Origin` headers, and preflights, which now
>   answer `405` (a browser treats that as a refusal) instead of `200` or `400`.
> - **Through the Vite proxy** (a backend with a fake model that writes one chunk a second, on spare ports): REST
>   calls, a Hindi problem, a multipart receipt upload, and `Location` headers on the web app's address
>   (`http://localhost:5181/api/v1/expenses/1`). The `/agent` stream's text arrived a second apart, as written, so the
>   proxy doesn't buffer Server-Sent Events. With the backend stopped, the proxy answered `502` with an empty body.
> - The generated contract is byte-identical; the migrations check, the architecture scans, `tsc -b`, `oxlint` and
>   `npm run build` are clean.

## Two ideas behind it

**A backend-for-frontend (BFF).** A browser is a poor place to keep tokens: any script that runs in the page (an
injected one included) can read what the page can read. So the browser never sees a token. The backend signs the user
in with the provider, keeps what it learns on the server, and gives the browser one cookie: a random key that
JavaScript can't read (HttpOnly), sent only to this site. It's the pattern Duende's BFF library implements for ASP.NET
Core: the browser holds a claim ticket, and the coat stays in the cloakroom.

**Standard OpenID Connect, so the provider can be replaced.** SpendWise speaks only the published standards
(discovery, the authorization code flow with PKCE, ID tokens, RP-initiated and back-channel logout). The provider is a
setting: its address, a client id and secret, and two small differences written as data (how to skip straight to
Google, and where roles are in the token). Moving to Keycloak, Entra ID, Auth0 or another provider that supports OIDC
means changing `.env`, not the code. SpendWise's own user ids are what the rest of the data points at, so a new
provider doesn't orphan anything.

## Part 1: one origin

```
before:  browser (http://localhost:5173) --CORS--> http://localhost:8000/api/v1/...

after:   browser --> http://localhost:5173/              Vite serves the web app
                 --> http://localhost:5173/api/v1/...    Vite's proxy --> http://127.0.0.1:8000/api/v1/...
         production: a reverse proxy serves web/dist and forwards /api/v1/ to uvicorn, the same way
```

**Why first.** The session cookie works best when the web app and the API share an origin: it can then be
`SameSite=Strict` with the `__Host-` prefix (sent only to this exact site, never on a request another site starts),
and the browser needs no CORS rules or "credentials" mode to send it. Doing it first, alone, means its own effects
can be checked before sign-in adds more.

**What changed.**
- The web app calls relative URLs. `api` (openapi-fetch) has no base URL, and the assistant's stream posts to
  `/api/v1/agent`. `shared/config/env.ts` and `VITE_API_URL` are gone: the browser code reads no settings.
- `vite.config.ts` proxies `API_PREFIX` (from the generated contract) to `API_PROXY_TARGET` (in `web/.env`, default
  `http://127.0.0.1:8000`). It has no `VITE_` prefix because only Node reads it. `npm run preview` uses the same proxy.
- The backend has no `CORSMiddleware` and no `CORS_ORIGINS` setting. `UnexpectedErrorMiddleware` stays: it still turns
  a bug into a 500 problem in the request's language.
- **The proxy keeps the browser's `Host`** (`changeOrigin: false`). The backend builds a new expense's or receipt's
  `Location` from it (`request.url_for`), so it points at the web app's address.
- **"Can't reach SpendWise" when the backend is down.** Before, `fetch` failed outright. Now the proxy answers: Vite
  sends `502` with an empty body, and production proxies send 502, 503 or 504. The backend's own errors, its 502s
  included, are always problem details, so `ApiError.fromProblem` reads a gateway status without one as unreachable
  (status 0, retried like before).

**Unchanged.** MCP clients, Swagger UI (`/docs`), `curl` and `mcp_stdio.py` still talk to the backend directly, at
`http://127.0.0.1:8000`.

**For production (Part 4's checklist).** The reverse proxy forwards `/api/v1/` with the original `Host`, and
`X-Forwarded-Proto`, so that uvicorn (with `--proxy-headers`) builds `https://` URLs.

## What was built (Part 1)

| Where | What |
|---|---|
| `web/vite.config.ts` | `apiProxy(target)`: `API_PREFIX` to `API_PROXY_TARGET` (default `http://127.0.0.1:8000`), `changeOrigin: false` |
| `web/src/shared/api/http.ts` | no base URL; `GATEWAY_FAILURES` (502, 503, 504) without a problem body become `unreachableError()` |
| `web/src/features/assistant/api/agent-stream.ts` | posts to the relative `AGENT_PATH` |
| `web/src/shared/config/env.ts` | removed (`API_ORIGIN`); `vite-env.d.ts` declares no variables of the app's own |
| `web/.env.example` | `API_PROXY_TARGET` instead of `VITE_API_URL` |
| `backend/app/main.py`, `infrastructure/config.py`, `.env.example` | no `CORSMiddleware`, no `CORS_ORIGINS` |
| `backend/app/web/problems.py` | `UnexpectedErrorMiddleware`'s comment: why it sits closest to the routes, now that CORS is gone |

## Run it

```powershell
.\run.ps1                 # backend on http://127.0.0.1:8000, as before
cd web; npm run dev       # http://localhost:5173; /api/v1 is forwarded to the backend
```

A `CORS_ORIGINS` line left in your `.env` is ignored (unknown settings are).

## Verify it by hand

1. Open http://localhost:5173: the Dashboard loads. In the browser's Network tab, every API call goes to
   `localhost:5173/api/v1/...`, and no response has an `Access-Control-Allow-Origin` header.
2. Add an expense, then ask the assistant something: its answer streams in as before.
3. Stop the backend and reload: the toast says "Can't reach SpendWise right now", and the `npm run dev` terminal
   shows `http proxy error: ... ECONNREFUSED`.

## Design questions

**1. CORS kept other websites from reading the API. With it gone, what does?**

<details><summary>Answer</summary>

The browser's same-origin policy, which is the default: a page may read answers only from its own origin unless the
server says otherwise, and CORS was how the server said otherwise. With no CORS headers at all, no other origin is
allowed. Requests that need a preflight (a JSON body, `PATCH`, `DELETE`) aren't even sent, because the preflight now
gets a 405. The list of trusted origins, which had to follow the web app's port, is gone too.
</details>

**2. Could another site still make my browser send a request to SpendWise?**

<details><summary>Answer</summary>

A "simple" one, yes: a plain form post needs no preflight, and that was just as true with CORS, which only ever
governed reading. JSON routes refuse it (a `text/plain` or form body is a 422), but a multipart upload to
`POST /receipts` is accepted. Part 2 closes it: every API call will need an `X-CSRF: 1` header, and another site can't
add a header without a preflight, which fails. Until then nothing is signed in, so such a request carries no one's
session.
</details>

**3. Why does the proxy keep the browser's `Host` instead of rewriting it to the backend's?**

<details><summary>Answer</summary>

The backend builds absolute URLs from the request's `Host`: a new expense's `Location` is
`request.url_for(...)`. With `changeOrigin: true` that would be `http://127.0.0.1:8000/api/v1/expenses/1`, an address
the web app doesn't call. Keeping the `Host` gives `http://localhost:5173/api/v1/expenses/1`, which is right. A
production proxy must be set up the same way (in nginx, `proxy_set_header Host $host`).
</details>

**4. Why does a 502 from the proxy say "can't reach", when the backend also sends 502s?**

<details><summary>Answer</summary>

The backend's 502 means a service it depends on (Gemini, a remote MCP server) failed, and it always comes as a
problem with a `detail` written for people, which is shown. The proxy's 502 has no problem body: it means the backend
itself didn't answer. So the body tells them apart, not the status.
</details>
