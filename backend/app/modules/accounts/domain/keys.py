"""The random values a sign-in and a session are made of, and how keys are stored (accounts module, domain).

Cookie keys, state, nonce and the PKCE verifier come from the operating system's secure random source (`secrets`):
nobody can guess or predict them. A cookie's key is stored only as its SHA-256 hash, so the database alone never
gives a working cookie away. Used by the sign-in use cases (application/) and the session check.
"""

import hashlib
import secrets

# 32 random bytes (256 bits) for every key, state and nonce: 43 URL-safe characters.
KEY_BYTES = 32
# 64 bytes for the PKCE verifier: 86 characters, inside RFC 7636's 43 to 128 (4.1).
VERIFIER_BYTES = 64
# 16 bytes for a session's public handle: 32 hex characters.
HANDLE_BYTES = 16


def new_key() -> str:
    """A new random key: a cookie's value, or a sign-in's state or nonce."""
    return secrets.token_urlsafe(KEY_BYTES)


def new_verifier() -> str:
    """A new PKCE code verifier: only its SHA-256 goes to the provider at first, so a stolen code is useless."""
    return secrets.token_urlsafe(VERIFIER_BYTES)


def new_handle() -> str:
    """A session's new public handle: unguessable, so a sign-out link can't be forged."""
    return secrets.token_hex(HANDLE_BYTES)


def hash_key(key: str) -> str:
    """How a key is stored and looked up: its SHA-256, in hex. A random 256-bit key needs no slow hash or salt."""
    return hashlib.sha256(key.encode()).hexdigest()
