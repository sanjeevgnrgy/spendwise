# References: official documentation

Where to read the official documentation for every library, protocol, standard and service SpendWise uses. The
libraries are the ones pinned in [requirements.txt](../requirements.txt) and [web/package.json](../web/package.json);
pinned versions matter, so check a page against the version in use.

This is a directory, not a record of facts. The specific facts the code relies on, with the page each came from, are
in [sources.md](sources.md). Links marked ✓ were read while building SpendWise (they appear in sources.md); the others
are each project's documentation home.

Keep it current: add a row when a dependency, protocol or service is added, and remove it when one goes.

## Backend (Python)

| Tool | Used for | Official docs |
|---|---|---|
| Python | the language | https://docs.python.org/3/ |
| FastAPI | REST routes, dependencies, OpenAPI | https://fastapi.tiangolo.com/ |
| Starlette | under FastAPI: middleware, uploads, responses | https://www.starlette.io/ |
| Uvicorn | the ASGI server | https://www.uvicorn.org/ |
| Pydantic | commands, queries, validation | https://docs.pydantic.dev/latest/ |
| pydantic-settings | settings from `.env` | https://docs.pydantic.dev/latest/concepts/pydantic_settings/ |
| SQLModel | table classes | https://sqlmodel.tiangolo.com/ |
| SQLAlchemy | sessions, statements, indexes | https://docs.sqlalchemy.org/ (✓ [SQLite dialect](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html)) |
| Alembic | database migrations | https://alembic.sqlalchemy.org/ ✓ |
| SQLite | the database | https://www.sqlite.org/docs.html |
| google-genai | the Gemini SDK | https://googleapis.github.io/python-genai/ |
| MCP Python SDK (`mcp`) | the MCP server and in-process client | https://github.com/modelcontextprotocol/python-sdk |
| ag-ui-protocol | AG-UI events, server side | https://docs.ag-ui.com/ ✓ |
| a2a-sdk | the A2A agents and client | https://github.com/a2aproject/a2a-python ✓ |
| Babel | CLDR formatting: dates, money, plurals | https://babel.pocoo.org/ |
| httpx | HTTP client (A2A transport) | https://www.python-httpx.org/ |
| httpx2 | HTTP client (the OpenID Connect adapter) | https://pypi.org/project/httpx2/ (package page) |
| python-multipart | multipart uploads (receipts) | https://pypi.org/project/python-multipart/ (package page) |
| PyJWT | checking ID and logout tokens | https://pyjwt.readthedocs.io/ |
| cryptography (Fernet) | sealing stored secrets | https://cryptography.io/en/latest/fernet/ |

## Web app

| Tool | Used for | Official docs |
|---|---|---|
| Next.js 16 | the App Router, rewrites, metadata | https://nextjs.org/docs (for this version, also the docs bundled in `web/node_modules/next/dist/docs/`: AGENTS.md section 3) |
| React | components | https://react.dev/ ✓ |
| TypeScript | the language | https://www.typescriptlang.org/docs/ |
| TanStack Query | server data, caching, refresh | https://tanstack.com/query/v5/docs/framework/react/overview ✓ |
| TanStack Table | the Expenses table | https://tanstack.com/table/latest/docs/introduction |
| openapi-typescript, openapi-fetch | the generated, typed API client | https://openapi-ts.dev/ ✓ |
| i18next | texts and translations | https://www.i18next.com/ |
| react-i18next | translations in components | https://react.i18next.com/ |
| shadcn/ui | the UI components in `shared/ui` | https://ui.shadcn.com/docs |
| Radix UI | the primitives under shadcn/ui | https://www.radix-ui.com/primitives/docs/overview/introduction |
| Tailwind CSS | styling | https://tailwindcss.com/docs |
| tw-animate-css | animations | https://github.com/Wombosvideo/tw-animate-css |
| class-variance-authority | component variants | https://cva.style/docs |
| cn | class name helper package (see sources.md, section 9) | https://www.npmjs.com/package/cn |
| lucide-react | icons | https://lucide.dev/guide/packages/lucide-react |
| sonner | toasts | https://sonner.emilkowal.ski/ |
| Recharts | charts | https://recharts.org/ |
| react-day-picker | the date picker | https://daypicker.dev/ |
| date-fns | date helpers | https://date-fns.org/docs/ |
| react-resizable-panels | the resizable chat panel | https://github.com/bvaughn/react-resizable-panels |
| zod | schemas | https://zod.dev/ |
| Geist (`@fontsource-variable/geist`) | the typeface | https://fontsource.org/fonts/geist |
| @ag-ui/core | AG-UI events, browser side | https://docs.ag-ui.com/ ✓ |
| oxlint | linting, including the import and accessibility rules | https://oxc.rs/docs/guide/usage/linter.html |

## Protocols and standards

| What | Used for | Official docs |
|---|---|---|
| MCP (Model Context Protocol) | the expense tools, for the assistant and other AI clients | https://modelcontextprotocol.io/ ✓ |
| A2A (Agent2Agent) | the receipt, insights and currency agents | https://a2a-protocol.org/latest/specification/ ✓ |
| A2UI | cards and forms drawn by the browser | https://a2ui.org/specification/v1.0-a2ui/ ✓ |
| AG-UI | streaming the assistant to the web app | https://docs.ag-ui.com/introduction ✓ |
| Agent Skills | the `skills/` folders | https://agentskills.io/specification ✓ |
| OpenID Connect | signing in | https://openid.net/specs/openid-connect-core-1_0.html ✓ |
| OAuth 2.0 and PKCE | the sign-in flow | https://www.rfc-editor.org/rfc/rfc6749 ✓, https://www.rfc-editor.org/rfc/rfc7636 ✓ |
| RFC 9457, problem details | every API error | https://www.rfc-editor.org/rfc/rfc9457 ✓ |
| Server-Sent Events | the assistant's stream | https://html.spec.whatwg.org/multipage/server-sent-events.html ✓ |
| OWASP CSV injection | the report's CSV download | https://community.owasp.org/attacks/CSV_Injection ✓ |

## Services

| Service | Used for | Official docs |
|---|---|---|
| Gemini API (Google AI Studio) | the language model | https://aistudio.google.com/docs/interactions-overview ✓; your rate limits: https://aistudio.google.com/rate-limit |
| ZITADEL | the identity provider in development (any OpenID Connect provider works) | https://zitadel.com/docs ✓ |
