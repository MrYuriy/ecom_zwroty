import asyncio
import logging
import re
from pathlib import Path
from uuid import uuid4

from app.core import settings

logger = logging.getLogger(__name__)

_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
_NO_NUMBER = "brak"
_UNSAFE = re.compile(r"[^A-Za-z0-9-]")
_NUMBERED = re.compile(r"_(\d+)\.[A-Za-z0-9]+$")


def detect_image_type(head: bytes) -> str | None:
    """Content type from the file's magic bytes; the client's Content-Type header is not trusted."""
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def _safe_part(value: str) -> str:
    # Anything outside [A-Za-z0-9-] (including "_", the separator) becomes ~<hex>, so distinct values
    # can never produce the same file name.
    return _UNSAFE.sub(lambda m: f"~{ord(m.group()):x}", value)


def image_file_name(bo_wms_number: str | None, trade_reference: str, number: int, content_type: str) -> str:
    """{bo_wms_number or "brak"}_{trade_reference}_{N}.{ext}"""
    order_part = _safe_part(bo_wms_number) if bo_wms_number else _NO_NUMBER
    return f"{order_part}_{_safe_part(trade_reference)}_{number}.{_EXTENSIONS[content_type]}"


def upload_file_name(index: int, content_type: str) -> str:
    """Temporary name until the image is numbered; sorts in upload order within one batch."""
    return f"new-{index:03d}-{uuid4().hex}.{_EXTENSIONS[content_type]}"


def number_in_name(file_name: str) -> int | None:
    match = _NUMBERED.search(file_name)
    return int(match.group(1)) if match else None


class ImageStorage:
    """Line photos on the local filesystem (a mounted folder in docker)."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or Path(settings.storage.UPLOADS_DIR)).resolve()

    def path_of(self, file_name: str) -> Path:
        path = (self.root / file_name).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f"Refusing a path outside the uploads directory: {file_name}")
        return path

    async def save(self, data: bytes, file_name: str) -> None:
        await asyncio.to_thread(self._write, self.path_of(file_name), data)

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

    async def rename(self, renames: list[tuple[str, str]]) -> None:
        """Rename files old → new; safe when names swap (1↔2), since every file first moves to a temp name."""
        pairs = [(self.path_of(old), self.path_of(new)) for old, new in renames]
        await asyncio.to_thread(self._rename_all, pairs)

    @staticmethod
    def _rename_all(pairs: list[tuple[Path, Path]]) -> None:
        staged = []
        for old, new in pairs:
            if not old.is_file():
                logger.warning("Image file missing, cannot rename: %s", old.name)
                continue
            temp = old.with_name(f"renaming-{uuid4().hex}{old.suffix}")
            old.replace(temp)
            staged.append((temp, new))
        for temp, new in staged:
            temp.replace(new)
