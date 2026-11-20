# Refactor: one server

**Goal:** everything the backend does, the three A2A agents included, runs as one server on one port, so SpendWise
deploys and runs as `run.ps1` plus the web app. The version where each agent is its own service is kept on the
`multi-server` branch. Decision: D207.

**The owner's choices:** `main` is the single-server version and the current code goes on a `multi-server` branch
(rather than one branch with a setting, which I'd recommended); the web app stays its own Next.js server.

## The idea

An A2A agent is a contract (a card, a skill, tasks, artifacts), not a port. The backend already spoke to its agents
through one port of its own (`core/agents.RemoteAgents`) and one adapter (`A2AAgents`), and the offline checks had
been reaching the agents' apps in memory all along, through httpx's ASGI transport. So hosting them is a change of
wiring, not of design: the composition root builds the three agents' apps inside the backend's process and hands the
adapter in-memory transports instead of network addresses. Nothing in the modules, the agents or the orchestrator
changes. It's like a firm moving its specialists from separate offices into one building: they keep their own desks,
job descriptions and paperwork, and you still send them the same forms; there's just no taxi between offices.

## What changed

| Where | What |
|---|---|
| `backend/app/agents_host.py` (new) | builds the three agents with the backend's model and clock, a random key each, and the in-memory client |
| `backend/app/bootstrap.py` | the model is built first; the agents are `agents_host.hosted_agents(llm, clock)` unless a check passes its own |
| `backend/app/infrastructure/a2a/loop.py` (new) | `BackgroundLoop`: every A2A call runs on one long-lived event loop |
| `backend/app/infrastructure/config.py` | the agents' URL and key settings are gone from the backend |
| `backend/app/main.py` | the agents' loggers are shown with the backend's |
| `.env.example`, `run-agent.ps1`, docs | the agents need no settings; running one alone is optional |

## How it was checked

10 checks of the single-server app as `bootstrap.build()` makes it, with nothing on 9001-9003; every earlier suite;
an ordinary turn unchanged; the real server booted as `run.ps1` starts it, on a copy of the database. Details in D207.

## Try it

```powershell
.\run.ps1                 # the backend, with the receipt, insights and currency agents inside it
cd web; npm run dev       # the web app
```

No agent keys and no extra terminals. Attach a receipt, ask "where did my money go this month?", or add an expense in
dollars: the chips still show each agent's A2A task id.
