import json

import pytest

from app.services.sku_import_parser import SkuFileError, parse_sku_file

# The warehouse export: a bare fragment, one record per line, Windows-1250.
EXPORT = ""","items":
[
{"supplier_sku_id":"6973081270294","sku_id":"99900014","description":"Rekawice winylowe M"}
,{"supplier_sku_id":"99900014","sku_id":"99900014","description":"Rekawice winylowe M"}
,{"supplier_sku_id":"2000101723161","sku_id":"10172316","description":"SZYBKOZŁ Z ZAW. REG. 1\\/2 GAR.","ecommerce":"Y"}
,{"supplier_sku_id":"4078500294201","sku_id":"10172316","description":"SZYBKOZŁ Z ZAW. REG. 1\\/2 GAR.","ecommerce":"Y"}
,{"supplier_sku_id":"6973081270294","sku_id":"45887590","description":"RĘKAWICE WINYLOWE 100SZT","ecommerce":"N"}
,{"supplier_sku_id":"","sku_id":"","description":"broken row"}
]}
""".encode("cp1250")


def _import(client, headers, content: bytes, name: str = "sku_ean.json"):
    return client.post("/api/sku-imports", files=[("file", (name, content, "application/json"))], headers=headers)


# ---------- parser ----------


def test_parser_reads_the_export_fragment():
    parsed = parse_sku_file(EXPORT)
    assert parsed.rows_read == 6 and parsed.rows_skipped == 1
    assert parsed.skus["10172316"] == ["SZYBKOZŁ Z ZAW. REG. 1/2 GAR.", True]
    assert parsed.skus["99900014"] == ["Rekawice winylowe M", None]
    # A code listed under two products belongs to the last one in the file.
    assert parsed.eans["6973081270294"] == "45887590"


def test_parser_reads_a_regular_json_document():
    document = {"items": [{"supplier_sku_id": "590", "sku_id": "1", "description": "A", "ecommerce": "N"}]}
    for raw in (json.dumps(document), json.dumps(document["items"])):
        assert parse_sku_file(raw.encode()).skus == {"1": ["A", False]}


def test_parser_rejects_unrelated_files():
    with pytest.raises(SkuFileError):
        parse_sku_file(b'{"hello": "world"}')


# ---------- import ----------


async def test_import_creates_products_and_codes(client, admin_headers):
    response = await _import(client, admin_headers, EXPORT)
    assert response.status_code == 202
    job = (await client.get("/api/sku-imports/latest", headers=admin_headers)).json()
    assert job["status"] == "DONE", job
    assert (job["rows_read"], job["rows_skipped"]) == (6, 1)
    assert (job["skus_created"], job["skus_updated"]) == (3, 0)
    assert (job["eans_created"], job["eans_reassigned"]) == (4, 0)

    found = (await client.get("/api/skus/by-ean/4078500294201", headers=admin_headers)).json()
    assert found["trade_reference"] == "10172316"
    assert found["eans"] == ["2000101723161", "4078500294201"]
    assert found["product_name"] == "SZYBKOZŁ Z ZAW. REG. 1/2 GAR."
    assert found["is_parametrized"] is True
    shared = (await client.get("/api/skus/by-ean/6973081270294", headers=admin_headers)).json()
    assert shared["trade_reference"] == "45887590"


async def test_reimport_updates_moves_codes_and_deletes_nothing(client, admin_headers):
    existing = {"trade_reference": "77777777", "product_name": "Stary produkt", "eans": ["5900000000077"]}
    await client.post("/api/skus", json=existing, headers=admin_headers)
    await _import(client, admin_headers, EXPORT)

    update = ""","items":[
{"supplier_sku_id":"5900000000077","sku_id":"99900014","description":"Rekawice winylowe L","ecommerce":"Y"}
]}""".encode()
    started = (await _import(client, admin_headers, update)).json()
    job = (await client.get(f"/api/sku-imports/{started['uuid']}", headers=admin_headers)).json()
    assert (job["skus_created"], job["skus_updated"], job["eans_created"], job["eans_reassigned"]) == (0, 1, 0, 1)

    renamed = (await client.get("/api/skus/by-ean/5900000000077", headers=admin_headers)).json()
    assert renamed["trade_reference"] == "99900014"
    assert renamed["product_name"] == "Rekawice winylowe L" and renamed["is_parametrized"] is True
    # The old product is still there, only without the code that moved.
    old = (await client.get("/api/skus", params={"q": "77777777"}, headers=admin_headers)).json()["items"][0]
    assert old["eans"] == []
    # Products missing from the new file are kept.
    assert (await client.get("/api/skus/by-ean/2000101723161", headers=admin_headers)).status_code == 200


async def test_missing_ecommerce_keeps_the_flag(client, admin_headers):
    await client.post(
        "/api/skus",
        json={"trade_reference": "99900014", "product_name": "X", "is_parametrized": True},
        headers=admin_headers,
    )
    await _import(client, admin_headers, EXPORT)
    sku = (await client.get("/api/skus", params={"q": "99900014"}, headers=admin_headers)).json()["items"][0]
    assert sku["is_parametrized"] is True


async def test_a_bad_file_fails_without_touching_the_register(client, admin_headers):
    assert (await _import(client, admin_headers, b"not json at all")).status_code == 202
    job = (await client.get("/api/sku-imports/latest", headers=admin_headers)).json()
    assert job["status"] == "FAILED" and job["error"]
    assert (await client.get("/api/skus", headers=admin_headers)).json()["total"] == 0


async def test_empty_file_is_rejected(client, admin_headers):
    assert (await _import(client, admin_headers, b"")).status_code == 400


async def test_only_admins_import(client, operator_headers):
    assert (await _import(client, operator_headers, EXPORT)).status_code == 403
    assert (await client.get("/api/sku-imports/latest", headers=operator_headers)).status_code == 403
