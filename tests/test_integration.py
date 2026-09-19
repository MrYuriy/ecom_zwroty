import pytest

from app.core import settings

KEY = "test-integration-key"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture
def api_key(monkeypatch) -> dict:
    monkeypatch.setattr(settings.integration, "API_KEY", KEY)
    monkeypatch.setattr(settings.integration, "PUBLIC_BASE_URL", "https://ecom.example.com/")
    return {"X-API-Key": KEY}


async def _sku(client, headers, reference: str, parametrized: bool = True) -> int:
    payload = {"trade_reference": reference, "product_name": reference, "is_parametrized": parametrized}
    return (await client.post("/api/skus", json=payload, headers=headers)).json()["id"]


async def _order(client, headers, **header) -> str:
    return (await client.post("/api/returns", json=header, headers=headers)).json()["uuid"]


async def _add_line(client, headers, order: str, sku_id: int, **fields) -> str:
    body = {"quantity": 1, "carrier_type": "PARCEL", "goods_condition": "FULL_VALUE", "sku_id": sku_id, **fields}
    response = await client.post(f"/api/returns/{order}/lines", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["lines"][-1]["uuid"]


async def _close(client, headers, order: str) -> dict:
    response = await client.post(f"/api/returns/{order}/close", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


# ---------- report lines ----------


async def test_report_lines_match_the_report_layout(client, operator_headers, api_key):
    damaged = await _sku(client, operator_headers, "45783276")
    unparametrized = await _sku(client, operator_headers, "45603124", parametrized=False)

    first = await _order(client, operator_headers, return_date="2026-01-02")
    await _add_line(
        client,
        operator_headers,
        first,
        damaged,
        goods_condition="DAMAGED",
        damage_description="rogi",
        remarks="etykieta na @",
    )
    second = await _order(
        client, operator_headers, bo_wms_number="363775", tempo_number="25363L21171", return_date="2026-01-05"
    )
    await _add_line(client, operator_headers, second, unparametrized, quantity=15, carrier_type="PALLET")
    for order in (first, second):
        await _close(client, operator_headers, order)

    data = (await client.get("/api/integration/report-lines", headers=api_key)).json()
    assert data["columns"] == [
        "DATA ZWROTU",
        "NUMER BO/WMS",
        "NUMER TEMPO",
        "REFERENCJA HANDLOWA",
        "Produkt sparametryzowany",
        "UWAGI",
        "ILOŚĆ",
        "NOŚNIK",
        "KLASYFIKACJA TOWARU",
        "OPIS USZKODZENIA",
    ]
    assert [item["row"] for item in data["items"]] == [
        ["2026-01-02", "brak", "brak", "45783276", "tak", "etykieta na @", 1, "paczka", "uszkodzony", "rogi"],
        ["2026-01-05", "363775", "25363L21171", "45603124", "nie", "", 15, "paleta", "pełnowartościowy", ""],
    ]
    assert data["remaining"] == 0


async def test_only_closed_returns_are_exported(client, operator_headers, api_key):
    sku_id = await _sku(client, operator_headers, "82376357")
    open_order = await _order(client, operator_headers)
    await _add_line(client, operator_headers, open_order, sku_id)
    assert (await client.get("/api/integration/report-lines", headers=api_key)).json()["items"] == []

    await _close(client, operator_headers, open_order)
    assert len((await client.get("/api/integration/report-lines", headers=api_key)).json()["items"]) == 1


async def test_acknowledged_lines_are_not_sent_again(client, operator_headers, api_key):
    sku_id = await _sku(client, operator_headers, "82376357")
    order = await _order(client, operator_headers)
    lines = [await _add_line(client, operator_headers, order, sku_id) for _ in range(3)]
    await _close(client, operator_headers, order)

    page = (await client.get("/api/integration/report-lines", params={"limit": 2}, headers=api_key)).json()
    assert len(page["items"]) == 2 and page["remaining"] == 1

    sent = [item["line_uuid"] for item in page["items"]]
    ack = await client.post("/api/integration/report-lines/ack", json={"line_uuids": sent}, headers=api_key)
    assert ack.json() == {"acknowledged": 2}
    again = await client.post("/api/integration/report-lines/ack", json={"line_uuids": sent}, headers=api_key)
    assert again.json() == {"acknowledged": 0}

    rest = (await client.get("/api/integration/report-lines", headers=api_key)).json()
    assert [item["line_uuid"] for item in rest["items"]] == [line for line in lines if line not in sent]


async def test_edits_after_export_are_not_sent_again(client, operator_headers, api_key):
    sku_id = await _sku(client, operator_headers, "82376357")
    order = await _order(client, operator_headers)
    line = await _add_line(client, operator_headers, order, sku_id)
    await _close(client, operator_headers, order)
    await client.post("/api/integration/report-lines/ack", json={"line_uuids": [line]}, headers=api_key)

    await client.post(f"/api/returns/{order}/reopen", headers=operator_headers)
    await client.patch(f"/api/returns/{order}/lines/{line}", json={"quantity": 5}, headers=operator_headers)
    new_line = await _add_line(client, operator_headers, order, sku_id)
    await _close(client, operator_headers, order)

    items = (await client.get("/api/integration/report-lines", headers=api_key)).json()["items"]
    assert [item["line_uuid"] for item in items] == [new_line]


# ---------- images ----------


async def test_images_flow(client, operator_headers, api_key):
    sku_id = await _sku(client, operator_headers, "82376357")
    order = await _order(client, operator_headers, bo_wms_number="356902", return_date="2026-01-02")
    line = await _add_line(client, operator_headers, order, sku_id)
    await client.post(
        f"/api/returns/{order}/lines/{line}/images", files=[("files", ("a.png", PNG))], headers=operator_headers
    )
    assert (await client.get("/api/integration/images", headers=api_key)).json()["items"] == []  # still open

    await _close(client, operator_headers, order)
    item = (await client.get("/api/integration/images", headers=api_key)).json()["items"][0]
    assert item["file_name"] == "356902_82376357_1.png"
    assert item["url"] == f"https://ecom.example.com/api/integration/images/{item['image_uuid']}"
    assert item["bo_wms_number"] == "356902" and item["trade_reference"] == "82376357"

    file = await client.get(f"/api/integration/images/{item['image_uuid']}", headers=api_key)
    assert file.content == PNG
    assert 'filename="356902_82376357_1.png"' in file.headers["content-disposition"]

    ack = await client.post("/api/integration/images/ack", json={"image_uuids": [item["image_uuid"]]}, headers=api_key)
    assert ack.json() == {"acknowledged": 1}
    assert (await client.get("/api/integration/images", headers=api_key)).json()["items"] == []
    # The report line is a separate stream and is still pending.
    assert len((await client.get("/api/integration/report-lines", headers=api_key)).json()["items"]) == 1


# ---------- auth ----------


async def test_integration_needs_a_key_or_a_login(client, api_key):
    assert (await client.get("/api/integration/report-lines")).status_code == 401
    wrong = {"X-API-Key": "nope"}
    assert (await client.get("/api/integration/report-lines", headers=wrong)).status_code == 401


async def test_a_logged_in_user_can_use_the_integration(client, operator_headers):
    # A person pressing the button in the sheet logs in; no API key needed.
    assert (await client.get("/api/integration/report-lines", headers=operator_headers)).status_code == 200


async def test_no_key_configured_rejects_any_key(client, monkeypatch):
    monkeypatch.setattr(settings.integration, "API_KEY", "")
    response = await client.get("/api/integration/report-lines", headers={"X-API-Key": ""})
    assert response.status_code == 401
