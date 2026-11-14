"""Web: the FastAPI plumbing that every REST route shares (the HTTP adapter's common parts).

- dependencies.py: BusDep, ClockDep and IdPath, which give routes the bus, the clock and a checked path id;
- problems.py: RFC 9457 problem-details responses, the error handlers and the unexpected-error middleware.

It may import core/, never a module or infrastructure/. main.py installs the error handling; each module's routes
(api.py, the assistant's api/routes.py) use the dependencies, and the MCP endpoint (mcp/http.py) answers its 401
with problem_response. Business code (handlers, use cases) never imports it: it raises core/errors.py's errors.
"""
