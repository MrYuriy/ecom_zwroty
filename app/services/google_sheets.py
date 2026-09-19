import asyncio
from pathlib import Path

import httpx
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from app.core import settings

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
_API = "https://sheets.googleapis.com/v4/spreadsheets"


class GoogleSheetsError(RuntimeError):
    pass


class GoogleSheetsClient:
    """Read-only Google Sheets access with a service account."""

    def __init__(self, credentials_file: str | None = None) -> None:
        self._credentials_file = Path(credentials_file or settings.google.CREDENTIALS_FILE)
        self._credentials: service_account.Credentials | None = None

    async def _token(self) -> str:
        if self._credentials is None:
            if not self._credentials_file.is_file():
                raise GoogleSheetsError(f"Credentials file not found: {self._credentials_file}")
            self._credentials = service_account.Credentials.from_service_account_file(
                str(self._credentials_file), scopes=_SCOPES
            )
        if not self._credentials.valid:
            # google-auth refreshes synchronously (requests); keep it off the event loop.
            await asyncio.to_thread(self._credentials.refresh, Request())
        return self._credentials.token

    async def _get(self, client: httpx.AsyncClient, url: str, params: dict | None = None) -> dict:
        response = await client.get(url, params=params, headers={"Authorization": f"Bearer {await self._token()}"})
        if response.status_code != 200:
            raise GoogleSheetsError(f"Google Sheets API {response.status_code}: {response.text[:300]}")
        return response.json()

    async def read_columns(self, spreadsheet_id: str, sheet_gid: int, columns: str = "A:B") -> list[list[str]]:
        """All rows of the given columns of the tab with this gid (the number after #gid= in its URL)."""
        async with httpx.AsyncClient(timeout=30) as client:
            meta = await self._get(client, f"{_API}/{spreadsheet_id}", {"fields": "sheets.properties(sheetId,title)"})
            titles = {s["properties"]["sheetId"]: s["properties"]["title"] for s in meta.get("sheets", [])}
            if sheet_gid not in titles:
                raise GoogleSheetsError(f"No tab with gid={sheet_gid} in spreadsheet {spreadsheet_id}")
            # Quotes keep tab names with spaces valid in A1 notation.
            quoted = "'" + titles[sheet_gid].replace("'", "''") + "'"
            data = await self._get(client, f"{_API}/{spreadsheet_id}/values/{quoted}!{columns}")
        return data.get("values", [])


def get_sheets_client() -> GoogleSheetsClient:
    return GoogleSheetsClient()
