import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.core.exc import ObjectNotFoundException

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

_NO_CACHE = {"Cache-Control": "no-cache, must-revalidate"}
_SAFE_PAGE = re.compile(r"^[a-z0-9_-]+$")


class _CabinetFiles(StaticFiles):
    def file_response(self, *args, **kwargs) -> Response:
        response = super().file_response(*args, **kwargs)
        response.headers.update(_NO_CACHE)
        return response


def asset_version() -> str:
    """Stamp for JS/CSS URLs that moves with the files, so a deploy is never served stale scripts."""
    newest = max(
        (path.stat().st_mtime for pattern in ("*.js", "*.css") for path in FRONTEND_DIR.glob(pattern)),
        default=0.0,
    )
    return f"{int(newest):x}"


def register_cabinet(app: FastAPI) -> None:
    version = asset_version()

    def render(name: str) -> HTMLResponse:
        path = FRONTEND_DIR / name
        if not _SAFE_PAGE.match(path.stem) or not path.is_file():
            raise ObjectNotFoundException(name, "Page")
        html = path.read_text(encoding="utf-8").replace("?v=dev", f"?v={version}")
        return HTMLResponse(html, headers=_NO_CACHE)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse("/app/")

    @app.get("/app", include_in_schema=False)
    @app.get("/app/", include_in_schema=False)
    async def cabinet_index() -> HTMLResponse:
        return render("index.html")

    @app.get("/app/{name}.html", include_in_schema=False)
    async def cabinet_page(name: str) -> HTMLResponse:
        return render(f"{name}.html")

    app.mount("/app", _CabinetFiles(directory=FRONTEND_DIR, html=True), name="frontend")
