# Phase 22: Signing in

**Goal:** only people you allow can use SpendWise. They sign in through an **identity provider** (ZITADEL to begin
with, offering Google and GitHub) on its own hosted login page, and the backend keeps the session. Built in four parts,
by the owner's choice:

- **Part 1 (done):** one origin. The web app reaches the API on its own address, through a proxy, and CORS is
  removed. Decision: D184.
- **Part 2 (done):** the backend. A provider-neutral sign-in port and a standard OpenID Connect adapter, the
  `accounts` module (users, their identities, server-side sessions, login attempts), the sign-in routes, every other
  route locked, and the `X-CSRF` header. Decisions: D185, D186, D187. See [Part 2: the backend](#part-2-the-backend).
- **Part 3:** the web app. The sign-in page, a gate around the pages, the user menu, sign-out.
- **Part 4:** a real provider. A live sign-in with ZITADEL, Google and GitHub (following
  [identity_provider.md](../identity_provider.md), and correcting it where the console differs), back-channel logout,
  and a production checklist.

Between Part 2 and Part 3 the API needs a session but the web app has no sign-in page yet: sign in by opening
`/api/v1/auth/login` (see [Verify it by hand (Part 2)](#verify-it-by-hand-part-2)).

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

> **How Part 2 was checked:** offline, with fakes at the ports; no call to a real provider.
> - **The adapter against a fake provider** (42 checks; `httpx2.MockTransport` with discovery, keys, token and
>   UserInfo endpoints, RSA keys made on the spot): the authorization request (PKCE S256, a login option's scope and
>   parameter, an unknown option adding nothing, a reserved parameter refused at startup); a sign-in with the profile
>   and roles read from UserInfo, and UserInfo not asked when the ID token has all it needs; every way a token can be
>   wrong (another key, issuer, audience, `azp`, several audiences without `azp`, expired, issued in the future, wrong
>   or missing nonce, `alg: none`, HS256, no `exp`), 30 s past `exp` accepted; key rotation (an unknown key id
>   fetches the keys again, at most once a minute); Basic credentials form-encoded, `client_secret_post` when it's all
>   the provider offers; the provider refusing the code, answering for another issuer, unreachable; sign-out URLs;
>   logout tokens.
> - **The routes, with a fake provider and a movable clock** (71 checks): no header 403, no session 401 (in Hindi
>   too), every module route locked, `/health` open; the cookies' flags (HttpOnly, Secure, `__Host-`, Strict and
>   Lax, their lifetimes); a full sign-in back to its page; only the key's hash and the sealed ID token stored; the
>   same subject is the same user, another subject with the same email another user; each failure code (wrong state,
>   replayed, no login cookie, a token failing a check, the provider failing, cancelled, no code, after 10 minutes);
>   eight `return_to` attacks; session rotation; renewal, the idle and the absolute expiry; sign-out (wrong or no
>   `sid` 403, the provider's page with the ID token, the old key no longer accepted); back-channel logout by session
>   and by user, and an invalid token; a required role; a switched-off user; a provider switch; sign-in not
>   configured; `COOKIE_SECURE=false`; at most 500 login attempts kept.
> - **Nothing else changed:** signed in and sending `X-CSRF`, the 52 recorded scenarios of Part 1 are byte-identical
>   (REST, problems in both languages, uploads, the `/agent` stream and every model call), and the OpenAPI document
>   only gained the six sign-in routes and their three schemas.
> - **Browsers:** a probe on `http://localhost` showed the installed Edge 157 and Chrome keep `__Host-` Secure cookies
>   there, so the defaults work in development.
> - Migration 0006 upgrades, downgrades and upgrades again on a copy; `alembic check` is clean; the eight architecture
>   scans are clean (the new one: no provider's name in the code); the contract was regenerated; `tsc -b`, `oxlint`
>   and `npm run build` pass.
> - **Still to confirm live (Part 4):** ZITADEL's console labels, that its "Code" web application accepts PKCE along
>   with the client secret, and the hint scope sending people straight to Google or GitHub.
>
> **The two new Hindi texts were written by an AI** and need a native speaker's review.

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

## Part 2: the backend

### Design: signing in

```
browser                         SpendWise (web/auth.py, accounts/)                    provider (OIDC)
  |-- GET /auth/login ----------> end the old session; state, nonce, PKCE verifier;
  |                               StartLogin (stored, used once)
  |<- 302 + login cookie (Lax) ---|
  |------------------------------------------------------------- sign in (Google...) -->|
  |<---------------------------------------------- 302 /auth/callback?code&state -------|
  |-- GET /auth/callback --------> TakeLoginAttempt (login cookie) -> state matches ->
  |                               code + verifier -> tokens -------------------------->|
  |                               check the ID token (keys, iss, aud, azp, exp, nonce);
  |                               UserInfo if the profile or roles are missing; role rule;
  |                               SignIn: user by (issuer, subject), new session, ID token sealed
  |<- 302 return_to + session cookie (HttpOnly, Secure, Strict, __Host-)
  |-- GET /api/v1/... + X-CSRF --> require_csrf -> require_user (GetSession by the key's hash) -> the route
```

- **The provider is a port.** `IdentityProvider` (`core/identity.py`); one adapter, `OidcIdentityProvider`, standard
  OpenID Connect only, configured by `OIDC_*` (D185). What differs between providers is data: the login options'
  extra scopes or parameters, and where roles are. While a setting is missing, `UnconfiguredIdentityProvider` refuses
  every sign-in, so the API stays locked rather than open.
- **The session is on the server** (D186). The cookie is a random key; the database keeps its hash. The ID token is
  kept sealed for sign-out; access and refresh tokens aren't kept at all. A session ends after a day unused or 14 days
  in all, and is renewed at most every 12 hours while used.
- **Every module's route needs `X-CSRF: 1` and a session.** `main.py` adds `require_csrf` and `require_user` when it
  mounts each module's router; the modules themselves didn't change. The web app's `apiHeaders()` sends the header.
- **People are their identity** (D187): issuer and subject, unique together; SpendWise's own user id is what other
  data will point at. Never matched by email.
- **Slow work outside transactions** (D164): the attempt is stored before the browser leaves, taken when it comes
  back, and the session written only after the provider has answered.

### What was built (Part 2)

| Where | What |
|---|---|
| `core/identity.py`, `core/sealing.py` | the `IdentityProvider` and `Sealer` ports; `VerifiedLogin`, `LogoutNotice`, `Principal`, `IdentityError`, `InvalidTokenError` |
| `core/errors.py` | `AuthenticationError` (401) and `ForbiddenError` (403) |
| `infrastructure/identity/` | `oidc.py` (the adapter), `documents.py` (discovery and keys), `exchange.py` (token and UserInfo endpoints), `tokens.py` (token checks), `options.py` (`OIDC_LOGIN_OPTIONS`), `unconfigured.py` |
| `infrastructure/sealing.py` | `FernetSealer` (`SESSION_ENCRYPTION_KEYS`, rotatable) |
| `infrastructure/config.py`, `.env.example` | the `OIDC_*` settings, `PUBLIC_URL`, `SESSION_ENCRYPTION_KEYS`, `COOKIE_SECURE` |
| `modules/accounts/` | values, models, four tables; commands `StartLogin`, `TakeLoginAttempt`, `SignIn`, `RenewSession`, `EndSession`, `RevokeSessions`; queries `GetSession`, `GetCurrentUser`, `GetSignOut`; `domain/` (keys, return paths, profile rules); `application/` (`SignInFlow`, `SignOutFlow`, `SessionGate`); `api.py` (six routes) |
| `web/auth.py`, `web/i18n/` | the cookies, `require_csrf`, `require_user`, `CurrentUserDep`; two texts (401, 403) in English and Hindi |
| `bootstrap.py`, `main.py` | `build(identity=, sealer=)`, the session check on `app.state`, `auth_routers()`, the checks in front of every module's router |
| `migrations/versions/0006_accounts.py` | the four tables |
| `scripts/export_contracts.py` | `AUTH` in the web contract: the header, the sign-in page, the parameters, the failure codes |
| `web/src/shared/api/http.ts`, `features/assistant/api/agent-stream.ts` | `apiHeaders()`: every call sends `X-CSRF` |
| `requirements.txt` | `pyjwt==2.15.1`, `cryptography==50.0.2` (already installed; now pinned) |

### Run it

```powershell
.\run.ps1                 # applies migration 0006 on start
cd web; npm run dev
```

With no `OIDC_*` settings the server log says "Sign-in isn't configured, so nobody can sign in", and every API route
answers 401: set up a provider first ([identity_provider.md](../identity_provider.md)).

### Verify it by hand (Part 2)

1. `http://localhost:5173/health` and `http://127.0.0.1:8000/health` answer `{"status":"ok"}` without signing in.
2. In the browser's developer tools, any API call the web app makes answers 401 `unauthorized` ("Sign in to
   continue."): the web app's sign-in page comes in Part 3.
3. Open `http://localhost:5173/api/v1/auth/login`: the provider's login page. After signing in you're back on the
   Dashboard, which now loads. The cookie `__Host-spendwise-session` is HttpOnly (not visible to `document.cookie`).
4. `http://localhost:5173/api/v1/auth/user` typed in the address bar answers 403: it has no `X-CSRF` header. The
   web app's own call to it (Network tab) answers your name and a `logout_url`.
5. Open the `logout_url`: you go to the provider's sign-out page, then to `/sign-in` (a "Page not found" until Part
   3), and the Dashboard's calls answer 401 again.

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

**5. Why keep the session on the server instead of in a signed cookie, or the tokens in the browser?**

<details><summary>Answer</summary>

Anything the browser holds, a script in the page can use, and an injected one could send it elsewhere. Here the
browser holds only a random key it can't even read (HttpOnly); everything it stands for stays on the server, so a
session can be ended at once (sign-out, a switched-off account, the provider's back-channel logout) rather than
lasting until a token expires. The cost is one indexed query per request, which this app can afford.
</details>

**6. Why does every API call carry `X-CSRF: 1`, when the session cookie is already SameSite=Strict?**

<details><summary>Answer</summary>

Defence in depth. Strict keeps the cookie off requests another site starts, but it relies on the browser and on the
site boundary (another app on the same site counts as "same site"). The header needs no secret: a page on another
origin can't add a custom header without a preflight, which the API refuses because it sends no CORS headers. So even
a browser that sent the cookie would send a request the API turns away.
</details>

**7. Why not find a returning person by their email, so a Google sign-in and a GitHub sign-in are the same person?**

<details><summary>Answer</summary>

Because an email proves only that someone controls that address at some provider, and providers differ in how
carefully they check it. Matching on it would let anyone who can get an account with your address anywhere into
yours. A person is their identity at the provider (issuer and subject); joining several logins into one person is the
provider's job (ZITADEL links them to one user there, so SpendWise sees one subject).
</details>
