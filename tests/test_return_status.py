PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


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


async def test_close_and_reopen(client, operator_headers):
    order = await _order(client, operator_headers)
    assert (await client.get(f"/api/returns/{order}", headers=operator_headers)).json()["status"] == "OPEN"

    closed = await _close(client, operator_headers, order)
    assert closed["status"] == "CLOSED" and closed["closed_at"]
    assert (await _close(client, operator_headers, order))["status"] == "CLOSED"  # idempotent

    reopened = (await client.post(f"/api/returns/{order}/reopen", headers=operator_headers)).json()
    assert reopened["status"] == "OPEN" and reopened["closed_at"] is None


async def test_closed_return_is_locked_until_reopened(client, operator_headers):
    sku_id = await _sku(client, operator_headers, "82376357")
    order = await _order(client, operator_headers)
    line = await _add_line(client, operator_headers, order, sku_id)
    await _close(client, operator_headers, order)

    blocked = [
        client.post(
            f"/api/returns/{order}/lines",
            json={"quantity": 1, "carrier_type": "PARCEL", "goods_condition": "DAMAGED", "sku_id": sku_id},
            headers=operator_headers,
        ),
        client.patch(f"/api/returns/{order}/lines/{line}", json={"quantity": 2}, headers=operator_headers),
        client.delete(f"/api/returns/{order}/lines/{line}", headers=operator_headers),
        client.patch(f"/api/returns/{order}", json={"bo_wms_number": "1"}, headers=operator_headers),
        client.post(
            f"/api/returns/{order}/lines/{line}/images", files=[("files", ("a.png", PNG))], headers=operator_headers
        ),
        client.delete(f"/api/returns/{order}", headers=operator_headers),
    ]
    for request in blocked:
        assert (await request).status_code == 400

    await client.post(f"/api/returns/{order}/reopen", headers=operator_headers)
    response = await client.patch(f"/api/returns/{order}/lines/{line}", json={"quantity": 2}, headers=operator_headers)
    assert response.status_code == 200
