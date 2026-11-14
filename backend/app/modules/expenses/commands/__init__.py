"""The expenses module's commands, one file each: the command message, its handler and anything only it uses; the
only code that changes expenses. Handlers apply the rules in domain/rules.py, then stage their change through
persistence/repository.py. module.py registers each handler with the bus; the package's __init__.py exports the
messages.
"""
