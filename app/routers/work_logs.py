from datetime import date

from fastapi import APIRouter, Query, Response

from app.dependencies import CurrentUserDep, WorkLogServiceDep
from app.schemas.common import Page
from app.schemas.work_log import WorkLogOut, WorkLogSave

router = APIRouter(prefix="/work-logs", tags=["Work logs"])


@router.get("", response_model=Page[WorkLogOut])
async def list_work_logs(
    service: WorkLogServiceDep,
    _: CurrentUserDep,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> Page[WorkLogOut]:
    return await service.recent(page, limit)


@router.get("/{day}", response_model=WorkLogOut)
async def get_work_log(day: date, service: WorkLogServiceDep, _: CurrentUserDep) -> WorkLogOut:
    return await service.get(day)


@router.put("/{day}", response_model=WorkLogOut)
async def save_work_log(day: date, data: WorkLogSave, service: WorkLogServiceDep, user: CurrentUserDep) -> WorkLogOut:
    return await service.save(day, data, user.id)


@router.delete("/{day}", status_code=204)
async def delete_work_log(day: date, service: WorkLogServiceDep, _: CurrentUserDep) -> Response:
    await service.delete(day)
    return Response(status_code=204)
