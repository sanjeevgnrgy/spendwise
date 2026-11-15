"""Keeping a secret text unreadable where it's stored: the Sealer port (core layer).

A session keeps the identity provider's ID token on the server (signing out names it to the provider). The database
holds it sealed: encrypted and authenticated, so a copy of the database doesn't give the tokens away. The accounts
module's sign-in use cases seal and unseal through this port; the composition root picks the adapter (today
infrastructure/sealing.FernetSealer, with SESSION_ENCRYPTION_KEYS). A check passes its own.
"""

from typing import Protocol


class Sealer(Protocol):
    """Seals texts so only this app can read them back."""

    def seal(self, text: str) -> str:
        """`text`, encrypted and authenticated, as printable text. Raises RuntimeError if no key is configured."""
        ...

    def unseal(self, sealed: str) -> str | None:
        """The text `sealed` was made from; None if it can't be read (another key, tampered with, or no key)."""
        ...
