from app.services.image_storage import image_file_name

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
LINE = {"quantity": 1, "carrier_type": "PARCEL", "goods_condition": "DAMAGED"}


async def _sku(client, headers, reference: str) -> int:
    payload = {"trade_reference": reference, "product_name": f"Produkt {reference}"}
    return (await client.post("/api/skus", json=payload, headers=headers)).json()["id"]


async def _line(client, headers, sku_id: int, bo: str | None = None) -> dict:
    order_uuid = (await client.post("/api/returns", json={"bo_wms_number": bo}, headers=headers)).json()["uuid"]
    order = (
        await client.post(f"/api/returns/{order_uuid}/lines", json={**LINE, "sku_id": sku_id}, headers=headers)
    ).json()
    return {"order": order_uuid, "line": order["lines"][-1]["uuid"]}


async def _upload(client, headers, line: dict, *contents: bytes) -> list[str]:
    files = [("files", (f"photo{i}", data, "application/octet-stream")) for i, data in enumerate(contents)]
    response = await client.post(
        f"/api/returns/{line['order']}/lines/{line['line']}/images", files=files, headers=headers
    )
    assert response.status_code == 201, response.text
    return _names(response.json(), line)


def _names(order: dict, line: dict) -> list[str]:
    target = next(item for item in order["lines"] if item["uuid"] == line["line"])
    return [image["file_name"] for image in target["images"]]


def _files(uploads_dir) -> set[str]:
    return {path.name for path in uploads_dir.iterdir()}


async def test_names_follow_bo_reference_and_number(client, operator_headers, uploads_dir):
    line = await _line(client, operator_headers, await _sku(client, operator_headers, "82376357"), bo="356902")
    assert await _upload(client, operator_headers, line, PNG, JPEG) == [
        "356902_82376357_1.png",
        "356902_82376357_2.jpg",
    ]
    # A later upload continues the numbering.
    assert (await _upload(client, operator_headers, line, PNG))[-1] == "356902_82376357_3.png"
    assert _files(uploads_dir) == {"356902_82376357_1.png", "356902_82376357_2.jpg", "356902_82376357_3.png"}


async def test_order_without_number_is_brak(client, operator_headers):
    line = await _line(client, operator_headers, await _sku(client, operator_headers, "45783276"))
    assert await _upload(client, operator_headers, line, PNG) == ["brak_45783276_1.png"]


async def test_same_pair_in_two_lines_never_collides(client, operator_headers):
    sku_id = await _sku(client, operator_headers, "45783276")
    first = await _line(client, operator_headers, sku_id)
    second = await _line(client, operator_headers, sku_id)
    await _upload(client, operator_headers, first, PNG)
    assert await _upload(client, operator_headers, second, PNG) == ["brak_45783276_2.png"]


async def test_deleting_a_photo_closes_the_gap(client, operator_headers, uploads_dir):
    line = await _line(client, operator_headers, await _sku(client, operator_headers, "82376357"), bo="356902")
    await _upload(client, operator_headers, line, PNG, JPEG, PNG)
    order = (await client.get(f"/api/returns/{line['order']}", headers=operator_headers)).json()
    first = order["lines"][0]["images"][0]["uuid"]

    url = f"/api/returns/{line['order']}/lines/{line['line']}/images/{first}"
    order = (await client.delete(url, headers=operator_headers)).json()
    assert _names(order, line) == ["356902_82376357_1.jpg", "356902_82376357_2.png"]
    assert _files(uploads_dir) == {"356902_82376357_1.jpg", "356902_82376357_2.png"}


async def test_new_bo_number_renames_files(client, operator_headers, uploads_dir):
    line = await _line(client, operator_headers, await _sku(client, operator_headers, "82376357"))
    await _upload(client, operator_headers, line, PNG)

    order = (
        await client.patch(f"/api/returns/{line['order']}", json={"bo_wms_number": "361852"}, headers=operator_headers)
    ).json()
    assert _names(order, line) == ["361852_82376357_1.png"]
    assert _files(uploads_dir) == {"361852_82376357_1.png"}


async def test_other_sku_on_the_line_renames_files(client, operator_headers, uploads_dir):
    line = await _line(client, operator_headers, await _sku(client, operator_headers, "82376357"), bo="356902")
    await _upload(client, operator_headers, line, PNG)
    other = await _sku(client, operator_headers, "92716869")

    url = f"/api/returns/{line['order']}/lines/{line['line']}"
    order = (await client.patch(url, json={"sku_id": other}, headers=operator_headers)).json()
    assert _names(order, line) == ["356902_92716869_1.png"]
    assert _files(uploads_dir) == {"356902_92716869_1.png"}


async def test_new_trade_reference_renames_files(client, operator_headers, uploads_dir):
    sku_id = await _sku(client, operator_headers, "82376357")
    line = await _line(client, operator_headers, sku_id, bo="356902")
    await _upload(client, operator_headers, line, PNG)

    await client.patch(f"/api/skus/{sku_id}", json={"trade_reference": "82376358"}, headers=operator_headers)
    assert _files(uploads_dir) == {"356902_82376358_1.png"}


async def test_deleting_a_line_renumbers_the_rest_of_the_pair(client, operator_headers, uploads_dir):
    sku_id = await _sku(client, operator_headers, "45783276")
    first = await _line(client, operator_headers, sku_id)
    second = await _line(client, operator_headers, sku_id)
    await _upload(client, operator_headers, first, PNG)
    await _upload(client, operator_headers, second, JPEG)

    await client.delete(f"/api/returns/{first['order']}/lines/{first['line']}", headers=operator_headers)
    assert _files(uploads_dir) == {"brak_45783276_1.jpg"}


async def test_download_carries_the_file_name(client, operator_headers):
    line = await _line(client, operator_headers, await _sku(client, operator_headers, "82376357"), bo="356902")
    await _upload(client, operator_headers, line, PNG)
    order = (await client.get(f"/api/returns/{line['order']}", headers=operator_headers)).json()

    response = await client.get(f"/api/images/{order['lines'][0]['images'][0]['uuid']}", headers=operator_headers)
    assert response.headers["content-disposition"] == 'inline; filename="356902_82376357_1.png"'


def test_unsafe_characters_are_encoded():
    assert image_file_name("A/B 1", "REF_1", 2, "image/webp") == "A~2fB~201_REF~5f1_2.webp"
