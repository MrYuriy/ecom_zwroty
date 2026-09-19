import pytest

from app.core import settings
from app.services.google_sheets import get_sheets_client
from app.services.wms_order import parse_rows

SHEET = [
    ["ORDER_ID", "CUSTOMER_ID"],
    ["167162", "26261L44439"],
    [" 167133 ", " 26261L42539 "],
    ["167087"],
    [],
    ["", "orphan"],
    ["167162", "duplicate-ignored"],
]


class FakeSheets:
    def __init__(self, values):
        self.values = values
        self.calls = []

    async def read_columns(self, spreadsheet_id, sheet_gid, columns="A:B"):
        self.calls.append((spreadsheet_id, sheet_gid))
        return self.values


@pytest.fixture
def sheets(app, monkeypatch):
    fake = FakeSheets(SHEET)
    monkeypatch.setattr(settings.google, "WMS_SHEET_ID", "sheet-123")
    app.dependency_overrides[get_sheets_client] = lambda: fake
    return fake


def test_parse_rows_skips_header_blanks_and_duplicates():
    assert parse_rows(SHEET) == {"167162": "26261L44439", "167133": "26261L42539", "167087": None}


async def test_sync_adds_only_new_orders(client, admin_headers, sheets):
    first = await client.post("/api/wms-orders/sync", headers=admin_headers)
    assert first.json() == {"rows": 3, "added": 3}
    assert sheets.calls == [("sheet-123", 0)]

    sheets.values = SHEET + [["170000", "26300L1"]]
    second = await client.post("/api/wms-orders/sync", headers=admin_headers)
    assert second.json() == {"rows": 4, "added": 1}


async def test_lookup_returns_tempo_number(client, admin_headers, sheets):
    await client.post("/api/wms-orders/sync", headers=admin_headers)
    found = await client.get("/api/wms-orders/167133", headers=admin_headers)
    assert found.status_code == 200
    assert found.json()["tempo_number"] == "26261L42539"
    assert (await client.get("/api/wms-orders/999999", headers=admin_headers)).status_code == 404


async def test_lookup_requires_login(client):
    assert (await client.get("/api/wms-orders/167133")).status_code == 401


async def test_only_admin_can_trigger_sync(client, operator_headers, sheets):
    assert (await client.post("/api/wms-orders/sync", headers=operator_headers)).status_code == 403
    assert sheets.calls == []


async def test_sync_without_sheet_id_is_rejected(client, admin_headers, sheets, monkeypatch):
    monkeypatch.setattr(settings.google, "WMS_SHEET_ID", "")
    assert (await client.post("/api/wms-orders/sync", headers=admin_headers)).status_code == 400


async def test_admin_lists_and_searches_orders(client, admin_headers, sheets):
    await client.post("/api/wms-orders/sync", headers=admin_headers)
    everything = (await client.get("/api/wms-orders", headers=admin_headers)).json()
    assert everything["total"] == 3

    by_tempo = (await client.get("/api/wms-orders", params={"q": "42539"}, headers=admin_headers)).json()
    assert [o["bo_wms_number"] for o in by_tempo["items"]] == ["167133"]


async def test_operator_cannot_list_orders(client, operator_headers):
    assert (await client.get("/api/wms-orders", headers=operator_headers)).status_code == 403
