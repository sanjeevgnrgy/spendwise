"""The receipt agent: an A2A service, outside the monolith, that reads one receipt into a fixed shape (Phase 24).

Its own process on 127.0.0.1 (port RECEIPT_AGENT_PORT, 9001 by default), started with `python -m receipt`
(run-receipt-agent.ps1). One skill, extract_receipt: a client agent sends a receipt's bytes and the choices it may
pick from; the agent asks Gemini once and answers with a data artifact. It keeps nothing about a receipt once the
answer is sent, and never knows whose receipt it is: the client checks that.

- contract.py: what travels on the wire (the skill's id, the request's data, the answer's shape and limits);
- reader.py: the model call (prompt, schema, checks);
- executor.py: the A2A AgentExecutor, which turns a request into a task and its artifact;
- task_store.py: the task store, which forgets old tasks and never keeps a file's bytes;
- card.py: the Agent Card; http.py: the key check and no-store headers; settings.py: its configuration;
- server.py: the composition root (build_app, create_app); __main__.py: runs it.

It reuses the monolith's LLM port and Gemini adapter (backend/app/core, app/infrastructure/llm and logging), never
a module, web/ or the monolith's settings (D196).
"""
