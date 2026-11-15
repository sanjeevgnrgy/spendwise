"""The accounts module's use cases that aren't bus messages (application/): signing in (sign_in.py), signing out
(sign_out.py), and the session check every protected request goes through (sessions.py). They call the identity
provider, which can take seconds, so they aren't handlers: a handler runs inside a database session that would be
held open meanwhile. The composition root builds them through module.py, with the provider and the sealer passed in.
"""
