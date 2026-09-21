SKU = {"trade_reference": "45783276", "eans": ["5901234123457"], "product_name": "Lampa", "is_parametrized": True}


async def test_create_and_find_by_ean(client, operator_headers):
    created = await client.post("/api/skus", json=SKU, headers=operator_headers)
    assert created.status_code == 201

    found = await client.get("/api/skus/by-ean/5901234123457", headers=operator_headers)
    assert found.status_code == 200
    assert found.json()["trade_reference"] == "45783276"
    assert found.json()["is_parametrized"] is True


async def test_one_product_has_many_codes(client, operator_headers):
    payload = {**SKU, "eans": [" 5901234123457 ", "2000101723161", "5901234123457", ""]}
    created = (await client.post("/api/skus", json=payload, headers=operator_headers)).json()
    assert created["eans"] == ["2000101723161", "5901234123457"]
    for code in created["eans"]:
        response = await client.get(f"/api/skus/by-ean/{code}", headers=operator_headers)
        assert response.json()["id"] == created["id"]


async def test_unknown_ean_is_404(client, operator_headers):
    assert (await client.get("/api/skus/by-ean/0000000000000", headers=operator_headers)).status_code == 404


async def test_duplicate_reference_or_code_of_another_sku_conflicts(client, operator_headers):
    await client.post("/api/skus", json=SKU, headers=operator_headers)
    same_ref = {**SKU, "eans": ["1111111111111"]}
    same_ean = {**SKU, "trade_reference": "999"}
    assert (await client.post("/api/skus", json=same_ref, headers=operator_headers)).status_code == 409
    assert (await client.post("/api/skus", json=same_ean, headers=operator_headers)).status_code == 409


async def test_search_matches_name_reference_and_code_prefix(client, operator_headers):
    await client.post("/api/skus", json=SKU, headers=operator_headers)
    for query in ("lamp", "4578", "590123"):
        response = await client.get("/api/skus", params={"q": query}, headers=operator_headers)
        assert response.json()["total"] == 1, query
    # Codes match from the start only.
    assert (await client.get("/api/skus", params={"q": "123457"}, headers=operator_headers)).json()["total"] == 0


async def test_update_replaces_codes_and_keeps_required_fields_on_null(client, operator_headers):
    sku_id = (await client.post("/api/skus", json=SKU, headers=operator_headers)).json()["id"]
    response = await client.patch(
        f"/api/skus/{sku_id}",
        json={"product_name": None, "eans": ["2000000000001", "5901234123457"]},
        headers=operator_headers,
    )
    assert response.status_code == 200
    assert response.json()["product_name"] == "Lampa"
    assert response.json()["eans"] == ["2000000000001", "5901234123457"]

    cleared = await client.patch(f"/api/skus/{sku_id}", json={"eans": []}, headers=operator_headers)
    assert cleared.json()["eans"] == []
    untouched = await client.patch(f"/api/skus/{sku_id}", json={"product_name": "Lampa 2"}, headers=operator_headers)
    assert untouched.json()["eans"] == []


async def test_sku_requires_auth(client):
    assert (await client.get("/api/skus")).status_code == 401


async def test_delete_unused_sku_removes_it_with_its_codes(client, operator_headers):
    created = (await client.post("/api/skus", json=SKU, headers=operator_headers)).json()
    assert (await client.get(f"/api/skus/{created['id']}/usage", headers=operator_headers)).json() == []

    deleted = await client.delete(f"/api/skus/{created['id']}", headers=operator_headers)
    assert deleted.status_code == 204
    assert (await client.get(f"/api/skus/{created['id']}", headers=operator_headers)).status_code == 404
    assert (await client.get("/api/skus/by-ean/5901234123457", headers=operator_headers)).status_code == 404
    # The freed code can go to a new product.
    assert (await client.post("/api/skus", json=SKU, headers=operator_headers)).status_code == 201


async def test_sku_used_in_a_return_is_not_deleted_and_lists_the_returns(client, operator_headers):
    sku_id = (await client.post("/api/skus", json=SKU, headers=operator_headers)).json()["id"]
    line = {"sku_id": sku_id, "quantity": 1, "carrier_type": "PARCEL", "goods_condition": "FULL_VALUE"}
    orders = []
    for number in ("356902", None):
        order = (await client.post("/api/returns", json={"bo_wms_number": number}, headers=operator_headers)).json()
        for _ in range(2 if number else 1):
            await client.post(f"/api/returns/{order['uuid']}/lines", json=line, headers=operator_headers)
        orders.append(order)

    deleted = await client.delete(f"/api/skus/{sku_id}", headers=operator_headers)
    assert deleted.status_code == 409
    assert (await client.get(f"/api/skus/{sku_id}", headers=operator_headers)).status_code == 200

    usage = (await client.get(f"/api/skus/{sku_id}/usage", headers=operator_headers)).json()
    by_uuid = {item["uuid"]: item for item in usage}
    assert set(by_uuid) == {order["uuid"] for order in orders}
    assert by_uuid[orders[0]["uuid"]]["lines"] == 2
    assert by_uuid[orders[0]["uuid"]]["bo_wms_number"] == "356902"
    assert by_uuid[orders[1]["uuid"]]["lines"] == 1
    assert by_uuid[orders[1]["uuid"]]["status"] == "OPEN"


async def test_delete_or_usage_of_unknown_sku_is_404(client, operator_headers):
    assert (await client.delete("/api/skus/999", headers=operator_headers)).status_code == 404
    assert (await client.get("/api/skus/999/usage", headers=operator_headers)).status_code == 404
