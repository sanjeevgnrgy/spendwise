"""The approval commands, one vertical slice per file: the command message and its handler, side by side.

request_approval.py (a card is shown: remember it), take_approval.py (Approve or Cancel arrives: read and forget
it in one step) and restore_approval.py (the decision failed midway: put it back). module.py registers each
handler on the bus; the rest of the assistant sends the commands, imported from the approvals package.
Nothing is exported here: each file is imported by its full path.
"""
