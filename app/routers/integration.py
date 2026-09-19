"""API for external scripts (Google Apps Script): a logged-in user's token or the X-API-Key header.

Flow per stream: GET the pending items, write/download them, then POST their uuids to .../ack.
Nothing counts as delivered until acknowledged, so a script that fails half-way just gets the rest again.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse

from app.core import settings
from app.core.security.integration_access import require_integration_access
from app.dependencies import IntegrationServiceDep
from app.schemas.integration import AckResult, ImagesAck, ImagesOut, LinesAck, ReportLinesOut

router = APIRouter(prefix="/integration", tags=["Integration"], dependencies=[Depends(require_integration_access)])


def _base_url(request: Request) -> str:
    return (settings.integration.PUBLIC_BASE_URL or str(request.base_url)).rstrip("/")


@router.get("/report-lines", response_model=ReportLinesOut)
async def report_lines(service: IntegrationServiceDep, limit: int = Query(500, ge=1, le=1000)) -> ReportLinesOut:
    """Report rows of closed returns not delivered yet, oldest first, in the report sheet's column order."""
    return await service.report_lines(limit)


@router.post("/report-lines/ack", response_model=AckResult)
async def acknowledge_report_lines(data: LinesAck, service: IntegrationServiceDep) -> AckResult:
    return await service.acknowledge_lines(data.line_uuids)


@router.get("/images", response_model=ImagesOut)
async def pending_images(
    request: Request, service: IntegrationServiceDep, limit: int = Query(100, ge=1, le=1000)
) -> ImagesOut:
    """Photos of closed returns not downloaded yet, each with a download URL (same X-API-Key header)."""
    return await service.images(limit, _base_url(request))


@router.get("/images/{image_uuid}", response_class=FileResponse)
async def download_image(image_uuid: UUID, service: IntegrationServiceDep) -> FileResponse:
    path, content_type, file_name = await service.image_file(image_uuid)
    return FileResponse(path, media_type=content_type, filename=file_name)


@router.post("/images/ack", response_model=AckResult)
async def acknowledge_images(data: ImagesAck, service: IntegrationServiceDep) -> AckResult:
    return await service.acknowledge_images(data.image_uuids)
