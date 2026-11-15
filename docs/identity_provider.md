# Identity provider

How SpendWise signs people in, what it needs from an identity provider, how to set up today's provider (ZITADEL),
and how to switch to another. The design and its reasons: [phases/phase-22-sign-in.md](phases/phase-22-sign-in.md),
D185–D187 in [decisions.md](decisions.md).

## How SpendWise uses a provider

SpendWise is a **confidential web client** of any provider that implements **OpenID Connect** (D185). It uses only
the published standards: Discovery, the authorization code flow with PKCE (S256), the ID token's checks, UserInfo,
RP-Initiated Logout and Back-Channel Logout. The provider's name appears nowhere in the code; it's configuration.

| The provider does | SpendWise does |
|---|---|
| shows the login page, and the Google / GitHub (later Apple) buttons on it | starts the sign-in, checks the answer, keeps the session (one HttpOnly cookie, D186) |
| keeps the person's account, their linked social logins, MFA | keeps its own user (its own id), found by the provider's issuer and subject (D187) |
| decides who may sign in at all (grants) | can also require a role (`OIDC_REQUIRED_ROLE`), and can switch a user off (`app_user.is_active`) |
| branding of its pages | the web app's own sign-in page (Part 3), which sends people to the provider |

What the provider must offer:

- a discovery document at `<issuer>/.well-known/openid-configuration`;
- the authorization code flow with PKCE, for a client with a secret (`client_secret_basic` or `client_secret_post`);
- ID tokens signed with an asymmetric key (RS, PS, ES or EdDSA), carrying the nonce it was sent;
- a UserInfo endpoint, when the ID token doesn't carry the email and name;
- optionally an `end_session_endpoint` (sign-out there too) and back-channel logout.

## Registered at the provider

Exactly these addresses, all on `PUBLIC_URL` (the origin people open the web app at, D184):

| | Development | Production |
|---|---|---|
| Redirect URI | `http://localhost:5173/api/v1/auth/callback` | `https://<your host>/api/v1/auth/callback` |
| Post-logout redirect URI | `http://localhost:5173/sign-in` | `https://<your host>/sign-in` |
| Back-channel logout URI (optional) | not reachable by a cloud provider | `https://<your host>/api/v1/auth/backchannel-logout` |

## Settings

The full table is in [configuration.md](configuration.md#sign-in). In short, in `.env`:

```ini
OIDC_ISSUER=https://<your instance>
OIDC_CLIENT_ID=<the client id>
OIDC_CLIENT_SECRET=<the client secret>
SESSION_ENCRYPTION_KEYS=["<a Fernet key>"]
# Optional: one button per login option, the provider's role claim, a required role
OIDC_LOGIN_OPTIONS=[{"key":"google","label":"Google","extra_scopes":["..."]}]
OIDC_ROLE_CLAIM=...
OIDC_REQUIRED_ROLE=...
```

Make a key with `.\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
Until the issuer, client id, secret and a key are all set, nobody can sign in and every API route answers 401
(fail closed); the server log says which settings are missing when someone tries.

## ZITADEL (today's provider)

These steps follow ZITADEL's documentation ([sources.md](sources.md#27-openid-connect-and-zitadel-phase-22)). Part 4
walks through them in the console and corrects anything that differs.

1. **Instance.** Create a ZITADEL Cloud instance. Its address is the issuer: `OIDC_ISSUER=https://<instance>.zitadel.cloud`.
2. **Project and who may sign in.** Create a project, e.g. "SpendWise", and a role in it, e.g. `spendwise-user`.
   Assign the role to each person who may use SpendWise. Turn on the project's **"Check Role Assignment on
   Authentication"** (older consoles: "Check authorization on Authentication"): then only people with a role in the
   project can sign in at all. Turn on **"Assert Roles on Authentication"** too if SpendWise should check the role
   itself (`OIDC_REQUIRED_ROLE`): it sends the roles through UserInfo (and in tokens, by the application's settings).
3. **Application.** In the project, add a **Web** application with the authentication method that uses a client
   secret ("Code"). Add the redirect and post-logout URIs above. Turn on **development mode** for the
   `http://localhost` addresses (it allows plain http); never in production. Copy the client id and secret into `.env`.
4. **Social logins.** Add Google and GitHub as identity providers (each needs an OAuth app at Google or GitHub, with
   the callback address ZITADEL shows), and allow external login in the login settings. Whether a first login creates
   a ZITADEL user, and whether ZITADEL links accounts, is set there; SpendWise never merges people by email itself.
5. **Buttons (optional).** For a "Continue with Google" button that skips ZITADEL's page, give each option the
   provider-hint scope with that identity provider's id. If the identity provider belongs to one organization, add the
   organization's scope too:
   ```ini
   OIDC_LOGIN_OPTIONS=[{"key":"google","label":"Google","extra_scopes":["urn:zitadel:iam:org:idp:id:<google idp id>"]},{"key":"github","label":"GitHub","extra_scopes":["urn:zitadel:iam:org:idp:id:<github idp id>"]}]
   ```
6. **Roles (optional).** `OIDC_ROLE_CLAIM=urn:zitadel:iam:org:project:roles` (an object keyed by role name) and
   `OIDC_REQUIRED_ROLE=spendwise-user`. SpendWise reads the claim from the ID token, or from UserInfo when the ID token
   doesn't carry it.
7. **Branding.** Logo and colours of the login page are set in ZITADEL's branding settings.
8. **Back-channel logout (production).** Set the application's back-channel logout URI. ZITADEL then tells SpendWise
   when a session ends there, and SpendWise ends the matching sessions.

By ZITADEL's claims reference, the email and name are in the ID token only for `response_type=id_token`; for
SpendWise's code flow they come from UserInfo, which SpendWise asks whenever the ID token lacks them (or lacks the
role claim).

## Another provider

Only the settings change. Two things differ between providers and are written as data:

| | How to skip to one login option | Where roles are |
|---|---|---|
| ZITADEL | an extra scope: `urn:zitadel:iam:org:idp:id:<id>` | `urn:zitadel:iam:org:project:roles` |
| Keycloak | an extra parameter: `"extra_params": {"kc_idp_hint": "google"}` | wherever its role mapper puts them, e.g. `realm_access.roles` |

`OIDC_ROLE_CLAIM` takes a claim's exact name, or a dotted path. A provider that doesn't implement OpenID Connect at
all would need one new adapter for the `IdentityProvider` port (`core/identity.py`) and one line in `bootstrap.py`.

## Switching providers

1. Set up the new provider, with the people who use SpendWise (imported, or signing up there).
2. Register SpendWise there with the same addresses (above).
3. Change `OIDC_*` in `.env` and restart. Every session from the old provider stops working (a session remembers its
   issuer), so everyone signs in again.
4. A person's first sign-in at the new provider has a new issuer and subject. Unless it's linked to their existing
   SpendWise user, it becomes a new user. Two ways to link, to be built when a switch is planned (the tables already
   allow it: a user can have several identities):
   - **a mapping import:** a list of old subject → new subject, added as identities of the existing users;
   - **a time-limited email-match mode:** during the switch only, a first sign-in from the new issuer joins the user
     whose old identity has the same *verified* email. Outside that window SpendWise never matches people by email.

Until Phase 23 makes data per-user, everyone shares one set of expenses, so a new user id loses nothing. After Phase
23, link identities before switching.
