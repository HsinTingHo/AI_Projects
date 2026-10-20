"""Shared storage contract and object-key validation.

ReportStorage describes the methods adapters provide; it does not implement I/O.
LocalStorage and GCSStorage satisfy this protocol without inheriting from it.
Methods are synchronous: async services should call them in a worker thread.
"""

from typing import BinaryIO, Protocol


class ReportStorage(Protocol):
    """Storage-independent operations on caller-owned binary streams.

    Adapters validate keys, leave streams open, and propagate operational errors.
    Keys identify immutable uploads and must not be reused for another report.
    """

    def save(self, key: str, source: BinaryIO) -> None:
        """Save bytes from the current position through EOF."""
        ...

    def download_to(self, key: str, destination: BinaryIO) -> None:
        """Copy the object into destination at its current position."""
        ...

    def delete(self, key: str) -> None:
        """Delete a key; missing keys are harmless. Keys must never be reused."""
        ...


def validate_key(key: str) -> str:
    """Return a valid relative slash-separated key unchanged.

    Reject rather than normalize ambiguous paths so local and cloud storage
    agree on object identity. This does not sanitize an uploaded filename or
    enforce filesystem containment; the local adapter checks containment too.
    """
    if not isinstance(key, str):
        raise TypeError("Storage key must be a string")
    if not key:
        raise ValueError("Storage key must not be empty")
    if "\\" in key or ":" in key:
        raise ValueError("Storage key must use relative paths with forward slashes")
    if any(ord(character) < 32 or ord(character) == 127 for character in key):
        raise ValueError("Storage key must not contain control characters")
    if any(part in ("", ".", "..") for part in key.split("/")):
        raise ValueError("Storage key must not contain empty or traversal segments")
    return key
