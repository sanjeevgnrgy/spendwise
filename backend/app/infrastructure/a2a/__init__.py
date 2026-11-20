"""The adapter for the remote-agents port (core/agents.py): A2A, the backend as a client agent (agents.py, D201),
its calls run on one background loop (loop.py, D207).

Infrastructure. The composition root (bootstrap.py) builds A2AAgents with one AgentEndpoint per agent and injects it;
nothing else imports this package.
"""

from app.infrastructure.a2a.agents import A2AAgents, AgentEndpoint

__all__ = ["A2AAgents", "AgentEndpoint"]
