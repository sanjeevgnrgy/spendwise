"""Where uploaded files' bytes are kept, independent of the storage behind it: the FileStore port (core layer).

The receipts module saves an uploaded receipt here and reads it back to send it to the model; its table keeps
only the key. The composition root (bootstrap.py) picks the adapter: today infrastructure/files.LocalFileStore, a
folder on disk (UPLOADS_DIR). A check passes its own, e.g. one that keeps files in memory.
"""

from typing import Protocol


class FileStore(Protocol):
    """Keeps files' bytes under keys it makes up itself, so no name a user chose ever reaches a path."""

    def save(self, data: bytes) -> str:
        """Store `data` under a new, unguessable key, and return the key."""
        ...

    def read(self, key: str) -> bytes:
        """The bytes stored under `key`. Raises FileNotFoundError if there are none (or the key is malformed)."""
        ...

    def delete(self, key: str) -> None:
        """Forget the bytes under `key`; nothing happens if there are none."""
        ...
