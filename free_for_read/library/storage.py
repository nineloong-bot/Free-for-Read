from pathlib import Path
from typing import Protocol
from uuid import uuid4

from free_for_read.core.errors import ParseError


class StorageBackend(Protocol):
    def save(self, filename: str, content: bytes) -> str:
        raise NotImplementedError

    def path_for(self, key: str) -> Path:
        raise NotImplementedError


class LocalStorageBackend:
    def __init__(self, *, root: Path | str = "storage") -> None:
        self.root = Path(root)

    def save(self, filename: str, content: bytes) -> str:
        safe_name = _safe_filename(filename)
        suffix = Path(safe_name).suffix.lower()
        stem = Path(safe_name).stem.replace(" ", "_") or "book"
        key = f"books/{uuid4().hex}_{stem}{suffix}"
        path = self.root / key
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        except (OSError, ValueError) as exc:
            raise ParseError(
                code="storage_failed",
                message="Failed to save uploaded file.",
                details={"filename": filename},
            ) from exc
        return key

    def path_for(self, key: str) -> Path:
        path = (self.root / key).resolve()
        root = self.root.resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ParseError(
                code="storage_failed",
                message="Stored file path is outside storage root.",
                details={"key": key},
            ) from exc
        return path


def _safe_filename(filename: str) -> str:
    if (
        not filename
        or "/" in filename
        or "\\" in filename
        or any(ord(char) < 32 for char in filename)
    ):
        raise ParseError(
            code="storage_failed",
            message="Unsafe upload filename.",
            details={"filename": filename},
        )
    return filename
