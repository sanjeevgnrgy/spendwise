"""The assistant's way to have a receipt read: the ReceiptReader port (port.py) and its adapter (agent_reader.py),
which asks the receipt agent through the remote-agents port (core/agents.py).

The receipt turn (application/receipt_turn.py) uses the port; the composition root builds the adapter, through
module.py, to reach the receipt agent (agents/receipt, Phase 24). Imports run application/ -> receipt_agent/, never
back.
"""
