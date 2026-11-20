"""Runs the insights agent: `python -m insights`, with backend/ and agents/ on PYTHONPATH (run-agent.ps1 insights).

The entry point. Reads the settings (it stops here, naming the setting, if INSIGHTS_AGENT_KEY is missing or short),
then serves the app on 127.0.0.1 at INSIGHTS_AGENT_PORT, the address its Agent Card gives.
"""

from agent_kit.server import serve
from insights.server import create_app
from insights.settings import AgentSettings


def main() -> None:
    """Serve the agent until stopped (Ctrl+C)."""
    settings = AgentSettings()
    serve(create_app(settings), settings.insights_agent_port)


if __name__ == "__main__":
    main()
