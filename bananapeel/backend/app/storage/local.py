"""Local storage with atomic publication and no overwriting of existing reports."""

import os
from pathlib import Path
import shutil
import tempfile
from typing import BinaryIO

from app.storage.base import validate_key


class LocalStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / validate_key(key)).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Storage key escapes the configured root")
        return path

    def save(self, key: str, source: BinaryIO) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".upload-")
        try:
            with os.fdopen(descriptor, "wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
                output.flush()
                os.fsync(output.fileno())
            # Atomic create; unlike replace(), link() fails if the key exists.
            os.link(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def download_to(self, key: str, destination: BinaryIO) -> None:
        with self._path(key).open("rb") as source:
            shutil.copyfileobj(source, destination, length=1024 * 1024)

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)
