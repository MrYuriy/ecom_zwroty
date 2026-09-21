import pytest_asyncio

LINE = {"quantity": 1, "carrier_type": "PARCEL", "goods_condition": "DAMAGED", "damage_description": "rogi"}


@pytest_asyncio.fixture
async def sku_id(client, operator_headers) -> int:
    payload = {
        "trade_reference": "82376357",
        "eans": ["5900000000001"],
        "product_name": "Dysk",
        "is_parametrized": True,
    }
    return (await client.post("/api/skus", json=payload, headers=operator_headers)).json()["id"]


async def _create_order(client, headers, **payload) -> dict:
    response = await client.post("/api/returns", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def test_create_order_sets_operator_and_today(client, operator_headers):
    me = (await client.get("/api/auth/me", headers=operator_headers)).json()
    order = await _create_order(client, operator_headers, bo_wms_number="356902", tempo_number="25343L5901")
    assert order["operator_id"] == me["id"]
    assert order["return_date"]
    assert order["lines"] == []


async def test_brak_and_blank_numbers_are_stored_as_null(client, operator_headers):
    order = await _create_order(client, operator_headers, bo_wms_number="brak", tempo_number="  ")
    assert order["bo_wms_number"] is None
    assert order["tempo_number"] is None


async def test_same_number_may_repeat(client, operator_headers):
    await _create_order(client, operator_headers, bo_wms_number="361852")
    await _create_order(client, operator_headers, bo_wms_number="361852")


async def test_add_update_delete_line(client, operator_headers, sku_id):
    order = await _create_order(client, operator_headers, bo_wms_number="359048")
    url = f"/api/returns/{order['uuid']}/lines"

    order = (
        await client.post(url, json={**LINE, "sku_id": sku_id, "remarks": "dysk"}, headers=operator_headers)
    ).json()
    line = order["lines"][0]
    assert line["sku"]["trade_reference"] == "82376357"
    assert line["remarks"] == "dysk"

    updated = await client.patch(
        f"{url}/{line['uuid']}", json={"quantity": 3, "damage_description": None}, headers=operator_headers
    )
    assert updated.json()["lines"][0]["quantity"] == 3
    assert updated.json()["lines"][0]["damage_description"] is None

    deleted = await client.delete(f"{url}/{line['uuid']}", headers=operator_headers)
    assert deleted.json()["lines"] == []


async def test_line_rejects_zero_quantity_and_unknown_sku(client, operator_headers, sku_id):
    order = await _create_order(client, operator_headers)
    url = f"/api/returns/{order['uuid']}/lines"
    assert (
        await client.post(url, json={**LINE, "sku_id": sku_id, "quantity": 0}, headers=operator_headers)
    ).status_code == 422
    assert (await client.post(url, json={**LINE, "sku_id": 9999}, headers=operator_headers)).status_code == 404


async def test_delete_order_removes_lines(client, operator_headers, sku_id):
    order = await _create_order(client, operator_headers)
    await client.post(f"/api/returns/{order['uuid']}/lines", json={**LINE, "sku_id": sku_id}, headers=operator_headers)

    assert (await client.delete(f"/api/returns/{order['uuid']}", headers=operator_headers)).status_code == 204
    assert (await client.get(f"/api/returns/{order['uuid']}", headers=operator_headers)).status_code == 404


async def test_list_filters_by_number_and_date(client, operator_headers):
    await _create_order(client, operator_headers, bo_wms_number="500341", return_date="2026-01-02")
    await _create_order(client, operator_headers, tempo_number="25355L36", return_date="2026-01-05")

    by_number = await client.get("/api/returns", params={"number": "25355"}, headers=operator_headers)
    assert by_number.json()["total"] == 1

    by_date = await client.get(
        "/api/returns", params={"date_from": "2026-01-03", "date_to": "2026-01-31"}, headers=operator_headers
    )
    assert [o["tempo_number"] for o in by_date.json()["items"]] == ["25355L36"]
