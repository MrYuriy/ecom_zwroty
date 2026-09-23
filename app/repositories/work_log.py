from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.work_log import WorkLog
from app.repositories.base import BaseRepository


class WorkLogRepository(BaseRepository[WorkLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WorkLog)

    async def get_for_day(self, day: date) -> WorkLog | None:
        query = select(WorkLog).where(WorkLog.work_date == day).options(selectinload(WorkLog.author))
        return (await self.session.execute(query)).scalar_one_or_none()

    async def minutes_for_day(self, day: date) -> int | None:
        return await self.session.scalar(select(WorkLog.minutes).where(WorkLog.work_date == day))

    async def recent(self, page: int, limit: int) -> tuple[list[WorkLog], int]:
        query = (
            select(WorkLog)
            .options(selectinload(WorkLog.author))
            .order_by(WorkLog.work_date.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        rows = (await self.session.execute(query)).scalars().all()
        total = (await self.session.execute(select(func.count()).select_from(WorkLog))).scalar() or 0
        return list(rows), total
