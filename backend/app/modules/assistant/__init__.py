"""Assistant module: an agent that reads and changes expenses through its tools, on the user's behalf.

Public interface: nothing for other modules. The composition root uses module.py.

Inside, by layer:
- api.py, agui.py: HTTP and AG-UI in and out (adapters);
- turns.py, parse.py: the use cases; agent.py: the agent loop; approvals.py: commands;
- tools.py: the expense-tools port and its MCP adapter;
- a2ui/: cards and forms (presentation); events.py, protocol.py, schemas.py: the shapes passed around.
"""
