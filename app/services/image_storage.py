import asyncio
from pathlib import Path
from uuid import uuid4

from app.core import settings

_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def detect_image_type(head: bytes) -> str | None:
    """Content type from the file's magic bytes; the client's Content-Type header is not trusted."""
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


class ImageStorage:
    """Line photos on the local filesystem (a docker volume in production)."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or Path(settings.storage.UPLOADS_DIR)).resolve()

    def path_of(self, file_name: str) -> Path:
        path = (self.root / file_name).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f"Refusing a path outside the uploads directory: {file_name}")
        return path

    async def save(self, data: bytes, content_type: str) -> str:
        file_name = f"{uuid4().hex}.{_EXTENSIONS[content_type]}"
        path = self.path_of(file_name)
        await asyncio.to_thread(self._write, path, data)
        return file_name

    @staticmethod
    def _write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    async def delete(self, file_names: list[str]) -> None:
        await asyncio.to_thread(self._unlink_all, [self.path_of(name) for name in file_names])

    @staticmethod
    def _unlink_all(paths: list[Path]) -> None:
        for path in paths:
            path.unlink(missing_ok=True)
