"""The assistant's use cases: what the routes ask for, carried out with the agent, the tools and the bus.

Application layer: assistant.py (Assistant: run_turn, decide, chat), decisions.py (Approve/Cancel on a delete
card, without the model) and expense_parser.py (ExpenseParser, POST /parse). The routes (api/routes.py) call
them; module.py builds them. Nothing is exported here: each file is imported by its full path.
"""
