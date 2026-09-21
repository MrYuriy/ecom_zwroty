"""Bulk update of the SKU register from the warehouse SKU/EAN export.

Adds new products and codes, updates names and the "parametrized" flag (the file's `ecommerce` Y/N),
and moves a code to the last product the file lists it under. Nothing is ever deleted: old returns
keep pointing at their products. The whole write is one transaction, so a failure leaves the register as it was.
"""

import asyncio
import logging
import os
import tempfile
from datetime import timedelta
from pathlib import Path
from uuid import UUID

from fastapi import Depends, UploadFile
from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exc import BadRequestException, ObjectNotFoundException
from app.database.postgres import async_session, get_session
from app.enums.sku_import import SkuImportStatus
from app.models.sku_import import SkuImport
from app.repositories.sku_import import SkuBulkRepository, SkuImportRepository
from app.schemas.sku_import import SkuImportOut
from app.services.sku_import_parser import ParsedSkuFile, parse_sku_file

logger = logging.getLogger(__name__)

MAX_FILE_MB = 200
_STALE_AFTER = timedelta(hours=2)
_CHUNK = 1024 * 1024


class SkuImportService:
    def __init__(self, session: AsyncSession) -> None:
        self.imports = SkuImportRepository(session)

    async def start(self, upload: UploadFile, user_id: int) -> tuple[SkuImportOut, Path]:
        if await self.imports.running(_STALE_AFTER):
            raise BadRequestException("An import is already running; wait for it to finish")
        path = await _save_upload(upload)
        job = await self.imports.create_one({"file_name": (upload.filename or "plik")[:255], "started_by_id": user_id})
        return SkuImportOut.model_validate(job), path

    async def latest(self) -> SkuImportOut | None:
        job = await self.imports.latest()
        return SkuImportOut.model_validate(job) if job else None

    async def get(self, import_uuid: UUID) -> SkuImportOut:
        job = await self.imports.get_one(uuid=import_uuid)
        if not job:
            raise ObjectNotFoundException(import_uuid, "SKU import")
        return SkuImportOut.model_validate(job)


async def _save_upload(upload: UploadFile) -> Path:
    handle, name = tempfile.mkstemp(prefix="sku-import-", suffix=".json")
    path = Path(name)
    size = 0
    try:
        with os.fdopen(handle, "wb") as out:
            while chunk := await upload.read(_CHUNK):
                size += len(chunk)
                if size > MAX_FILE_MB * 1024 * 1024:
                    raise BadRequestException(f"The file is larger than {MAX_FILE_MB} MB")
                out.write(chunk)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    if size == 0:
        path.unlink(missing_ok=True)
        raise BadRequestException("The file is empty")
    return path


async def run_import(import_uuid: UUID, path: Path, session_factory: async_sessionmaker) -> None:
    """Background job: parse the file, then write everything in one transaction."""

    async def report(**fields) -> None:
        async with session_factory() as session:
            await session.execute(
                update(SkuImport).where(SkuImport.uuid == import_uuid).values(**fields, updated_at=func.now())
            )
            await session.commit()

    try:
        await report(status=SkuImportStatus.RUNNING, stage="czytanie pliku")
        raw = await asyncio.to_thread(path.read_bytes)
        parsed = await asyncio.to_thread(parse_sku_file, raw)
        del raw
        await report(stage="zapis do bazy", rows_read=parsed.rows_read, rows_skipped=parsed.rows_skipped)

        async with session_factory() as session:
            counts = await _write(SkuBulkRepository(session), parsed)
            await session.commit()

        await report(status=SkuImportStatus.DONE, stage=None, finished_at=func.now(), **counts)
        logger.info("SKU import %s done: %s", import_uuid, counts)
    except Exception as error:
        logger.exception("SKU import %s failed", import_uuid)
        await report(status=SkuImportStatus.FAILED, stage=None, error=str(error)[:1000], finished_at=func.now())
    finally:
        path.unlink(missing_ok=True)


async def _write(bulk: SkuBulkRepository, parsed: ParsedSkuFile) -> dict[str, int]:
    existing = await bulk.sku_map()
    new_skus, changed_skus = [], []
    for reference, (name, flag) in parsed.skus.items():
        if reference not in existing:
            new_skus.append({"trade_reference": reference, "product_name": name, "is_parametrized": bool(flag)})
            continue
        sku_id, old_name, old_flag = existing[reference]
        changes = {}
        if name != old_name:
            changes["product_name"] = name
        # No ecommerce value in the file means "no opinion": keep what the register has.
        if flag is not None and flag != old_flag:
            changes["is_parametrized"] = flag
        if changes:
            changed_skus.append({"id": sku_id, **changes})
    await bulk.insert_skus(new_skus)
    await bulk.update_skus(changed_skus)

    ids = {reference: values[0] for reference, values in (await bulk.sku_map()).items()}
    codes = await bulk.ean_map()
    new_eans, moved_eans = [], []
    for code, reference in parsed.eans.items():
        target = ids[reference]
        if code not in codes:
            new_eans.append({"ean": code, "sku_id": target})
        elif codes[code][1] != target:
            moved_eans.append({"id": codes[code][0], "sku_id": target})
    await bulk.insert_eans(new_eans)
    await bulk.update_eans(moved_eans)

    return {
        "skus_created": len(new_skus),
        "skus_updated": len(changed_skus),
        "eans_created": len(new_eans),
        "eans_reassigned": len(moved_eans),
    }


def get_sku_import_service(session: AsyncSession = Depends(get_session)) -> SkuImportService:
    return SkuImportService(session)


def get_session_factory() -> async_sessionmaker:
    """The background job opens its own sessions; tests point this at their database."""
    return async_session
