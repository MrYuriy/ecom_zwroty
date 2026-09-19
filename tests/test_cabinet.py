async def test_root_redirects_to_cabinet(client):
    response = await client.get("/")
    assert response.status_code == 307
    assert response.headers["location"] == "/app/"


PAGES = [
    "",
    "returns.html",
    "return.html",
    "return-form.html",
    "line.html",
    "line-view.html",
    "skus.html",
    "sku-form.html",
    "users.html",
    "user-form.html",
    "wms-orders.html",
]


async def test_pages_are_uncached_and_assets_versioned(client):
    for page in PAGES:
        path = f"/app/{page}"
        response = await client.get(path)
        assert response.status_code == 200, path
        assert response.headers["cache-control"] == "no-cache, must-revalidate"
        assert "?v=dev" not in response.text
        assert "api.js?v=" in response.text


async def test_unknown_page_is_404(client):
    assert (await client.get("/app/nope.html")).status_code == 404


async def test_static_assets_are_served(client):
    response = await client.get("/app/api.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
