from datetime import date

import pytest_asyncio

LINE = {"quantity": 2, "carrier_type": "PARCEL", "goods_condition": "DAMAGED", "damage_description": "rogi"}
URL = "/api/reports/day-pdf"


@pytest_asyncio.fixture
async def sku_id(client, operator_headers) -> int:
    payload = {"trade_reference": "82376357", "eans": ["5900000000001"], "product_name": "Dysk"}
    return (await client.post("/api/skus", json=payload, headers=operator_headers)).json()["id"]


async def test_day_pdf_opens_inline_with_the_received_items(client, operator_headers, sku_id):
    order = (await client.post("/api/returns", json={"bo_wms_number": "356902"}, headers=operator_headers)).json()
    await client.post(f"/api/returns/{order['uuid']}/lines", json={**LINE, "sku_id": sku_id}, headers=operator_headers)

    response = await client.get(URL, params={"day": order["return_date"]}, headers=operator_headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "inline" in response.headers["content-disposition"]
    assert order["return_date"] in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


async def test_a_day_without_returns_gives_the_empty_form(client, operator_headers):
    response = await client.get(URL, params={"day": "2020-01-02"}, headers=operator_headers)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


async def test_many_items_spill_onto_further_pages(client, operator_headers, sku_id):
    order = (await client.post("/api/returns", json={}, headers=operator_headers)).json()
    for _ in range(20):
        await client.post(
            f"/api/returns/{order['uuid']}/lines", json={**LINE, "sku_id": sku_id}, headers=operator_headers
        )

    one_page = await client.get(URL, params={"day": "2020-01-02"}, headers=operator_headers)
    two_pages = await client.get(URL, params={"day": order["return_date"]}, headers=operator_headers)
    assert two_pages.content.count(b"/Type /Page\n") > one_page.content.count(b"/Type /Page\n")


async def test_day_pdf_needs_a_login_and_a_valid_date(client, operator_headers):
    assert (await client.get(URL, params={"day": date.today().isoformat()})).status_code == 401
    assert (await client.get(URL, params={"day": "wczoraj"}, headers=operator_headers)).status_code == 422
    assert (await client.get(URL, headers=operator_headers)).status_code == 422
