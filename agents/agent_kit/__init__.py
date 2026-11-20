"""The agent kit: what every SpendWise A2A agent shares, so each agent is only its own contract and work (D202).

- http.py: AgentGate, the key check, the request size limit and no-store answers;
- task_store.py: ForgetfulTaskStore, a few recent tasks kept, never a file's bytes (D198);
- settings.py: the .env the agents read, the host (127.0.0.1 only), the key rule, an agent's URL;
- server.py: build_agent_app (the SDK's handler, the card and JSON-RPC routes behind the gate) and serve.

Used by agents/receipt and agents/currency. Like them, it imports only the backend's core and, for logging,
app.infrastructure.logging (D196).
"""
