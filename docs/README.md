# SpendWise documentation

Reference, guides and the engineering record for SpendWise. The project's top-level [README](../README.md) is the short
version: what SpendWise is, a quick start, and where to go next. This folder explains **how** it works and **why**
it's built that way.

## Where to start

| You want to… | Read |
|---|---|
| understand what SpendWise is and does | [overview.md](overview.md) |
| get it running on your machine | [getting_started.md](getting_started.md) |
| change the backend | [architecture.md](architecture.md), then [backend_onboarding.md](backend_onboarding.md) |
| change the web app | [architecture.md](architecture.md), then [frontend_onboarding.md](frontend_onboarding.md) |
| work on the code with an AI agent | [AGENTS.md](../AGENTS.md): the rules every change follows, and the definition of done |
| work on the AI assistant | [assistant_architecture.md](assistant_architecture.md) |
| see how a feature was designed and built | the [phase notes](#phase-notes) below |

## Overview and architecture

| File | What's in it |
|---|---|
| [overview.md](overview.md) | What SpendWise does, its features, the tech stack, the roadmap |
| [architecture.md](architecture.md) | The modular monolith with CQRS, vertical slices inside each module, the module rules, how a request flows, feature slices, the shared contract |
| [assistant_architecture.md](assistant_architecture.md) | The agent loop, tools over MCP, AG-UI streaming, A2UI cards and forms, approvals, memory, cost |
| [how_spendwise_works.md](how_spendwise_works.md) | The main flows as diagrams: adding an expense, the Dashboard, asking, deleting with approval, staying in sync |
| [architecture-review.md](architecture-review.md) | Every finding of the architecture review and the two code reviews, and how each was resolved |
| [decisions.md](decisions.md) | Every design decision (D1–D194), with why, and when to revisit it |

## Developer guides

| File | What's in it |
|---|---|
| [getting_started.md](getting_started.md) | Setup from zero: Python, Node, `.env`, migrations, sample data, the web app, MCP clients |
| [backend_onboarding.md](backend_onboarding.md) | Working in the backend: recipes for a query, a command, a table, a module, an MCP tool; review checklist |
| [frontend_onboarding.md](frontend_onboarding.md) | Working in the web app: feature slices, TanStack Query, the generated client, the A2UI renderer; recipes |
| [troubleshooting.md](troubleshooting.md) | Problems already hit and how to fix them |
| [git.md](git.md) | Repo-specific git identity, committing safely, the GitHub remote |
| [concepts/python-tooling.md](concepts/python-tooling.md) | Virtual environments, `.env`, `__pycache__`, `python -m`, pinned dependencies |

## Reference

| File | What's in it |
|---|---|
| [api_endpoints.md](api_endpoints.md) | Every REST route, the AG-UI stream, the MCP tools and resources, the error format, with examples |
| [database_schema.md](database_schema.md) | Tables, columns, indexes, which module owns what, the migrations |
| [configuration.md](configuration.md) | Every setting (backend `.env`, web `.env`), defaults, and the generated contract |
| [security.md](security.md) | What protects what (one origin, sign-in and sessions, the MCP token, approvals, prompt injection, the renderer), and the known gaps |
| [identity_provider.md](identity_provider.md) | Signing in: what SpendWise needs from an OpenID Connect provider, setting up ZITADEL, the values for other providers, and switching providers |
| [gemini.md](gemini.md) | Gemini setup, models and the free tier, privacy, errors, tokens |
| [sources.md](sources.md) | What the official docs, specs and library code say, with links, for the facts Phase 14 onwards relies on |
| [images/](images/) | Screenshots used by the READMEs (`hero.png`: the Dashboard with sample data) |

## Phase notes

The engineering record of each delivery phase: the design and its reasoning, what was built, how to run and verify
it, and design questions with their answers (collapsed). Later changes are noted in the phase they affect.

| File | What's in it |
|---|---|
| [phases/phase-1-project-setup.md](phases/phase-1-project-setup.md) | Routes, path parameters, `/docs` |
| [phases/phase-2-first-gemini-call.md](phases/phase-2-first-gemini-call.md) | Models, prompts, tokens, keeping the API key in `.env` |
| [phases/phase-3-modular-structure.md](phases/phase-3-modular-structure.md) | Modular monolith, module-owned tables, money in paise |
| [phases/phase-4-expenses-api.md](phases/phase-4-expenses-api.md) | Router → service → repository, CRUD, input vs output models, 201 / 404 / 422 |
| [phases/phase-5-tests.md](phases/phase-5-tests.md) | Fixtures, tests on a throwaway database, the architecture test, reading a failing test (the tests themselves were removed later, see D64) |
| [phases/phase-6-structured-output.md](phases/phase-6-structured-output.md) | Structured output, required-but-nullable fields, what happens with no amount |
| [phases/phase-7-function-calling-chat.md](phases/phase-7-function-calling-chat.md) | Function calling, the agent loop step by step, why steps are capped, watching it think |
| [phases/phase-8-memory.md](phases/phase-8-memory.md) | Why the model forgets, chat threads, sending the last N turns, the cost of long history |
| [phases/phase-9-mcp-module.md](phases/phase-9-mcp-module.md) | MCP: host, client and server, tools vs resources, the MCP module as an adapter, Inspector and Claude Desktop |
| [phases/phase-10-agent-uses-mcp.md](phases/phase-10-agent-uses-mcp.md) | The agent as an MCP client: discovering tools, schema conversion, error handling, what decoupling buys |
| [phases/phase-11-frontend.md](phases/phase-11-frontend.md) | React components, props, useState/useEffect, shadcn/ui vs a component library, CORS, the Expenses page |
| [phases/phase-12-dashboard.md](phases/phase-12-dashboard.md) | Why the backend aggregates, the trend endpoint, shadcn charts, loading / empty / error states |
| [phases/phase-13-chat-panel.md](phases/phase-13-chat-panel.md) | The chat panel, keeping panel and pages in sync with a shared context, resizable panel vs Sheet |
| [phases/phase-14-agui-streaming.md](phases/phase-14-agui-streaming.md) | SSE vs normal HTTP, the AG-UI events, streaming Gemini with tools in the loop, reading a stream in the browser |
| [phases/phase-15-tool-progress.md](phases/phase-15-tool-progress.md) | Why tool activity builds trust, AG-UI tool events, shared state and `dataVersion`, MCP tool annotations, status chips |
| [phases/phase-16-a2ui-card.md](phases/phase-16-a2ui-card.md) | Why agents send UI as data not HTML, A2UI v1.0 messages and catalog, a card for each tool result, a safe renderer |
| [phases/phase-17-a2ui-forms.md](phases/phase-17-a2ui-forms.md) | Data binding, why model-written UI is validated, a form instead of questions, Save as an A2UI action |
| [phases/phase-18-insight-cards.md](phases/phase-18-insight-cards.md) | Human in the loop and which actions deserve it, Approve/Cancel enforced by the server, a custom catalog for Chart and Stat |
| [phases/phase-19-languages.md](phases/phase-19-languages.md) | Translating a web app: namespaces and keys, plurals and placeholders, loading a language on demand, numbers and dates per locale, English and Hindi |
| [phases/phase-20-languages-server.md](phases/phase-20-languages-server.md) | The server's side of translation: Accept-Language, typed catalogs checked at startup, errors written where the response is built, CLDR money and dates, telling the model which language to reply in |
| [phases/phase-21-receipts.md](phases/phase-21-receipts.md) | Receipt scanning: the receipts module (uploads checked by their bytes, files kept apart from the database, Gemini reading an image or a PDF into a schema, the receipt's text treated as data), and a receipt attached in the chat offered as the expense form to confirm |
| [phases/phase-22-sign-in.md](phases/phase-22-sign-in.md) | Signing in (in progress): the backend-for-frontend pattern (the session on the server, one HttpOnly cookie in the browser), standard OpenID Connect so the identity provider can be replaced; Part 1, one origin with no CORS; Part 2, the backend: the sign-in port and OIDC adapter, the accounts module, server-side sessions, the X-CSRF header; Part 3, the web app: the sign-in page, the session check in front of the signed-in pages, the user menu |
| [phases/phase-23-per-person-data.md](phases/phase-23-per-person-data.md) | Each person's own data: an owner on every row, checked in the same statement that reads it (protection against BOLA), the assistant's tools bound to the signed-in person, MCP acting for a person through personal access tokens, the account routes (sessions, tokens), migration 0007; pages that never outlive their person, the Settings page; security headers; rate limits on the model-backed routes |
| [phases/phase-24-receipt-agent.md](phases/phase-24-receipt-agent.md) | The receipt agent: client and remote agents, the Agent Card, task states, A2A compared with MCP and why the agent lives outside the monolith; Part 1, the A2A server (one skill, a data artifact, a key check, a task store that keeps no files); Part 2, the assistant as its client (a port and an A2A adapter, the card and the answer checked, the task id in the chip), the receipts module down to uploads |
| [phases/phase-25-more-agents.md](phases/phase-25-more-agents.md) | More A2A agents: one port for remote agents and the shared agent kit; Part 1, the currency agent (no model, a rate provider behind an interface) and every expense stored in INR too, converted on the server at every save; Part 2, the insights agent (numbers by code, tips by the model) and input-required: asking which month, and resuming the same task; Part 3, the assistant as orchestrator: the agents' cards read at startup, a delegate_to_agent tool, how the model chooses, the person's answer resuming the agent's task |
| [phases/phase-26-agent-skills.md](phases/phase-26-agent-skills.md) | Agent Skills: progressive disclosure, SKILL.md folders, the catalog in the prompt and a load_skill tool; Part 1, the categorization skill; Part 2, the monthly report: a script the server runs, the reports module, a card with CSV and markdown downloads (A2UI client functions) |
| [phases/refactor-single-server.md](phases/refactor-single-server.md) | One server: the backend hosts the three A2A agents in its own process, reached in memory, still over A2A; the multi-server version kept on its own branch |
| [phases/refactor-nextjs.md](phases/refactor-nextjs.md) | The move to Next.js for search engines: App Router routes with server-rendered metadata, robots.txt and a sitemap, the signed-in app behind one client boundary, the API rewrite and its proxy settings, a real 404 |
| [phases/refactor-solid.md](phases/refactor-solid.md) | SOLID in practice (surfaces instead of flags, tool and component registries, narrow ports), testability seams and how behaviour was recorded, scalability work and limits |
| [phases/refactor-architecture.md](phases/refactor-architecture.md) | CQRS and the unit of work, ports and adapters, feature slices, migrations, the generated contract; then the code-review fixes (versions, transactional SQLite) |

## Keeping these docs current

- Update the docs **in the same commit** as the code they describe.
- Each new phase adds `phases/phase-N-<name>.md`. If it changes how an earlier phase works, add a "Later changes" note
  to that phase's file rather than rewriting it.
- A new design decision gets an entry in [decisions.md](decisions.md): what, why, and when to revisit it. The log is
  append-only: an old entry gets a "Superseded by" or "Updated by" line, never an edit.
- A change to a route, table, setting or security measure updates [api_endpoints.md](api_endpoints.md),
  [database_schema.md](database_schema.md), [configuration.md](configuration.md) or [security.md](security.md).
- A new module, port or rule updates [architecture.md](architecture.md) (its interface table too).
- A problem that took real effort to solve gets an entry in [troubleshooting.md](troubleshooting.md).
- A fact taken from official docs, a spec or a library's code goes in [sources.md](sources.md), with its link or file.
- If a doc and the code disagree, the code is right and the doc is a bug. Fix the doc.
- A new rule for how the code is built goes in [AGENTS.md](../AGENTS.md) too, so AI agents follow it.
