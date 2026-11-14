"""The assistant's expense tools: the port the agent depends on, and the adapter behind it.

Port and adapter: port.py holds ExpenseTools (what the agent needs), ToolOutput and ToolsUnavailableError;
mcp_adapter.py holds McpExpenseTools, the port over MCP (this app's server in-process, or a remote one).
module.py exports both to the composition root. Nothing is exported here: each file is imported by its full path.
"""
