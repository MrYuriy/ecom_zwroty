from datetime import date

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exc import ObjectNotFoundException
from app.database.postgres import get_session
from app.models.work_log import WorkLog
from app.repositories.work_log import WorkLogRepository
from app.schemas.common import Page
from app.schemas.work_log import WorkLogOut, WorkLogSave


def _out(log: WorkLog) -> WorkLogOut:
    return WorkLogOut(
        work_date=log.work_date,
        minutes=log.minutes,
        author_name=log.author.full_name if log.author else None,
    )


class WorkLogService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.logs = WorkLogRepository(session)

    async def save(self, day: date, data: WorkLogSave, author_id: int) -> WorkLogOut:
        """One record per day: the day's entry is created or overwritten."""
        log = await self.logs.get_for_day(day)
        if log:
            log.minutes = data.minutes
            log.author_id = author_id
        else:
            log = WorkLog(work_date=day, minutes=data.minutes, author_id=author_id)
            self.session.add(log)
        await self.session.commit()
        return _out(await self.logs.get_for_day(day))

    async def get(self, day: date) -> WorkLogOut:
        log = await self.logs.get_for_day(day)
        if not log:
            raise ObjectNotFoundException(day.isoformat(), "Work log")
        return _out(log)

    async def delete(self, day: date) -> None:
        log = await self.logs.get_for_day(day)
        if not log:
            raise ObjectNotFoundException(day.isoformat(), "Work log")
        await self.logs.delete_one(log)

    async def recent(self, page: int, limit: int) -> Page[WorkLogOut]:
        logs, total = await self.logs.recent(page, limit)
        return Page(items=[_out(log) for log in logs], total=total, page=page, limit=limit)


def get_work_log_service(session: AsyncSession = Depends(get_session)) -> WorkLogService:
    return WorkLogService(session)
