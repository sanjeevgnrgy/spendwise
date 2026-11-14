"""Assistant module: an agent that reads and changes expenses through its tools, on the user's behalf.

Public interface: nothing for other modules. The composition root (bootstrap.py) uses module.py.

Inside, by layer:
- api.py, agui_request.py, agui.py: HTTP and AG-UI in and out (adapters);
- turns.py, parse.py: the use cases; decisions.py: Approve/Cancel on a delete card;
- agent.py: the agent loop, with prompts.py (its instruction), surfaces.py (text chat vs the web panel)
  and tool_runs.py (running one tool); approvals.py: the delete-card commands;
- tools.py: the expense-tools port and its MCP adapter;
- a2ui/: cards and forms (presentation); events.py, protocol.py, schemas.py: the shapes passed around;
- tables.py: the pending_approval table (private); module.py: what the composition root plugs in.

The guide to how these fit together is docs/assistant_architecture.md.
"""
