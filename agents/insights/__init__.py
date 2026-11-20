"""The insights agent: an A2A service, outside the monolith, that analyses a month of spending (Phase 25, part 2).

Its own process on 127.0.0.1 (port INSIGHTS_AGENT_PORT, 9002 by default), started with `python -m insights`
(run-agent.ps1 insights). One skill, analyze_spending: a client sends a person's expenses (in INR, without notes or
anything about the person) and perhaps a month and their question; the agent answers with an insights artifact:
totals, trends, unusual spends and a month-end forecast, worked out by code, and 3 saving tips, written by Gemini in
one call. Without a month, over several months, the task stops input-required asking which, and the client resumes
it with the person's reply (D205).

- contract.py: what travels on the wire (the request, a resumption, the answer);
- analysis.py: the numbers; months.py: which month (the expenses' months, a reply's month);
- tips.py: the model call; executor.py: the A2A AgentExecutor, its states and the question;
- card.py: the Agent Card; settings.py: its configuration;
- server.py: the composition root (build_app, create_app); __main__.py: runs it.

The key check, the task store, the task helpers and the web app are the agent kit's (agents/agent_kit, D202).
"""
