"""The currency agent: an A2A service, outside the monolith, that converts amounts between currencies (Phase 25).

Its own process on 127.0.0.1 (port CURRENCY_AGENT_PORT, 9003 by default), started with `python -m currency`
(run-agent.ps1 currency). One skill, convert_currency: a client sends an amount, two currencies and a day (as data,
or one line of text) and gets a conversion artifact. No model is involved. The rates come from a RateProvider:
MockRateProvider, fixed made-up rates, until a real API is plugged in (D203). The backend's expenses module asks it
for the rate of any expense not in INR, to store both amounts (D204).

- contract.py: what travels on the wire (the skill's id, the request, the answer, the text form);
- rates.py: the RateProvider interface and the mock behind it;
- executor.py: the A2A AgentExecutor; card.py: the Agent Card; settings.py: its configuration;
- server.py: the composition root (build_app, create_app); __main__.py: runs it.

The key check, the task store, the task helpers and the web app are the agent kit's (agents/agent_kit, D202).
"""
