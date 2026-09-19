from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.dependencies import CurrentUserDep, ReturnOrderServiceDep

router = APIRouter(prefix="/images", tags=["Images"])


@router.get("/{image_uuid}", response_class=FileResponse)
async def get_image(image_uuid: UUID, service: ReturnOrderServiceDep, _: CurrentUserDep) -> FileResponse:
    path, content_type, file_name = await service.get_image_file(image_uuid)
    # The content never changes under its uuid (only the name may); "private" keeps shared caches out of it.
    return FileResponse(
        path,
        media_type=content_type,
        filename=file_name,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, max-age=86400"},
    )
