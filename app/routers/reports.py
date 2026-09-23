from datetime import date

from fastapi import APIRouter, Query, Response

from app.dependencies import CurrentUserDep, DayReportPdfServiceDep

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/day-pdf")
async def day_report_pdf(
    service: DayReportPdfServiceDep,
    _: CurrentUserDep,
    day: date = Query(description="Return date (data zwrotu) to print"),
) -> Response:
    """The signed paper form for one day, filled in — opened in a browser tab, not downloaded."""
    pdf = await service.build(day)
    return Response(
        content=pdf.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="Zwroty_od_klientow_{day.isoformat()}.pdf"',
            # Built per request from the current data; nothing is stored, nothing may be cached.
            "Cache-Control": "no-store",
        },
    )
