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
