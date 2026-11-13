"""MCP module: exposes SpendWise's expense tools and resources over the Model Context Protocol.

It owns no tables and no business rules. Like a REST router, it is only an adapter: it turns
MCP requests into calls to the expenses and categories modules' public interfaces.

Public interface: nothing for other modules. main.py mounts `server` (see server.py) at /mcp,
and backend/mcp_stdio.py runs the same server over stdio.
"""
