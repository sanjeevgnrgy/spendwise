"""The MCP tools, one file per tool, each with the register_<tool>(server, bus, views) function that adds it.

Part of the mcp adapter. server.py lists the registrars in TOOL_REGISTRARS, in the order clients list the
tools; support.py holds what they share (argument types, annotations, the error rules, the contract check).
A tool only translates: it turns its arguments into a command or query for the expenses module, sends it
through the bus, and answers with a typed result (contracts.py). Nothing is exported here: server.py imports
each file by its full path.
"""
