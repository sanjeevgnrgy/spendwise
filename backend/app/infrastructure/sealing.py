"""FernetSealer: the Sealer port (core/sealing.py) with Fernet, authenticated encryption (infrastructure, adapter).

The composition root builds one from SESSION_ENCRYPTION_KEYS and hands it to the accounts module, which seals the
identity provider's ID token before a session stores it. Fernet is AES-128-CBC with an HMAC-SHA256 over the result,
from the `cryptography` package; MultiFernet tries each key, so keys can be rotated: put the new one first, keep the
old one until the sessions sealed with it have expired, then remove it.
"""

from collections.abc import Sequence

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

# What a sealed text is written in: Fernet tokens are URL-safe base64.
ASCII = "ascii"
NO_KEYS = "SESSION_ENCRYPTION_KEYS isn't set, so nothing can be sealed."


class FernetSealer:
    """Seals with the first of `keys` and unseals with any of them. With no keys it seals nothing (sign-in is then
    unavailable, so it's never asked to)."""

    def __init__(self, keys: Sequence[str]) -> None:
        """Use `keys`, newest first: each a Fernet key (32 random bytes, URL-safe base64).

        Raises ValueError, as the app starts, if one isn't a valid key.
        """
        try:
            self._fernet = MultiFernet([Fernet(key) for key in keys]) if keys else None
        except ValueError as error:
            raise ValueError(f"A SESSION_ENCRYPTION_KEYS entry isn't a Fernet key: {error}") from None

    def seal(self, text: str) -> str:
        """`text`, encrypted and authenticated with the newest key. Raises RuntimeError if there's no key."""
        if self._fernet is None:
            raise RuntimeError(NO_KEYS)
        return self._fernet.encrypt(text.encode()).decode(ASCII)

    def unseal(self, sealed: str) -> str | None:
        """The sealed text; None if no key opens it, or it was changed (Fernet checks its HMAC)."""
        if self._fernet is None:
            return None
        try:
            return self._fernet.decrypt(sealed.encode(ASCII)).decode()
        except (InvalidToken, ValueError):
            return None
