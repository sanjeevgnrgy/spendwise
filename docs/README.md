# SpendWise documentation

Learning notes and reference for SpendWise. The project's top-level [README](../README.md)
covers setup and running; this folder explains **why** things are the way they are.

## Contents

| File | What's in it |
|---|---|
| [architecture.md](architecture.md) | The modular monolith: layout, rules, how a request flows, how to add a module |
| [decisions.md](decisions.md) | Every design decision so far, with the reason and when to revisit it |
| [gemini.md](gemini.md) | Gemini setup, models and the free tier, privacy, errors, tokens |
| [troubleshooting.md](troubleshooting.md) | Problems already hit and how to fix them |
| [git.md](git.md) | Repo-specific git identity, committing safely, the GitHub remote |
| [concepts/python-tooling.md](concepts/python-tooling.md) | Virtual environments, `.env`, `__pycache__`, `python -m`, pinned dependencies |
| [phases/phase-1-project-setup.md](phases/phase-1-project-setup.md) | Routes, path parameters, `/docs` |
| [phases/phase-2-first-gemini-call.md](phases/phase-2-first-gemini-call.md) | Models, prompts, tokens, keeping the API key in `.env` |
| [phases/phase-3-modular-structure.md](phases/phase-3-modular-structure.md) | Modular monolith, module-owned tables, money in paise |
| [phases/phase-4-expenses-api.md](phases/phase-4-expenses-api.md) | Router → service → repository, CRUD, input vs output models, 201 / 404 / 422 |
| [phases/phase-5-tests.md](phases/phase-5-tests.md) | Fixtures, tests on a throwaway database, the architecture test, reading a failing test (the tests themselves were removed later, see D64) |
| [phases/phase-6-structured-output.md](phases/phase-6-structured-output.md) | Structured output, required-but-nullable fields, what happens with no amount |
| [phases/phase-7-function-calling-chat.md](phases/phase-7-function-calling-chat.md) | Function calling, the agent loop step by step, why steps are capped, watching it think |
| [phases/phase-8-memory.md](phases/phase-8-memory.md) | Why the model forgets, chat threads, sending the last N turns, the cost of long history |
| [phases/phase-9-mcp-module.md](phases/phase-9-mcp-module.md) | MCP: host, client and server, tools vs resources, the MCP module as an adapter, Inspector and Claude Desktop |
| [phases/phase-10-agent-uses-mcp.md](phases/phase-10-agent-uses-mcp.md) | The agent as an MCP client: discovering tools, schema conversion, error handling, what decoupling buys (not run yet) |
| [phases/phase-11-frontend.md](phases/phase-11-frontend.md) | React components, props, useState/useEffect, shadcn/ui vs a component library, CORS, the Expenses page |
| [phases/phase-12-dashboard.md](phases/phase-12-dashboard.md) | Why the backend aggregates, the trend endpoint, shadcn charts, loading / empty / error states |

Each phase file has the concepts, what was built, how to run and test it, and the
"check your understanding" questions. Answers are hidden; click to reveal them.

## Keeping these docs current

- Each new phase adds `phases/phase-N-<name>.md` in the same commit as its code.
- A new design decision gets an entry in [decisions.md](decisions.md): what, why, and when to revisit it.
- A problem that took real effort to solve gets an entry in [troubleshooting.md](troubleshooting.md).
- If a doc and the code disagree, the code is right and the doc is a bug. Fix the doc.
