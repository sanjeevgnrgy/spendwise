"""Assistant module: an agent that reads and changes expenses through its tools, on the user's behalf.

Public interface: nothing for other modules. The composition root (bootstrap.py) uses module.py.

Inside, one folder per role:
- api/: HTTP and AG-UI in and out (adapters): routes.py, schemas.py (request and response bodies),
  agui_request.py (AG-UI in), agui_stream.py (AG-UI out), protocol.py (names on the wire);
- application/: the use cases: assistant.py (Assistant: run_turn, read_receipt, decide, chat), decisions.py
  (Approve/Cancel on a delete card), receipt_turn.py (an attached receipt), expense_parser.py (POST /parse);
- agent/: the agent loop (agent.py), with prompts.py (its instruction), surfaces.py (text chat vs the web
  panel), tool_runs.py (running one tool) and events.py (what a turn yields);
- approvals/: the delete cards waiting for Approve or Cancel, as vertical slices (commands/: one file per
  command, holding the message and its handler), with their shapes (models.py) and table (persistence/);
- tools/: the expense-tools port (port.py) and its MCP adapter (mcp_adapter.py);
- receipt_agent/: the receipt-reading port (port.py) and its A2A adapter (a2a_client.py): the assistant as the
  receipt agent's client (Phase 24);
- a2ui/: cards and forms (presentation); module.py: what the composition root plugs in.

The guide to how these fit together is docs/assistant_architecture.md.
"""
