"""The agent loop: ask the model, run the tools it asks for, and repeat until it answers.

Application layer: agent.py (Agent.run), surfaces.py (what differs between text chat and the web panel),
prompts.py (the system instruction), tool_runs.py (running one tool over the ExpenseTools port) and events.py
(the plain events a turn yields, which api/agui_stream.py turns into AG-UI). The use cases (application/) run
it. Nothing is exported here: each file is imported by its full path.
"""
