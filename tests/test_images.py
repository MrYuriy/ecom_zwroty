import pytest_asyncio

from app.core import settings
from app.services.image_storage import ImageStorage

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
LINE = {"quantity": 1, "carrier_type": "PARCEL", "goods_condition": "DAMAGED", "damage_description": "rogi"}


@pytest_asyncio.fixture
async def line(client, operator_headers) -> dict:
    sku = {"trade_reference": "82376357", "ean": "5900000000001", "product_name": "Dysk"}
    sku_id = (await client.post("/api/skus", json=sku, headers=operator_headers)).json()["id"]
    order = (await client.post("/api/returns", json={}, headers=operator_headers)).json()
    order = (
        await client.post(
            f"/api/returns/{order['uuid']}/lines", json={**LINE, "sku_id": sku_id}, headers=operator_headers
        )
    ).json()
    return {"order": order["uuid"], "line": order["lines"][0]["uuid"]}


def _url(line: dict) -> str:
    return f"/api/returns/{line['order']}/lines/{line['line']}/images"


async def test_upload_list_and_download(client, operator_headers, line, uploads_dir):
    files = [("files", ("a.png", PNG, "image/png")), ("files", ("b.jpg", JPEG, "image/jpeg"))]
    response = await client.post(_url(line), files=files, headers=operator_headers)
    assert response.status_code == 201, response.text
    images = response.json()["lines"][0]["images"]
    assert [i["content_type"] for i in images] == ["image/png", "image/jpeg"]
    assert len(list(uploads_dir.iterdir())) == 2

    download = await client.get(f"/api/images/{images[0]['uuid']}", headers=operator_headers)
    assert download.status_code == 200
    assert download.content == PNG
    assert download.headers["content-type"] == "image/png"


async def test_download_requires_auth(client, operator_headers, line):
    response = await client.post(_url(line), files=[("files", ("a.png", PNG, "image/png"))], headers=operator_headers)
    image_uuid = response.json()["lines"][0]["images"][0]["uuid"]
    assert (await client.get(f"/api/images/{image_uuid}")).status_code == 401


async def test_type_is_checked_by_content_not_header(client, operator_headers, line, uploads_dir):
    fake = [("files", ("virus.jpg", b"MZ\x90\x00 not an image", "image/jpeg"))]
    assert (await client.post(_url(line), files=fake, headers=operator_headers)).status_code == 400
    assert not uploads_dir.exists() or not list(uploads_dir.iterdir())


async def test_one_bad_file_rejects_the_whole_upload(client, operator_headers, line, uploads_dir):
    files = [("files", ("ok.png", PNG, "image/png")), ("files", ("bad.txt", b"hello", "text/plain"))]
    assert (await client.post(_url(line), files=files, headers=operator_headers)).status_code == 400
    order = (await client.get(f"/api/returns/{line['order']}", headers=operator_headers)).json()
    assert order["lines"][0]["images"] == []
    assert not uploads_dir.exists() or not list(uploads_dir.iterdir())


async def test_size_and_count_limits(client, operator_headers, line, monkeypatch):
    monkeypatch.setattr(settings.storage, "MAX_IMAGE_MB", 0)
    too_big = [("files", ("a.png", PNG, "image/png"))]
    assert (await client.post(_url(line), files=too_big, headers=operator_headers)).status_code == 400

    monkeypatch.setattr(settings.storage, "MAX_IMAGE_MB", 15)
    monkeypatch.setattr(settings.storage, "MAX_IMAGES_PER_LINE", 2)
    three = [("files", (f"{i}.png", PNG, "image/png")) for i in range(3)]
    assert (await client.post(_url(line), files=three, headers=operator_headers)).status_code == 400


async def test_delete_image_removes_file(client, operator_headers, line, uploads_dir):
    response = await client.post(_url(line), files=[("files", ("a.png", PNG, "image/png"))], headers=operator_headers)
    image_uuid = response.json()["lines"][0]["images"][0]["uuid"]

    deleted = await client.delete(f"{_url(line)}/{image_uuid}", headers=operator_headers)
    assert deleted.status_code == 200
    assert deleted.json()["lines"][0]["images"] == []
    assert not list(uploads_dir.iterdir())


async def test_deleting_line_removes_files(client, operator_headers, line, uploads_dir):
    await client.post(_url(line), files=[("files", ("a.png", PNG, "image/png"))], headers=operator_headers)
    await client.delete(f"/api/returns/{line['order']}/lines/{line['line']}", headers=operator_headers)
    assert not list(uploads_dir.iterdir())


async def test_deleting_order_removes_files(client, operator_headers, line, uploads_dir):
    await client.post(_url(line), files=[("files", ("a.png", PNG, "image/png"))], headers=operator_headers)
    assert (await client.delete(f"/api/returns/{line['order']}", headers=operator_headers)).status_code == 204
    assert not list(uploads_dir.iterdir())


def test_storage_refuses_paths_outside_uploads(uploads_dir):
    storage = ImageStorage()
    for name in ("../secret.txt", "../../etc/passwd", "/etc/passwd"):
        try:
            storage.path_of(name)
        except ValueError:
            continue
        raise AssertionError(f"{name} escaped the uploads directory")
