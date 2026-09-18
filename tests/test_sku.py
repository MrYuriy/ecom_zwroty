SKU = {"trade_reference": "45783276", "ean": "5901234123457", "product_name": "Lampa", "is_parametrized": True}


async def test_create_and_find_by_ean(client, operator_headers):
    created = await client.post("/api/skus", json=SKU, headers=operator_headers)
    assert created.status_code == 201

    found = await client.get(f"/api/skus/by-ean/{SKU['ean']}", headers=operator_headers)
    assert found.status_code == 200
    assert found.json()["trade_reference"] == "45783276"
    assert found.json()["is_parametrized"] is True


async def test_unknown_ean_is_404(client, operator_headers):
    assert (await client.get("/api/skus/by-ean/0000000000000", headers=operator_headers)).status_code == 404


async def test_duplicate_reference_or_ean_conflicts(client, operator_headers):
    await client.post("/api/skus", json=SKU, headers=operator_headers)
    same_ref = {**SKU, "ean": "1111111111111"}
    same_ean = {**SKU, "trade_reference": "999"}
    assert (await client.post("/api/skus", json=same_ref, headers=operator_headers)).status_code == 409
    assert (await client.post("/api/skus", json=same_ean, headers=operator_headers)).status_code == 409


async def test_search_matches_name_reference_and_ean(client, operator_headers):
    await client.post("/api/skus", json=SKU, headers=operator_headers)
    for query in ("lamp", "4578", "590123"):
        response = await client.get("/api/skus", params={"q": query}, headers=operator_headers)
        assert response.json()["total"] == 1, query


async def test_update_keeps_required_fields_on_null(client, operator_headers):
    sku_id = (await client.post("/api/skus", json=SKU, headers=operator_headers)).json()["id"]
    response = await client.patch(
        f"/api/skus/{sku_id}", json={"product_name": None, "ean": None}, headers=operator_headers
    )
    assert response.status_code == 200
    assert response.json()["product_name"] == "Lampa"
    assert response.json()["ean"] is None


async def test_sku_requires_auth(client):
    assert (await client.get("/api/skus")).status_code == 401
